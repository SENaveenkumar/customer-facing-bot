from __future__ import annotations

from typing import Any

from dxp_support_mcp.graphql.allowlist import OperationRegistry
from dxp_support_mcp.graphql.client import GraphQLClient
from dxp_support_mcp.tools.dxp_read import dxp_read

# Hardcoded fallback when LastContractDefaults is unavailable.
# quoteLines are not included — caller must supply productId + quantity in user_input.
HARDCODED_CREATE_PROFILE: dict[str, Any] = {
    "autoRenew": False,
    "billToAccountId": "300000166572548",
    "billToAddressId": "300000326145330",
    "billToContactId": "1772537152821204",
    "shipToAddressId": "1752154117458796",
    "shipToContactId": "1757506796491262",
    "currencyCode": "USD",
    "customerAccountId": "300000016059641",
    "termQuantity": 1,
    "termUOM": "YEAR",
    "contractType": "NEW",
}


def get_last_contract_defaults(
    client: GraphQLClient,
    registry: OperationRegistry,
    account_id: str,
) -> dict[str, Any] | None:
    data = dxp_read(
        client,
        registry,
        "LastContractDefaults",
        {"accountId": account_id},
    )
    return data.get("lastContractDefaults")


def build_create_quote_input(
    account_id: str,
    user_input: dict[str, Any] | None,
    defaults: dict[str, Any] | None,
) -> dict[str, Any]:
    """Build a mutation-ready CreateQuoteInput with tolerant key normalization."""
    if user_input and _has_minimum_create_fields(user_input):
        base = normalize_create_quote_input(user_input)
        base.setdefault("billToAccountId", account_id)
        return base

    if not defaults:
        merged = dict(HARDCODED_CREATE_PROFILE)
        merged["billToAccountId"] = account_id or merged["billToAccountId"]
        merged.update(user_input or {})
        normalized = normalize_create_quote_input(merged)
        if not _has_minimum_create_fields(normalized):
            raise ValueError(
                "No previous contract defaults available. Hardcoded profile applied, "
                "but quoteLines (productId + quantity) are still required."
            )
        return normalized

    quote_lines = defaults.get("quoteLines") or []
    return normalize_create_quote_input(
        {
        "currencyCode": defaults["currencyCode"],
        "billToContactId": defaults["billToContactId"],
        "billToAddressId": defaults["billToAddressId"],
        "billToAccountId": defaults.get("billToAccountId") or account_id,
        "customerAccountId": defaults["customerAccountId"],
        "shipToAddressId": defaults.get("shipToAddressId"),
        "shipToContactId": defaults.get("shipToContactId"),
        "termUOM": defaults["termUOM"],
        "termQuantity": defaults["termQuantity"],
        "autoRenew": defaults.get("autoRenew", False),
        "contractType": "NEW",
        "quoteLines": [
            {"productId": line["productId"], "quantity": line["quantity"]}
            for line in quote_lines
            if line.get("productId") and line.get("productId") != "UNKNOWN"
        ],
        **(user_input or {}),
        }
    )


def _has_minimum_create_fields(data: dict[str, Any]) -> bool:
    normalized = normalize_create_quote_input(data)
    required = {
        "currencyCode",
        "billToContactId",
        "billToAddressId",
        "customerAccountId",
        "termUOM",
        "termQuantity",
        "quoteLines",
    }
    return required.issubset(normalized.keys()) and bool(normalized.get("quoteLines"))


def normalize_create_quote_input(data: dict[str, Any]) -> dict[str, Any]:
    """Map legacy aliases to safer canonical keys expected by newer schemas."""
    base = dict(data)

    # Normalize casing for TermUOM expected by CreateQuoteInput.
    if "termUom" in base and "termUOM" not in base:
        base["termUOM"] = base.pop("termUom")

    # Normalize currency key expected by CreateQuoteInput.
    if "currencyId" in base and "currencyCode" not in base:
        base["currencyCode"] = base.pop("currencyId")

    if "contractType" not in base:
        # Keep contract type internal default; user should not be prompted for it.
        base["contractType"] = "NEW"

    quote_lines = base.get("quoteLines")
    if isinstance(quote_lines, list):
        normalized_lines: list[dict[str, Any]] = []
        for line in quote_lines:
            if not isinstance(line, dict):
                continue
            product_id = line.get("productId") or line.get("id")
            quantity = line.get("quantity", 1)
            if product_id:
                normalized_lines.append(
                    {"productId": product_id, "quantity": quantity}
                )
        base["quoteLines"] = normalized_lines

    return {k: v for k, v in base.items() if v is not None}
