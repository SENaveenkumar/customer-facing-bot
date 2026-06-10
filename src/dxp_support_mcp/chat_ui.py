"""Simple Gradio chat UI. Run: python -m dxp_support_mcp.chat_ui"""

from __future__ import annotations

import os

import gradio as gr
import httpx

from dxp_support_mcp.agent.orchestrator import SupportOrchestrator
from dxp_support_mcp.config import load_config
from dxp_support_mcp.graphql.allowlist import OperationRegistry
from dxp_support_mcp.graphql.client import GraphQLClient
from dxp_support_mcp.paths import PROJECT_ROOT

config = load_config()
_api_base = os.getenv("CHAT_API_URL", "").rstrip("/")
_use_api = bool(_api_base)

if _use_api:
    _session_id: str | None = None
else:
    _registry = OperationRegistry.load(PROJECT_ROOT)
    _graphql_client = GraphQLClient(config)
    _orchestrator = SupportOrchestrator(config, _graphql_client, _registry)


def _chat_via_api(message: str, _history: list) -> str:
    global _session_id
    payload: dict[str, str] = {"message": message}
    if _session_id:
        payload["session_id"] = _session_id

    with httpx.Client(timeout=180.0) as http:
        response = http.post(f"{_api_base}/v1/chat", json=payload)

    if response.status_code >= 400:
        return f"API error ({response.status_code}): {response.text}"

    body = response.json()
    _session_id = body["session_id"]
    return body["reply"]


def _chat_direct(message: str, _history: list) -> str:
    return _orchestrator.chat(message)


def _reset() -> None:
    global _session_id
    if _use_api:
        if _session_id:
            try:
                with httpx.Client(timeout=30.0) as http:
                    http.post(f"{_api_base}/v1/sessions/{_session_id}/reset")
            except httpx.HTTPError:
                pass
        _session_id = None
    else:
        _orchestrator.reset()


def _build_ui() -> gr.Blocks:
    with gr.Blocks(title="DXP Chatbot") as demo:
        gr.Markdown("# DXP Chatbot")

        chat = gr.ChatInterface(
            fn=_chat_via_api if _use_api else _chat_direct,
            chatbot=gr.Chatbot(height=620),
            examples=[
                "Want to create a new draft contract?",
                "Show 5 important updates or alerts from my dealer dashboard",
            ],
        )

        with gr.Row():
            reset_btn = gr.Button("New conversation", variant="secondary")
            reset_status = gr.Markdown("")

        def on_reset() -> str:
            _reset()
            return "Conversation cleared."

        reset_btn.click(on_reset, outputs=reset_status)

    return demo


def main() -> None:
    port = int(os.getenv("CHAT_UI_PORT", "7860"))
    demo = _build_ui()
    demo.launch(
        server_name=os.getenv("CHAT_UI_HOST", "127.0.0.1"),
        server_port=port,
        share=False,
    )


if __name__ == "__main__":
    main()
