from __future__ import annotations

from typing import Any

from dxp_support_mcp.graphql.allowlist import OperationRegistry
from dxp_support_mcp.graphql.client import GraphQLClient


def dxp_read(
    client: GraphQLClient,
    registry: OperationRegistry,
    operation_name: str,
    variables: dict[str, Any] | None = None,
    dealer_account_id: str | None = None,
) -> Any:
    op = registry.get_read(operation_name)
    return client.execute(
        op.document,
        variables,
        operation_name,
        account_ids=dealer_account_id,
    )
