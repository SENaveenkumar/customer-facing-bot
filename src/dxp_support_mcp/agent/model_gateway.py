from __future__ import annotations

from typing import Any

import httpx

from dxp_support_mcp.auth.trimble_id import TrimbleIdTokenProvider
from dxp_support_mcp.config import AppConfig


class ModelGatewayClient:
    """Trimble Model Gateway client (OpenAI-compatible /openai/v1)."""

    def __init__(self, config: AppConfig, token_provider: TrimbleIdTokenProvider) -> None:
        self._config = config
        self._token_provider = token_provider

    @property
    def chat_completions_url(self) -> str:
        return f"{self._config.trimble_model_gateway_url}/openai/v1/chat/completions"

    def create_chat_completion(self, payload: dict[str, Any]) -> dict[str, Any]:
        request = dict(payload)
        if "max_tokens" not in request and "max_completion_tokens" not in request:
            request["max_tokens"] = self._config.trimble_max_tokens

        token = self._token_provider.get_access_token()
        with httpx.Client(timeout=120.0) as http:
            response = http.post(
                self.chat_completions_url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json=request,
            )

        if response.status_code >= 400:
            raise RuntimeError(
                f"Model Gateway error ({response.status_code}): {response.text}"
            )

        return response.json()
