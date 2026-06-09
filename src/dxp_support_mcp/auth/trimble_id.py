from __future__ import annotations

import base64
import time
from typing import Any

import httpx

from dxp_support_mcp.config import AppConfig


class TrimbleIdTokenProvider:
    """OAuth2 client-credentials token provider for Trimble ID."""

    def __init__(self, config: AppConfig) -> None:
        self._config = config
        self._access_token: str | None = None
        self._expires_at: float = 0.0

    def get_access_token(self) -> str:
        if self._config.tid_token:
            return self._config.tid_token

        if not self._config.tid_client_id or not self._config.tid_client_secret:
            raise ValueError(
                "Set TID_TOKEN or TID_CLIENT_ID + TID_CLIENT_SECRET"
            )

        if self._access_token and time.time() < self._expires_at - 60:
            return self._access_token

        credentials = base64.b64encode(
            f"{self._config.tid_client_id}:{self._config.tid_client_secret}".encode()
        ).decode()

        with httpx.Client(timeout=30.0) as http:
            response = http.post(
                self._config.tid_token_url,
                headers={
                    "Authorization": f"Basic {credentials}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data={
                    "grant_type": "client_credentials",
                    "scope": self._config.tid_scope,
                },
            )

        if response.status_code >= 400:
            raise RuntimeError(f"TID token request failed: {response.text}")

        body: dict[str, Any] = response.json()
        token = body.get("access_token")
        if not token:
            raise RuntimeError("TID token response missing access_token")

        expires_in = int(body.get("expires_in", 3600))
        self._access_token = token
        self._expires_at = time.time() + expires_in
        return token
