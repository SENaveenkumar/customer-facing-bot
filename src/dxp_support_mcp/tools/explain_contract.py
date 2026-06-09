from __future__ import annotations

import json
from typing import Any

from dxp_support_mcp.config import AppConfig
from dxp_support_mcp.graphql.allowlist import OperationRegistry
from dxp_support_mcp.graphql.client import GraphQLClient
from dxp_support_mcp.support.explain_pipeline import explain_contract_response


def explain_contract(
    client: GraphQLClient,
    registry: OperationRegistry,
    config: AppConfig,
    contract_id: str,
    question: str | None = None,
) -> str:
    result = explain_contract_response(
        client, registry, config, contract_id, question, briefing=False
    )
    return json.dumps(result, indent=2)


def get_contract_briefing(
    client: GraphQLClient,
    registry: OperationRegistry,
    config: AppConfig,
    contract_id: str,
) -> str:
    result = explain_contract_response(
        client, registry, config, contract_id, question=None, briefing=True
    )
    return json.dumps(result, indent=2)
