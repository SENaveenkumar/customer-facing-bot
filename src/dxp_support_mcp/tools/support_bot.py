from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from dxp_support_mcp.graphql.allowlist import OperationRegistry
from dxp_support_mcp.graphql.client import GraphQLClient
from dxp_support_mcp.paths import PROJECT_ROOT
from dxp_support_mcp.tools.dxp_read import dxp_read


def _load_sql_template(name: str) -> str:
    path = PROJECT_ROOT / "operations" / "sql" / f"{name}.sql"
    if not path.is_file():
        raise FileNotFoundError(f"SQL template not found: {path}")
    return path.read_text(encoding="utf-8")


def support_bot_sql_read(
    client: GraphQLClient,
    registry: OperationRegistry,
    account_id: str,
    sql: str,
    max_rows: int = 100,
) -> Any:
    """Run read-only SQL via DXP supportBotRead (SELECT only, must use :account_id)."""
    data = dxp_read(
        client,
        registry,
        "SupportBotRead",
        {"accountId": account_id, "sql": sql, "maxRows": max_rows},
    )
    payload = data.get("supportBotRead") if isinstance(data, dict) else data
    if isinstance(payload, dict) and isinstance(payload.get("jsonRows"), str):
        payload = {
            **payload,
            "rows": json.loads(payload["jsonRows"]),
        }
    return payload


def support_bot_sql_template(
    client: GraphQLClient,
    registry: OperationRegistry,
    account_id: str,
    template_name: str,
    max_rows: int = 100,
) -> Any:
    """Run a bundled SQL file from operations/sql/ (e.g. renewal_eligible_contracts)."""
    sql = _load_sql_template(template_name)
    return support_bot_sql_read(client, registry, account_id, sql, max_rows)


def renewal_eligible_contract_ids(
    client: GraphQLClient,
    registry: OperationRegistry,
    account_id: str,
) -> list[str]:
    """Contract IDs eligible for renewal (C# isEligibleForRenewal rules)."""
    data = dxp_read(
        client,
        registry,
        "RenewalEligibleContractIds",
        {"accountId": account_id},
    )
    ids = data.get("renewalEligibleContractIds") or []
    return [str(x) for x in ids]


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
