from __future__ import annotations

import json
import logging
from typing import Any

from dxp_support_mcp import state
from dxp_support_mcp.config import AppConfig
from dxp_support_mcp.graphql.allowlist import OperationRegistry
from dxp_support_mcp.graphql.client import GraphQLClient
from dxp_support_mcp.tools.contract_mutations import (
    create_draft_contract,
    explain_last_error,
    submit_contract,
)
from dxp_support_mcp.tools.contracts import (
    get_contract,
    list_contracts,
    list_top_dealer_dashboard_alerts,
    lookup_customer_context,
)
from dxp_support_mcp.tools.dxp_read import dxp_read
from dxp_support_mcp.tools.explain_contract import explain_contract, get_contract_briefing
from dxp_support_mcp.support.rag_retriever import KnowledgeIndex
from dxp_support_mcp.tools.smart_contract import (
    create_contract_smart,
    prepare_contract_input,
)

logger = logging.getLogger(__name__)


def _json_result(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, indent=2)


def run_tool(
    name: str,
    args: dict[str, Any],
    *,
    config: AppConfig,
    client: GraphQLClient,
    registry: OperationRegistry,
) -> str:
    try:
        logger.debug("runner.dispatch name=%s args_keys=%s", name, sorted(args.keys()))
        if name == "dxp_read_tool":
            result = _json_result(
                dxp_read(
                    client,
                    registry,
                    args["operation_name"],
                    args.get("variables"),
                )
            )
            logger.debug("runner.done name=%s result_chars=%d", name, len(result))
            return result
        if name == "get_contract_tool":
            result = _json_result(
                get_contract(client, registry, args["contract_id"])
            )
            logger.debug("runner.done name=%s result_chars=%d", name, len(result))
            return result
        if name == "list_contracts_tool":
            result = _json_result(
                list_contracts(
                    client,
                    registry,
                    args["account_id"],
                    args.get("first", 10),
                )
            )
            logger.debug("runner.done name=%s result_chars=%d", name, len(result))
            return result
        if name == "lookup_customer_context_tool":
            term = args.get("term_uom", "YEAR")
            if term not in ("MONTH", "YEAR"):
                term = "YEAR"
            result = _json_result(
                lookup_customer_context(
                    client,
                    registry,
                    args["dealer_account_id"],
                    args["customer_account_id"],
                    term,
                )
            )
        if name == "list_top_alerts_tool":
            first = max(1, min(int(args.get("first", 5)), 5))
            module = (args.get("module", "CONTRACT") or "CONTRACT").strip().upper()
            after = (args.get("after") or "").strip() or None
            search_term = (args.get("search_term") or "").strip() or None
            return _json_result(
                list_top_dealer_dashboard_alerts(
                    client,
                    registry,
                    first,
                    after,
                    search_term,
                    module,
                )
            )
            logger.debug("runner.done name=%s result_chars=%d", name, len(result))
            return result
        if name == "prepare_contract_input_tool":
            result = _json_result(
                prepare_contract_input(
                    client,
                    registry,
                    args["account_id"],
                    args.get("user_input"),
                )
            )
            logger.debug("runner.done name=%s result_chars=%d", name, len(result))
            return result
        if name == "create_contract_smart_tool":
            result = _json_result(
                create_contract_smart(
                    client,
                    registry,
                    config,
                    args["account_id"],
                    args.get("user_input"),
                    args.get("confirmed", False),
                )
            )
            logger.debug("runner.done name=%s result_chars=%d", name, len(result))
            return result
        if name == "create_draft_contract_tool":
            result = create_draft_contract(
                client,
                registry,
                config,
                args["input"],
                args.get("confirmed", False),
            )
            logger.debug("runner.done name=%s result_chars=%d", name, len(result))
            return result
        if name == "submit_contract_tool":
            result = submit_contract(
                client,
                registry,
                config,
                args["contract_id"],
                args.get("purchase_order_number"),
                args.get("confirmed", False),
            )
            logger.debug("runner.done name=%s result_chars=%d", name, len(result))
            return result
        if name == "explain_last_error_tool":
            result = explain_last_error(client)
            logger.debug("runner.done name=%s result_chars=%d", name, len(result))
            return result
        if name == "explain_contract_tool":
            result = _json_result(
                explain_contract(
                    client,
                    registry,
                    config,
                    args["contract_id"],
                    args.get("question"),
                )
            )
            logger.debug("runner.done name=%s result_chars=%d", name, len(result))
            return result
        if name == "get_contract_briefing_tool":
            result = _json_result(
                get_contract_briefing(
                    client,
                    registry,
                    config,
                    args["contract_id"],
                )
            )
            logger.debug("runner.done name=%s result_chars=%d", name, len(result))
            return result
        if name == "search_knowledge_tool":
            top_k = min(int(args.get("top_k", 5)), 10)
            index = KnowledgeIndex(config)
            chunks = index.retrieve(args["query"], context_tags=set(), top_k=top_k)
            result = _json_result(
                {
                    "query": args["query"],
                    "chunksLoaded": len(index.chunks()),
                    "results": [
                        {
                            "id": chunk.id,
                            "title": chunk.title,
                            "tags": list(chunk.tags),
                            "excerpt": chunk.content[:400],
                        }
                        for chunk in chunks
                    ],
                }
            )
            logger.debug("runner.done name=%s result_chars=%d", name, len(result))
            return result
        logger.warning("runner.unknown_tool name=%s", name)
        return json.dumps({"error": f"Unknown tool: {name}"})
    except Exception as exc:
        state.session_state["last_errors"] = client.get_last_errors()
        logger.exception("runner.error name=%s", name)
        return json.dumps({"error": str(exc)})
