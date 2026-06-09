"""Contract support: live context + RAG knowledge + synthesis."""

from dxp_support_mcp.support.context_builder import build_contract_context
from dxp_support_mcp.support.explain_pipeline import explain_contract_response

__all__ = ["build_contract_context", "explain_contract_response"]
