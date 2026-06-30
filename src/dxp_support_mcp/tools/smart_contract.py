from __future__ import annotations

import json
from typing import Any

from dxp_support_mcp.config import AppConfig
from dxp_support_mcp.graphql.allowlist import OperationRegistry
from dxp_support_mcp.graphql.client import GraphQLClient
from dxp_support_mcp.tools.contract_mutations import create_draft_contract
from dxp_support_mcp.tools.support_bot import build_create_quote_input


def prepare_contract_input(
    client: GraphQLClient,
    registry: OperationRegistry,
    account_id: str,
    user_input: dict[str, Any] | None = None,
) -> str:
    """
    If user_input has full CreateQuoteInput fields, use it.
    Otherwise merge user_input onto the hardcoded default profile.
    """
    merged = build_create_quote_input(account_id, user_input)
    source = "user_input" if user_input and _has_minimum(user_input) else "fallback"
    return json.dumps(
        {
            "source": source,
            "proposedInput": merged,
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
    """Merge user_input with default profile, then create draft."""
    merged = build_create_quote_input(account_id, user_input)
    return create_draft_contract(client, registry, config, merged, confirmed)


def _has_minimum(data: dict[str, Any]) -> bool:
    return bool(
        data.get("quoteLines")
        and data.get("customerAccountId")
        and data.get("billToContactId")
    )
