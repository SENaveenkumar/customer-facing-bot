"""HTTP chat API. Run: python -m dxp_support_mcp.chat_api"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from dxp_support_mcp.agent.orchestrator import SupportOrchestrator
from dxp_support_mcp.config import load_config
from dxp_support_mcp.graphql.allowlist import OperationRegistry
from dxp_support_mcp.graphql.client import GraphQLClient
from dxp_support_mcp.logging_utils import configure_logging
from dxp_support_mcp.paths import PROJECT_ROOT

configure_logging()
logger = logging.getLogger(__name__)

config = load_config()
registry = OperationRegistry.load(PROJECT_ROOT)
graphql_client = GraphQLClient(config)

_sessions: dict[str, SupportOrchestrator] = {}


def _get_or_create_session(session_id: str | None) -> tuple[str, SupportOrchestrator]:
    if session_id and session_id in _sessions:
        logger.debug("session.reuse id=%s", session_id)
        return session_id, _sessions[session_id]

    new_id = session_id or str(uuid.uuid4())
    orch = SupportOrchestrator(config, graphql_client, registry, session_id=new_id)
    _sessions[new_id] = orch
    logger.info("session.create id=%s", new_id)
    return new_id, orch


app = FastAPI(
    title="DXP Support Chat API",
    description=(
        "Chat API backed by Trimble Model Gateway (claude-4.5-sonnet) "
        "with DXP MCP tool execution."
    ),
    version="0.1.0",
)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    session_id: str | None = None


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    model: str


class SessionResponse(BaseModel):
    session_id: str


class HealthResponse(BaseModel):
    status: str
    model: str
    model_gateway: str


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        model=config.trimble_model,
        model_gateway=config.trimble_model_gateway_url,
    )


@app.post("/v1/sessions", response_model=SessionResponse)
def create_session() -> SessionResponse:
    session_id, _ = _get_or_create_session(None)
    return SessionResponse(session_id=session_id)


@app.delete("/v1/sessions/{session_id}")
def delete_session(session_id: str) -> dict[str, str]:
    if session_id in _sessions:
        del _sessions[session_id]
        return {"status": "deleted"}
    raise HTTPException(status_code=404, detail="Session not found")


@app.post("/v1/sessions/{session_id}/reset")
def reset_session(session_id: str) -> dict[str, str]:
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    _sessions[session_id].reset()
    return {"status": "reset"}


@app.post("/v1/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    try:
        session_id, orch = _get_or_create_session(request.session_id)
        logger.info("chat.request session_id=%s message_chars=%d", session_id, len(request.message))
        reply = orch.chat(request.message)
        logger.info("chat.reply session_id=%s reply_chars=%d", session_id, len(reply))
    except Exception as exc:
        logger.exception("chat.error session_id=%s", request.session_id)
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return ChatResponse(
        session_id=session_id,
        reply=reply,
        model=config.trimble_model,
    )


@app.post("/v1/chat/completions")
def chat_completions_proxy(body: dict[str, Any]) -> dict[str, Any]:
    """OpenAI-compatible passthrough without local MCP tools (for testing gateway auth)."""
    from dxp_support_mcp.agent.model_gateway import ModelGatewayClient
    from dxp_support_mcp.auth.trimble_id import TrimbleIdTokenProvider

    try:
        logger.info("chat.proxy.request keys=%s", sorted(body.keys()))
        gateway = ModelGatewayClient(config, TrimbleIdTokenProvider(config))
        return gateway.create_chat_completion(body)
    except Exception as exc:
        logger.exception("chat.proxy.error")
        raise HTTPException(status_code=502, detail=str(exc)) from exc


def main() -> None:
    import uvicorn

    uvicorn.run(
        "dxp_support_mcp.chat_api:app",
        host=config.chat_api_host,
        port=config.chat_api_port,
        reload=False,
    )


if __name__ == "__main__":
    main()
