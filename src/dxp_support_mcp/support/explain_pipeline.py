from __future__ import annotations

from typing import Any

from dxp_support_mcp.config import AppConfig
from dxp_support_mcp.graphql.allowlist import OperationRegistry
from dxp_support_mcp.graphql.client import GraphQLClient
from dxp_support_mcp.support.context_builder import build_contract_context
from dxp_support_mcp.support.intent_router import detect_intents, tags_for_intents
from dxp_support_mcp.support.rag_retriever import KnowledgeIndex, context_tags_from_contract
from dxp_support_mcp.support.synthesizer import synthesize_answer

_index_cache: dict[str, KnowledgeIndex] = {}


def _get_index(config: AppConfig) -> KnowledgeIndex:
    key = str(config.knowledge_dir)
    if key not in _index_cache:
        _index_cache[key] = KnowledgeIndex(config.knowledge_dir)
    return _index_cache[key]


def explain_contract_response(
    client: GraphQLClient,
    registry: OperationRegistry,
    config: AppConfig,
    contract_id: str,
    question: str | None = None,
    *,
    briefing: bool = False,
) -> dict[str, Any]:
    context = build_contract_context(client, registry, config, contract_id)
    intents = detect_intents(None if briefing else question, context)

    ctx_tags = context_tags_from_contract(context)
    ctx_tags.update(tags_for_intents(intents))

    index = _get_index(config)
    chunks = index.retrieve(
        question=None if briefing else question,
        context_tags=ctx_tags,
        top_k=config.rag_top_k,
    )

    synthesis = synthesize_answer(config, context, chunks, intents, question)

    facts = {
        "status": context.get("status"),
        "type": context.get("type"),
        "statusChangeReason": context.get("statusChangeReason"),
        "approvalStatus": context.get("approvalStatus"),
        "errorReason": context.get("errorReason"),
        "renewalDate": context.get("renewalDate"),
        "daysToRenewal": context.get("daysToRenewal"),
        "blockers": context.get("blockers"),
    }

    response: dict[str, Any] = {
        "contractId": context.get("contractId"),
        "contractNumber": context.get("contractNumber"),
        "question": question,
        "briefing": briefing,
        "intentsDetected": intents,
        "facts": facts,
        "summary": synthesis.get("summary"),
        "explanation": synthesis.get("explanation"),
        "nextSteps": synthesis.get("nextSteps"),
        "relatedQuestions": synthesis.get("relatedQuestions"),
        "sources": [{"id": c.id, "title": c.title} for c in chunks],
        "confidence": synthesis.get("confidence"),
        "synthesisMode": synthesis.get("mode"),
        "knowledgeChunksLoaded": len(index.chunks()),
    }

    if briefing:
        response["briefingDetails"] = _build_briefing(context)

    if synthesis.get("llmError"):
        response["llmError"] = synthesis["llmError"]

    return response


def _build_briefing(context: dict[str, Any]) -> dict[str, Any]:
    return {
        "currentState": _state_label(context),
        "keyDates": {
            "renewalDate": context.get("renewalDate"),
            "quoteValidUntil": context.get("quoteValidUntil"),
            "daysToRenewal": context.get("daysToRenewal"),
        },
        "activeBlockers": context.get("blockers"),
        "askAbout": [
            "Why is there a contract error?",
            "What should I do next?",
            "When is the last date for renewal?",
            "Why is this contract not eligible for renewal?",
            "Why can't I create an amendment?",
        ],
    }


def _state_label(context: dict[str, Any]) -> str:
    status = context.get("status") or "UNKNOWN"
    parts = [status]
    if context.get("type"):
        parts.append(str(context["type"]))
    if context.get("statusChangeReason"):
        parts.append(str(context["statusChangeReason"]))
    elif context.get("errorReason"):
        parts.append(str(context["errorReason"]))
    if context.get("approvalStatus"):
        parts.append(f"approval={context['approvalStatus']}")
    return " / ".join(parts)
