from __future__ import annotations

import json
from typing import Any

from dxp_support_mcp.config import AppConfig
from dxp_support_mcp.graphql.allowlist import OperationRegistry
from dxp_support_mcp.graphql.client import GraphQLClient
from dxp_support_mcp.tools.contract_mutations import create_draft_contract
from dxp_support_mcp.tools.support_bot import (
    build_create_quote_input,
    get_last_contract_defaults,
)


def prepare_contract_input(
    client: GraphQLClient,
    registry: OperationRegistry,
    account_id: str,
    user_input: dict[str, Any] | None = None,
) -> str:
    """
    If user_input has full CreateQuoteInput fields, use it.
    Otherwise load lastContractDefaults for the account and merge.
    """
    defaults: dict[str, Any] | None = None
    defaults_error: str | None = None
    try:
        defaults = get_last_contract_defaults(client, registry, account_id)
    except Exception as exc:
        defaults_error = str(exc)
    merged = build_create_quote_input(account_id, user_input, defaults)
    source = "user_input" if user_input and _has_minimum(user_input) else "last_contract"
    if defaults is None and source != "user_input":
        source = "fallback"
    return json.dumps(
        {
            "source": source,
            "sourceContractId": (defaults or {}).get("sourceContractId"),
            "proposedInput": merged,
            "warnings": (
                ["LastContractDefaults unavailable; using provided/hardcoded input only."]
                if defaults_error
                else []
            ),
            "defaultsError": defaults_error,
        },
        indent=2,
    )


def create_contract_smart(
    client: GraphQLClient,
    registry: OperationRegistry,
    config: AppConfig,
    account_id: str,
    user_input: dict[str, Any] | None = None,
    confirmed: bool = False,
) -> str:
    """Prepare input (user or last contract) then create draft."""
    defaults: dict[str, Any] | None = None
    try:
        defaults = get_last_contract_defaults(client, registry, account_id)
    except Exception:
        defaults = None
    merged = build_create_quote_input(account_id, user_input, defaults)
    return create_draft_contract(client, registry, config, merged, confirmed)


def _has_minimum(data: dict[str, Any]) -> bool:
    return bool(
        data.get("quoteLines")
        and data.get("customerAccountId")
        and data.get("billToContactId")
    )
