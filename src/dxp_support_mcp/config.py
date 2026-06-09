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
    openai_api_key: str | None
    openai_base_url: str
    openai_model: str
    knowledge_dir: Path
    rag_top_k: int


def load_config() -> AppConfig:
    graphql_url = os.getenv("DXP_GRAPHQL_URL", "").strip()
    if not graphql_url:
        raise ValueError("DXP_GRAPHQL_URL is required")

    account_ids = os.getenv("DXP_ACCOUNT_IDS", "").strip() or None
    knowledge_dir = Path(
        os.getenv("KNOWLEDGE_DIR", str(PROJECT_ROOT / "knowledge" / "chunks"))
    ).resolve()

    return AppConfig(
        graphql_url=graphql_url,
        bearer_token=os.getenv("DXP_BEARER_TOKEN", "").strip(),
        account_ids=account_ids,
        strict_writes=os.getenv("MCP_STRICT_WRITES", "true").lower() != "false",
        openai_api_key=os.getenv("OPENAI_API_KEY") or None,
        openai_base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/"),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        knowledge_dir=knowledge_dir,
        rag_top_k=max(1, int(os.getenv("RAG_TOP_K", "5"))),
    )
