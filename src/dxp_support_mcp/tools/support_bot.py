from __future__ import annotations

from typing import Any

from dxp_support_mcp.graphql.allowlist import OperationRegistry
from dxp_support_mcp.graphql.client import GraphQLClient
from dxp_support_mcp.tools.dxp_read import dxp_read


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
    """Merge user-supplied fields over last-contract defaults."""
    if user_input and _has_minimum_create_fields(user_input):
        base = dict(user_input)
        base.setdefault("billToAccountId", account_id)
        return base

    if not defaults:
        raise ValueError(
            "No user input and no previous contract for this account. "
            "Provide create details or create at least one contract first."
        )

    quote_lines = defaults.get("quoteLines") or []
    return {
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


def _has_minimum_create_fields(data: dict[str, Any]) -> bool:
    required = {
        "currencyCode",
        "billToContactId",
        "billToAddressId",
        "customerAccountId",
        "termUOM",
        "termQuantity",
        "quoteLines",
    }
    return required.issubset(data.keys()) and bool(data.get("quoteLines"))
