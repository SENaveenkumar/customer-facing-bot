"""MCP server entrypoint (stdio). Run: python -m dxp_support_mcp.mcp_server"""

from __future__ import annotations

import json
from typing import Any

from mcp.server.fastmcp import FastMCP

from dxp_support_mcp.config import load_config
from dxp_support_mcp.graphql.allowlist import OperationRegistry
from dxp_support_mcp.graphql.client import GraphQLClient
from dxp_support_mcp.paths import PROJECT_ROOT
from dxp_support_mcp import state
from dxp_support_mcp.tools.contract_mutations import (
    create_draft_contract,
    explain_last_error,
    submit_contract,
)
from dxp_support_mcp.tools.contracts import (
    get_contract,
    list_contracts,
    lookup_customer_context,
)
from dxp_support_mcp.tools.dxp_read import dxp_read
from dxp_support_mcp.tools.smart_contract import (
    create_contract_smart,
    prepare_contract_input,
)
from dxp_support_mcp.tools.explain_contract import explain_contract, get_contract_briefing

config = load_config()
registry = OperationRegistry.load(PROJECT_ROOT)
client = GraphQLClient(config)

mcp = FastMCP(
    name="dxp-support",
    instructions=(
        "DXP dealer support assistant. Use lookup_customer_context before creating contracts. "
        "For contract errors, status, renewal, or next-step questions use explain_contract_tool "
        "with the contract id. Mutations require confirmed=true when strict writes are enabled."
    ),
)

READ_OPS = registry.list_read_names()


def _json_result(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, indent=2)


def _handle(fn):
    def wrapper(*args, **kwargs):
        try:
            return _json_result(fn(*args, **kwargs))
        except Exception as exc:
            state.session_state["last_errors"] = client.get_last_errors()
            return json.dumps({"error": str(exc)}, indent=2)

    return wrapper


@mcp.tool(
    description=f"Execute an allowlisted read-only GraphQL operation. Allowed: {', '.join(READ_OPS)}"
)
def dxp_read_tool(
    operation_name: str,
    variables: dict[str, Any] | None = None,
) -> str:
    """Run a persisted read query by operation name."""
    return _handle(dxp_read)(client, registry, operation_name, variables)


@mcp.tool()
def get_contract_tool(contract_id: str) -> str:
    """Fetch a contract by ID (DRAFT, SUBMITTED, etc.)."""
    return _handle(get_contract)(client, registry, contract_id)


@mcp.tool()
def list_contracts_tool(account_id: str, first: int = 10) -> str:
    """List contracts for a dealer account (contractsV2)."""
    return _handle(list_contracts)(client, registry, account_id, first)


@mcp.tool()
def lookup_customer_context_tool(
    dealer_account_id: str,
    customer_account_id: str,
    term_uom: str = "YEAR",
) -> str:
    """Load dealer account, customer, and products for drafting a contract."""
    term: Any = term_uom if term_uom in ("MONTH", "YEAR") else "YEAR"
    return _handle(lookup_customer_context)(
        client, registry, dealer_account_id, customer_account_id, term
    )


@mcp.tool()
def prepare_contract_input_tool(
    account_id: str,
    user_input: dict[str, Any] | None = None,
) -> str:
    """Build CreateQuoteInput from user_input, or from last contract on this account if omitted."""
    return _handle(prepare_contract_input)(
        client, registry, account_id, user_input
    )


@mcp.tool()
def create_contract_smart_tool(
    account_id: str,
    user_input: dict[str, Any] | None = None,
    confirmed: bool = False,
) -> str:
    """Create draft using user_input or last-contract defaults for this account_id."""
    return _handle(create_contract_smart)(
        client, registry, config, account_id, user_input, confirmed
    )


@mcp.tool()
def create_draft_contract_tool(
    input: dict[str, Any],
    confirmed: bool = False,
) -> str:
    """Create a DRAFT contract (createDraftContract). Set confirmed=true after user approval."""
    return _handle(create_draft_contract)(client, registry, config, input, confirmed)


@mcp.tool()
def submit_contract_tool(
    contract_id: str,
    purchase_order_number: str | None = None,
    confirmed: bool = False,
) -> str:
    """Submit a DRAFT contract (convertContract). Set confirmed=true after user approval."""
    return _handle(submit_contract)(
        client, registry, config, contract_id, purchase_order_number, confirmed
    )


@mcp.tool()
def explain_last_error_tool() -> str:
    """Explain the most recent GraphQL error with support hints."""
    return explain_last_error(client)


@mcp.tool()
def explain_contract_tool(contract_id: str, question: str | None = None) -> str:
    """Answer any contract support question using live GraphQL facts + RAG knowledge.

    Combines contract data (status, errorReason, renewalDate, eligibility) with knowledge chunks.
    Works for errors, next steps, renewal/amendment eligibility, discounts, device transfer, etc.
    Examples: 'Why is there an error?', 'What should I do next?', 'Why not eligible for renewal?'
    """
    return _handle(explain_contract)(client, registry, config, contract_id, question)


@mcp.tool()
def get_contract_briefing_tool(contract_id: str) -> str:
    """Full contract support briefing: status, dates, eligibility, blockers, and recommended actions."""
    return _handle(get_contract_briefing)(client, registry, config, contract_id)


@mcp.tool()
def search_knowledge_tool(query: str, top_k: int = 5) -> str:
    """Search RAG knowledge chunks without calling GraphQL (debug / general DXP questions)."""
    from dxp_support_mcp.support.rag_retriever import KnowledgeIndex

    index = KnowledgeIndex(config)
    chunks = index.retrieve(query, context_tags=set(), top_k=min(top_k, 10))
    return _json_result(
        {
            "query": query,
            "chunksLoaded": len(index.chunks()),
            "results": [
                {"id": c.id, "title": c.title, "tags": list(c.tags), "excerpt": c.content[:400]}
                for c in chunks
            ],
        }
    )


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
