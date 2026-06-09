from __future__ import annotations

import json
from typing import Any

import httpx

from dxp_support_mcp.agent.prompts import SYSTEM_PROMPT, TOOL_DEFINITIONS
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
    lookup_customer_context,
)
from dxp_support_mcp.tools.dxp_read import dxp_read


class SupportOrchestrator:
    def __init__(
        self,
        config: AppConfig,
        client: GraphQLClient,
        registry: OperationRegistry,
    ) -> None:
        self._config = config
        self._client = client
        self._registry = registry
        self._messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]

    def run_tool(self, name: str, args: dict[str, Any]) -> str:
        try:
            if name == "dxp_read_tool":
                return json.dumps(
                    dxp_read(
                        self._client,
                        self._registry,
                        args["operation_name"],
                        args.get("variables"),
                    ),
                    indent=2,
                )
            if name == "get_contract_tool":
                return json.dumps(
                    get_contract(self._client, self._registry, args["contract_id"]),
                    indent=2,
                )
            if name == "list_contracts_tool":
                return json.dumps(
                    list_contracts(
                        self._client,
                        self._registry,
                        args["account_id"],
                        args.get("first", 10),
                    ),
                    indent=2,
                )
            if name == "lookup_customer_context_tool":
                return json.dumps(
                    lookup_customer_context(
                        self._client,
                        self._registry,
                        args["dealer_account_id"],
                        args["customer_account_id"],
                        args.get("term_uom", "YEAR"),
                    ),
                    indent=2,
                )
            if name == "create_draft_contract_tool":
                return create_draft_contract(
                    self._client,
                    self._registry,
                    self._config,
                    args["input"],
                    args.get("confirmed", False),
                )
            if name == "submit_contract_tool":
                return submit_contract(
                    self._client,
                    self._registry,
                    self._config,
                    args["contract_id"],
                    args.get("purchase_order_number"),
                    args.get("confirmed", False),
                )
            if name == "explain_last_error_tool":
                return explain_last_error(self._client)
            return json.dumps({"error": f"Unknown tool: {name}"})
        except Exception as exc:
            return json.dumps({"error": str(exc)})

    def chat(self, user_message: str) -> str:
        if not self._config.openai_api_key:
            return (
                "OPENAI_API_KEY is not set. Use direct tools:\n"
                "  python -m dxp_support_mcp.cli tool lookup <dealerId> <customerId>\n"
                f"\nYour message: {user_message}"
            )

        self._messages.append({"role": "user", "content": user_message})

        for _ in range(8):
            with httpx.Client(timeout=120.0) as http:
                response = http.post(
                    f"{self._config.openai_base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self._config.openai_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self._config.openai_model,
                        "messages": self._messages,
                        "tools": TOOL_DEFINITIONS,
                        "tool_choice": "auto",
                    },
                )
            if response.status_code >= 400:
                raise RuntimeError(response.text)

            body = response.json()
            choice = body["choices"][0]["message"]

            if choice.get("tool_calls"):
                self._messages.append(
                    {"role": "assistant", "content": choice.get("content") or ""}
                )
                for call in choice["tool_calls"]:
                    fn = call["function"]
                    args = json.loads(fn.get("arguments") or "{}")
                    result = self.run_tool(fn["name"], args)
                    self._messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": call["id"],
                            "content": result,
                        }
                    )
                continue

            reply = choice.get("content") or ""
            self._messages.append({"role": "assistant", "content": reply})
            return reply

        return "Stopped after maximum tool rounds."
