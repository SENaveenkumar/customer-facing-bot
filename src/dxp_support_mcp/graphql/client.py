from __future__ import annotations

from typing import Any

import httpx

from dxp_support_mcp.config import AppConfig

# Must match bussys-dxp-gql-dotnet ApiConstants.Headers.AccountIds
ACCOUNT_IDS_HEADER = "dxp-Account-Ids"


def resolve_account_ids(
    variables: dict[str, Any] | None,
    explicit: str | None,
    config_default: str | None,
) -> str | None:
    """Pick dealer account id for the dxp-Account-Ids header."""
    if explicit and explicit.strip():
        return explicit.strip()
    if variables:
        for key in ("accountId", "account_id", "dealerAccountId"):
            value = variables.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        nested = variables.get("input")
        if isinstance(nested, dict):
            bill_to = nested.get("billToAccountId")
            if isinstance(bill_to, str) and bill_to.strip():
                return bill_to.strip()
    if config_default and config_default.strip():
        return config_default.strip()
    return None


class GraphQLClient:
    def __init__(self, config: AppConfig, token_override: str | None = None) -> None:
        self._config = config
        self._token_override = token_override
        self._last_errors: list[dict[str, Any]] | None = None

    def set_bearer_token(self, token: str) -> None:
        self._token_override = token

    def get_last_errors(self) -> list[dict[str, Any]] | None:
        return self._last_errors

    def execute(
        self,
        query: str,
        variables: dict[str, Any] | None = None,
        operation_name: str | None = None,
        account_ids: str | None = None,
    ) -> Any:
        token = (self._token_override or self._config.bearer_token).strip()
        if not token:
            raise ValueError(
                "No bearer token. Set DXP_BEARER_TOKEN or pass token to the client."
            )

        auth = token if token.lower().startswith("bearer ") else f"Bearer {token}"
        body: dict[str, Any] = {"query": query, "variables": variables or {}}
        if operation_name:
            body["operationName"] = operation_name

        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "Authorization": auth,
        }
        resolved_account_ids = resolve_account_ids(
            variables, account_ids, self._config.account_ids
        )
        if resolved_account_ids:
            headers[ACCOUNT_IDS_HEADER] = resolved_account_ids

        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                self._config.graphql_url,
                json=body,
                headers=headers,
            )

        if response.status_code >= 400:
            raise RuntimeError(f"GraphQL HTTP {response.status_code}: {response.text}")

        payload = response.json()
        errors = payload.get("errors")
        if errors:
            self._last_errors = errors
            messages = "; ".join(e.get("message", str(e)) for e in errors)
            raise RuntimeError(f"GraphQL errors: {messages}")

        self._last_errors = None
        return payload.get("data")
