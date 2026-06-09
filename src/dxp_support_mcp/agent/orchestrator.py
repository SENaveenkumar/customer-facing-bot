from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from dxp_support_mcp.agent.model_gateway import ModelGatewayClient
from dxp_support_mcp.agent.prompts import SYSTEM_PROMPT, TOOL_DEFINITIONS
from dxp_support_mcp.auth.trimble_id import TrimbleIdTokenProvider
from dxp_support_mcp.config import AppConfig
from dxp_support_mcp.graphql.allowlist import OperationRegistry
from dxp_support_mcp.graphql.client import GraphQLClient
from dxp_support_mcp.tools.runner import run_tool

logger = logging.getLogger(__name__)


class SupportOrchestrator:
    def __init__(
        self,
        config: AppConfig,
        client: GraphQLClient,
        registry: OperationRegistry,
        *,
        session_id: str | None = None,
    ) -> None:
        self._config = config
        self._client = client
        self._registry = registry
        self.session_id = session_id or str(uuid.uuid4())
        self._token_provider = TrimbleIdTokenProvider(config)
        self._model_gateway = ModelGatewayClient(config, self._token_provider)
        self._messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]
        logger.debug("orchestrator.init session_id=%s", self.session_id)

    def run_tool(self, name: str, args: dict[str, Any]) -> str:
        logger.info("tool.call session_id=%s name=%s", self.session_id, name)
        logger.debug("tool.call.args session_id=%s name=%s args=%s", self.session_id, name, args)
        return run_tool(
            name,
            args,
            config=self._config,
            client=self._client,
            registry=self._registry,
        )

    def _has_inference_credentials(self) -> bool:
        return bool(
            self._config.tid_token
            or (self._config.tid_client_id and self._config.tid_client_secret)
        )

    def chat(self, user_message: str) -> str:
        logger.info("orchestrator.chat.start session_id=%s message_chars=%d", self.session_id, len(user_message))
        if not self._has_inference_credentials():
            logger.warning("orchestrator.chat.no_credentials session_id=%s", self.session_id)
            return (
                "Trimble inference is not configured. Set TID_TOKEN or "
                "TID_CLIENT_ID + TID_CLIENT_SECRET.\n"
                "Direct tools: python -m dxp_support_mcp.cli tool lookup <dealerId> <customerId>\n"
                f"\nYour message: {user_message}"
            )

        self._messages.append({"role": "user", "content": user_message})

        for round_idx in range(self._config.max_tool_rounds):
            logger.debug(
                "orchestrator.round session_id=%s round=%d messages=%d",
                self.session_id,
                round_idx + 1,
                len(self._messages),
            )
            body = self._model_gateway.create_chat_completion(
                {
                    "model": self._config.trimble_model,
                    "messages": self._messages,
                    "tools": TOOL_DEFINITIONS,
                    "tool_choice": "auto",
                }
            )
            choice = body["choices"][0]["message"]

            if choice.get("tool_calls"):
                logger.info(
                    "orchestrator.tool_calls session_id=%s count=%d",
                    self.session_id,
                    len(choice["tool_calls"]),
                )
                assistant_message: dict[str, Any] = {
                    "role": "assistant",
                    "content": choice.get("content") or "",
                    "tool_calls": choice["tool_calls"],
                }
                self._messages.append(assistant_message)

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
            logger.info("orchestrator.chat.done session_id=%s reply_chars=%d", self.session_id, len(reply))
            return reply

        logger.warning("orchestrator.chat.max_rounds session_id=%s", self.session_id)
        return "Stopped after maximum tool rounds."

    def reset(self) -> None:
        self._messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        logger.info("orchestrator.reset session_id=%s", self.session_id)
