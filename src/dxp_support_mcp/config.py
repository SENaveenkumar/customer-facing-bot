import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from dxp_support_mcp.paths import PROJECT_ROOT

load_dotenv()


@dataclass(frozen=True)
class AppConfig:
    graphql_url: str
    bearer_token: str
    """Default dealer CDH account id(s) for dxp-Account-Ids header (comma-separated)."""
    account_ids: str | None
    strict_writes: bool
    knowledge_dir: Path
    rag_top_k: int
    rag_vector_top_n: int
    rag_vector_db_dir: Path
    rag_embedding_model: str
    trimble_model_gateway_url: str
    trimble_model: str
    trimble_max_tokens: int
    tid_token_url: str
    tid_client_id: str | None
    tid_client_secret: str | None
    tid_scope: str
    tid_token: str | None
    chat_api_host: str
    chat_api_port: int
    max_tool_rounds: int


def load_config() -> AppConfig:
    graphql_url = os.getenv("DXP_GRAPHQL_URL", "").strip()
    if not graphql_url:
        raise ValueError("DXP_GRAPHQL_URL is required")

    account_ids = os.getenv("DXP_ACCOUNT_IDS", "").strip() or None
    knowledge_dir = Path(
        os.getenv("KNOWLEDGE_DIR", str(PROJECT_ROOT / "knowledge" / "chunks"))
    ).resolve()
    rag_vector_db_dir = Path(
        os.getenv("RAG_VECTOR_DB_DIR", str(PROJECT_ROOT / ".rag_db"))
    ).resolve()

    return AppConfig(
        graphql_url=graphql_url,
        bearer_token=os.getenv("DXP_BEARER_TOKEN", "").strip(),
        account_ids=account_ids,
        strict_writes=os.getenv("MCP_STRICT_WRITES", "true").lower() != "false",
        knowledge_dir=knowledge_dir,
        rag_top_k=max(1, int(os.getenv("RAG_TOP_K", "5"))),
        rag_vector_top_n=max(5, int(os.getenv("RAG_VECTOR_TOP_N", "20"))),
        rag_vector_db_dir=rag_vector_db_dir,
        rag_embedding_model=os.getenv(
            "RAG_EMBEDDING_MODEL", "sentence-transformers/all-mpnet-base-v2"
        ),
        trimble_model_gateway_url=os.getenv(
            "TRIMBLE_MODEL_GATEWAY_URL", "https://models.dev.trimble-ai.com"
        ).rstrip("/"),
        trimble_model=os.getenv("TRIMBLE_MODEL", "claude-4.5-sonnet"),
        trimble_max_tokens=int(os.getenv("TRIMBLE_MAX_TOKENS", "4096")),
        tid_token_url=os.getenv(
            "TID_TOKEN_URL", "https://stage.id.trimblecloud.com/oauth/token"
        ).rstrip("/"),
        tid_client_id=os.getenv("TID_CLIENT_ID") or None,
        tid_client_secret=os.getenv("TID_CLIENT_SECRET") or None,
        tid_scope=os.getenv("TID_SCOPE", "openid models profile"),
        tid_token=os.getenv("TID_TOKEN") or None,
        chat_api_host=os.getenv("CHAT_API_HOST", "0.0.0.0"),
        chat_api_port=int(os.getenv("CHAT_API_PORT", "8080")),
        max_tool_rounds=int(os.getenv("MAX_TOOL_ROUNDS", "16")),
    )
