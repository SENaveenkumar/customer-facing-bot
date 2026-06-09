from __future__ import annotations

import json
import re
from typing import Any

import httpx

from dxp_support_mcp.config import AppConfig
from dxp_support_mcp.support.rag_retriever import KnowledgeChunk

SYSTEM_PROMPT = """You are a DXP dealer support assistant.

You receive CONTRACT_CONTEXT (live facts), KNOWLEDGE_CHUNKS (business rules), and an optional USER_QUESTION.

Rules:
- State facts ONLY from CONTRACT_CONTEXT. Never invent IDs, dates, or statuses.
- Explain "why" and recommended next steps using KNOWLEDGE_CHUNKS.
- For amendment, discount, and assignment eligibility use status/type/approvalStatus facts plus KB rules — do not hardcode status lists.
- Return valid JSON matching the schema exactly.
"""

RESPONSE_SCHEMA = {
    "summary": "string — one paragraph answer",
    "explanation": "string — why this is happening",
    "nextSteps": [{"action": "string", "priority": "high|medium|low", "automatable": "boolean"}],
    "relatedQuestions": ["string"],
    "confidence": "high|medium|low",
}


def synthesize_answer(
    config: AppConfig,
    context: dict[str, Any],
    chunks: list[KnowledgeChunk],
    intents: list[str],
    question: str | None,
) -> dict[str, Any]:
    if config.openai_api_key:
        try:
            return _synthesize_llm(config, context, chunks, intents, question)
        except Exception as exc:
            fallback = _synthesize_rule_based(context, chunks, intents, question)
            fallback["llmError"] = str(exc)
            return fallback

    return _synthesize_rule_based(context, chunks, intents, question)


def _synthesize_llm(
    config: AppConfig,
    context: dict[str, Any],
    chunks: list[KnowledgeChunk],
    intents: list[str],
    question: str | None,
) -> dict[str, Any]:
    payload_context = {k: v for k, v in context.items() if not k.startswith("_")}
    chunk_payload = [
        {"id": c.id, "title": c.title, "content": c.content[:2000]} for c in chunks
    ]

    user_content = json.dumps(
        {
            "contractContext": payload_context,
            "knowledgeChunks": chunk_payload,
            "intentsDetected": intents,
            "userQuestion": question,
            "responseSchema": RESPONSE_SCHEMA,
        },
        indent=2,
    )

    with httpx.Client(timeout=120.0) as http:
        response = http.post(
            f"{config.openai_base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {config.openai_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": config.openai_model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
                "response_format": {"type": "json_object"},
            },
        )
    if response.status_code >= 400:
        raise RuntimeError(response.text)

    body = response.json()
    content = body["choices"][0]["message"]["content"]
    parsed = json.loads(content)
    return {
        "summary": parsed.get("summary", ""),
        "explanation": parsed.get("explanation", ""),
        "nextSteps": parsed.get("nextSteps") or [],
        "relatedQuestions": parsed.get("relatedQuestions") or [],
        "confidence": parsed.get("confidence", "medium"),
        "mode": "llm",
    }


def _synthesize_rule_based(
    context: dict[str, Any],
    chunks: list[KnowledgeChunk],
    intents: list[str],
    question: str | None,
) -> dict[str, Any]:
    status = context.get("status") or "UNKNOWN"
    error_reason = context.get("errorReason")
    status_change_reason = context.get("statusChangeReason")
    approval_status = context.get("approvalStatus")

    summary_parts = [
        f"Contract {context.get('contractNumber') or context.get('contractId')} "
        f"is in {status} status."
    ]
    if context.get("type"):
        summary_parts.append(f"Type: {context['type']}.")
    if status_change_reason:
        summary_parts.append(f"Status change reason: {status_change_reason}.")
    elif error_reason:
        summary_parts.append(f"Error reason: {error_reason}.")
    if approval_status:
        summary_parts.append(f"Approval status: {approval_status}.")
    if context.get("renewalDate"):
        summary_parts.append(f"Renewal date: {context['renewalDate']}.")
    if context.get("daysToRenewal") is not None:
        summary_parts.append(f"Days to renewal: {context['daysToRenewal']}.")

    explanation = _explanation_from_chunks(chunks, context, intents, question)
    next_steps = _next_steps_from_context(context, chunks, intents)
    related = _related_questions(intents, context)

    return {
        "summary": " ".join(summary_parts),
        "explanation": explanation,
        "nextSteps": next_steps,
        "relatedQuestions": related,
        "confidence": "medium" if chunks else "low",
        "mode": "rule_based",
    }


def _explanation_from_chunks(
    chunks: list[KnowledgeChunk],
    context: dict[str, Any],
    intents: list[str],
    question: str | None,
) -> str:
    if not chunks:
        return (
            "No knowledge chunks loaded. Run knowledge/generate_kb.py to build "
            "knowledge/chunks/, or set KNOWLEDGE_DIR."
        )

    parts: list[str] = []
    status = (context.get("status") or "").upper()
    error_reason = context.get("errorReason")
    status_change_reason = context.get("statusChangeReason")
    approval_status = context.get("approvalStatus")

    for chunk in chunks[:3]:
        snippet = chunk.content.strip()
        if len(snippet) > 600:
            snippet = snippet[:600].rsplit("\n", 1)[0] + "..."
        parts.append(f"**{chunk.title}:** {snippet}")

    if "ELIGIBILITY" in intents or "RENEWAL" in intents:
        parts.append(
            "Renewal and amendment eligibility rules are in renewal and business-rules "
            "knowledge chunks — compare status, type, renewalDate, and blockers to those rules."
        )
    if status == "ERROR" and (error_reason or status_change_reason):
        reason = status_change_reason or error_reason
        parts.append(
            f"The API reports reason={reason}. "
            "Cross-reference with contract-reason and error knowledge chunks."
        )
    if approval_status == "PENDING":
        parts.append(
            "Approval is pending — see approval-workflow and discount-range knowledge chunks."
        )

    return "\n\n".join(parts)


def _next_steps_from_context(
    context: dict[str, Any],
    chunks: list[KnowledgeChunk],
    intents: list[str],
) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    status = (context.get("status") or "").upper()
    approval_status = context.get("approvalStatus")

    status_chunk = next(
        (c for c in chunks if c.id == f"contract-status-{status.lower()}"),
        None,
    )
    if status_chunk:
        allowed = _extract_section(status_chunk.content, "Allowed Actions")
        if allowed:
            for action in allowed.split(",")[:4]:
                action = action.strip()
                if action:
                    steps.append(
                        {"action": action, "priority": "high", "automatable": False}
                    )

    if status == "ERROR":
        steps.append(
            {
                "action": "Check dashboard attention events and contact support if unresolved",
                "priority": "high",
                "automatable": False,
            }
        )
    if status == "ON_HOLD" or approval_status == "PENDING" or "PRICING_DISCOUNT" in intents:
        steps.append(
            {
                "action": "Review statusChangeReason or hold reason; approve/resubmit pricing or submit D-Country form if applicable",
                "priority": "high",
                "automatable": False,
            }
        )
    if approval_status == "REJECTED":
        steps.append(
            {
                "action": "Withdraw approval request and reprice without declined discount or billing change",
                "priority": "high",
                "automatable": False,
            }
        )
    if "ELIGIBILITY" in intents and "amendment" in str(context.get("blockers")):
        steps.append(
            {
                "action": "Resolve amendment blockers per business-rules knowledge chunks before creating amendment",
                "priority": "high",
                "automatable": False,
            }
        )
    if status == "ACTIVATED" and "RENEWAL" in intents:
        steps.append(
            {
                "action": "Review renewal window rules and start renewal if eligible",
                "priority": "medium",
                "automatable": False,
            }
        )
    if status == "DRAFT":
        steps.append(
            {
                "action": "Review pricing and submit contract (convertContract)",
                "priority": "high",
                "automatable": True,
            }
        )

    if not steps:
        steps.append(
            {
                "action": "Monitor contract status for updates from order management",
                "priority": "low",
                "automatable": False,
            }
        )

    return _dedupe_steps(steps)


def _related_questions(intents: list[str], context: dict[str, Any]) -> list[str]:
    status = (context.get("status") or "").upper()
    questions = [
        "What should I do next?",
        "Why is this contract not eligible for renewal?",
        "Why can't I create an amendment?",
        "When is the last date for renewal?",
        "Why is there a renewal error?",
    ]
    if context.get("errorReason") or context.get("statusChangeReason"):
        questions.insert(0, "Why is there a contract error?")
    if context.get("approvalStatus") == "PENDING":
        questions.insert(0, "How do I apply a discount?")
    if status in ("DRAFT", "AMENDMENT_DRAFT"):
        questions.insert(0, "How do I apply a discount?")
    return questions[:5]


def _extract_section(content: str, heading: str) -> str | None:
    pattern = rf"\*\*{re.escape(heading)}:\*\*\s*(.+?)(?:\n\*\*|\Z)"
    match = re.search(pattern, content, re.DOTALL)
    if match:
        return match.group(1).strip()
    return None


def _dedupe_steps(steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for step in steps:
        key = step.get("action", "")
        if key not in seen:
            seen.add(key)
            out.append(step)
    return out
