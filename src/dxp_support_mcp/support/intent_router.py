from __future__ import annotations

import re
from typing import Any

INTENT_KEYWORDS: dict[str, list[str]] = {
    "ERROR_WHY": [
        "error",
        "wrong",
        "failed",
        "failure",
        "problem",
        "issue",
        "why is there",
        "what went wrong",
    ],
    "STATUS_MEANING": [
        "what does",
        "mean",
        "status mean",
        "explain status",
    ],
    "STATUS_NEXT_STEP": [
        "next step",
        "what should i do",
        "what can i do",
        "what to do",
        "how do i proceed",
        "next move",
    ],
    "ELIGIBILITY": [
        "eligible",
        "eligibility",
        "why can't",
        "why cant",
        "not allowed",
        "blocked",
        "cannot",
        "can't",
    ],
    "DATE_DEADLINE": [
        "when",
        "date",
        "deadline",
        "last date",
        "due",
        "expires",
        "expiry",
        "window",
    ],
    "PRICING_DISCOUNT": [
        "discount",
        "promo",
        "approval",
        "on hold",
        "hold",
        "reprice",
        "pricing",
    ],
    "ACTION_HOW_TO": [
        "how do i",
        "how to",
        "create amendment",
        "apply discount",
        "start renewal",
        "submit",
    ],
    "DEVICE_TRANSFER": [
        "device",
        "transfer",
        "transferred",
        "scheduled transfer",
        "serial",
    ],
    "RENEWAL": [
        "renew",
        "renewal",
        "renewal error",
        "auto-renew",
        "auto renew",
    ],
    "SUBSCRIPTION": [
        "subscription",
        "license",
        "assign",
        "seat",
        "entitlement",
    ],
    "PERMISSION": [
        "permission",
        "access denied",
        "authorized",
        "not authorized",
    ],
    "INTEGRATION_SYNC": [
        "salesforce",
        "sync",
        "stuck",
        "not updated",
        "delay",
    ],
    "GENERAL_FAQ": [],
}

INTENT_TO_TAGS: dict[str, list[str]] = {
    "ERROR_WHY": ["error", "contract", "reason"],
    "STATUS_MEANING": ["status", "contract"],
    "STATUS_NEXT_STEP": ["status", "workflow", "contract"],
    "ELIGIBILITY": ["business-rules", "renewal", "amendment", "rule"],
    "DATE_DEADLINE": ["renewal", "contract", "rule"],
    "PRICING_DISCOUNT": ["approval", "discount", "pricing"],
    "ACTION_HOW_TO": ["workflow", "contract", "amendment"],
    "DEVICE_TRANSFER": ["device", "transfer"],
    "RENEWAL": ["renewal", "status"],
    "SUBSCRIPTION": ["subscription", "ems"],
    "PERMISSION": ["permission", "auth", "error"],
    "INTEGRATION_SYNC": ["integration", "salesforce"],
    "GENERAL_FAQ": ["faq"],
}


def detect_intents(question: str | None, context: dict[str, Any]) -> list[str]:
    if question and question.strip():
        return _intents_from_question(question)

    return _intents_from_context(context)


def tags_for_intents(intents: list[str]) -> set[str]:
    tags: set[str] = set()
    for intent in intents:
        tags.update(INTENT_TO_TAGS.get(intent, []))
    return tags


def _intents_from_question(question: str) -> list[str]:
    q = question.lower()
    scores: dict[str, int] = {}

    for intent, keywords in INTENT_KEYWORDS.items():
        if intent == "GENERAL_FAQ":
            continue
        for kw in keywords:
            if kw in q:
                scores[intent] = scores.get(intent, 0) + 1

    if not scores:
        return ["GENERAL_FAQ"]

    ranked = sorted(scores.items(), key=lambda x: (-x[1], x[0]))
    top_score = ranked[0][1]
    return [intent for intent, score in ranked if score == top_score][:3]


def _intents_from_context(context: dict[str, Any]) -> list[str]:
    intents: list[str] = ["STATUS_NEXT_STEP"]
    status = (context.get("status") or "").upper()
    error_reason = context.get("errorReason")
    renewal_status = context.get("renewalStatus")
    blockers = context.get("blockers") or []

    if status == "ERROR" or error_reason:
        intents.insert(0, "ERROR_WHY")
    if status == "ON_HOLD" or "approval_pending" in blockers:
        intents.append("PRICING_DISCOUNT")
    if renewal_status == "RENEWAL_ERROR" or "renewal_error" in blockers:
        intents.insert(0, "RENEWAL")
        intents.insert(0, "ERROR_WHY")
    if "trial_contract" in blockers or "renewal_blackout_window" in blockers:
        intents.append("ELIGIBILITY")
        intents.append("RENEWAL")
    if "amendment" in str(context.get("blockers")):
        intents.append("ELIGIBILITY")
    if context.get("approvalStatus") == "PENDING":
        intents.append("PRICING_DISCOUNT")
    if context.get("renewalDate"):
        intents.append("DATE_DEADLINE")

    return _dedupe(intents)


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def status_tag(status: str | None) -> str | None:
    if not status:
        return None
    return re.sub(r"[^a-z0-9]+", "-", status.lower()).strip("-")
