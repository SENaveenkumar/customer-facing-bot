"""Interactive support chat CLI. Run: python -m dxp_support_mcp.cli"""

from __future__ import annotations

import json
import sys

from dxp_support_mcp.agent.orchestrator import SupportOrchestrator
from dxp_support_mcp.config import load_config
from dxp_support_mcp.graphql.allowlist import OperationRegistry
from dxp_support_mcp.graphql.client import GraphQLClient
from dxp_support_mcp.paths import PROJECT_ROOT


def _run_direct_tool(orch: SupportOrchestrator, parts: list[str]) -> str:
    cmd = parts[0] if parts else ""
    rest = parts[1:]

    if cmd == "lookup":
        return orch.run_tool(
            "lookup_customer_context_tool",
            {
                "dealer_account_id": rest[0],
                "customer_account_id": rest[1],
                "term_uom": rest[2] if len(rest) > 2 else "YEAR",
            },
        )
    if cmd == "contract":
        return orch.run_tool("get_contract_tool", {"contract_id": rest[0]})
    if cmd == "list":
        return orch.run_tool(
            "list_contracts_tool",
            {"account_id": rest[0], "first": int(rest[1]) if len(rest) > 1 else 10},
        )
    if cmd == "read":
        variables = json.loads(rest[1]) if len(rest) > 1 else {}
        return orch.run_tool(
            "dxp_read_tool",
            {"operation_name": rest[0], "variables": variables},
        )
    return orch.run_tool(cmd, json.loads(" ".join(rest) or "{}"))


def main() -> None:
    config = load_config()
    registry = OperationRegistry.load(PROJECT_ROOT)
    client = GraphQLClient(config)
    orch = SupportOrchestrator(config, client, registry)

    if len(sys.argv) > 1 and sys.argv[1] == "tool":
        print(_run_direct_tool(orch, sys.argv[2:]))
        return

    print("DXP Support Chat (exit to quit, help for commands)\n")
    if not config.openai_api_key:
        print("Tip: set OPENAI_API_KEY for AI chat, or: python -m dxp_support_mcp.cli tool ...\n")

    while True:
        try:
            line = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line:
            continue
        if line in ("exit", "quit"):
            break
        if line == "help":
            print(
                "Commands:\n"
                "  Natural language (needs OPENAI_API_KEY)\n"
                "  tool lookup <dealerAccountId> <customerAccountId>\n"
                "  tool contract <contractId>\n"
                "  tool list <accountId>\n"
                "  exit"
            )
            continue
        if line.startswith("tool "):
            print(_run_direct_tool(orch, line.split()[1:]), "\n")
            continue
        print(f"\nassistant> {orch.chat(line)}\n")


if __name__ == "__main__":
    main()
