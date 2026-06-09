# DXP Support MCP (Python)

MCP server and support chatbot for the DXP GraphQL API. Helps dealers create draft contracts and submit them using the same mutations and queries as the web app.

**Does not modify** `bussys-dxp-gql-dotnet` — standalone sibling project.

## Stack

- **Python 3.11+**
- **[MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)** (`FastMCP`)
- **Trimble Model Gateway** (`claude-4.5-sonnet` via `/openai/v1/chat/completions`)
- **Trimble ID** OAuth2 (stage: `https://stage.id.trimblecloud.com`)
- **FastAPI** chat API + **httpx** for HTTP calls

## Setup

```bash
cd BE-repo/dxp-support-mcp
python -m venv .venv

# Windows
.venv\Scripts\activate

pip install -e .
cp .env.example .env
# Edit .env: DXP_GRAPHQL_URL, DXP_BEARER_TOKEN, DXP_ACCOUNT_IDS
```

## Run MCP server (Cursor)

```bash
# With venv activated and PYTHONPATH=src, or after pip install -e .
python -m dxp_support_mcp.mcp_server
```

Add to Cursor MCP settings (see `mcp-config.example.json`):

```json
{
  "mcpServers": {
    "dxp-support": {
      "command": "python",
      "args": ["-m", "dxp_support_mcp.mcp_server"],
      "cwd": "<absolute-path>/dxp-support-mcp",
      "env": {
        "PYTHONPATH": "<absolute-path>/dxp-support-mcp/src",
        "DXP_GRAPHQL_URL": "https://your-dxp-host/graphql",
        "DXP_BEARER_TOKEN": "<jwt>",
        "DXP_ACCOUNT_IDS": "<dealer-cdh-account-id>",
        "MCP_STRICT_WRITES": "true"
      }
    }
  }
}
```

## MCP tools

| Tool | Description |
|------|-------------|
| `dxp_read_tool` | Generic allowlisted read (`GetContract`, `ListContracts`, …) |
| `prepare_contract_input_tool` | Build `CreateQuoteInput` from user input or last contract |
| `create_contract_smart_tool` | Create draft using user input or last-contract defaults |
| `get_contract_tool` | Contract by ID |
| `list_contracts_tool` | `contractsV2` for dealer account |
| `lookup_customer_context_tool` | Account + customer + products for drafting |
| `create_draft_contract_tool` | `createDraftContract` mutation |
| `submit_contract_tool` | `convertContract` mutation |
| `explain_last_error_tool` | Hints from last GraphQL error |
| `explain_contract_tool` | RAG + live contract facts — any support question by contract id |
| `get_contract_briefing_tool` | Full briefing (status, eligibility, blockers, next steps) |
| `search_knowledge_tool` | Search knowledge chunks without GraphQL |

When `MCP_STRICT_WRITES=true`, mutations require `confirmed=true` after user review.

## RAG contract explanations

`explain_contract_tool` and `get_contract_briefing_tool` combine live GraphQL data with knowledge under `knowledge/chunks/`.

```bash
# Generate knowledge base (first time)
python knowledge/generate_kb.py

# Ask about a contract (rule-based without OPENAI_API_KEY; richer with it)
python -m dxp_support_mcp.cli tool explain_contract_tool "{\"contract_id\":\"<guid>\",\"question\":\"Why not eligible for renewal?\"}"
python -m dxp_support_mcp.cli tool get_contract_briefing_tool "{\"contract_id\":\"<guid>\"}"
```

Optional env: `KNOWLEDGE_DIR`, `RAG_TOP_K`, `RAG_VECTOR_TOP_N`, `RAG_VECTOR_DB_DIR`, `RAG_EMBEDDING_MODEL`.
## Chat API (Trimble Model Gateway)

Uses [Trimble Model Gateway](https://developer.ai.trimble.com/api/models-inference/) with `claude-4.5-sonnet`, TID OAuth, and local MCP tool execution.

```bash
# Configure .env (see .env.example):
#   TRIMBLE_MODEL_GATEWAY_URL=https://models.dev.trimble-ai.com
#   TID_TOKEN=<paste TID access token manually>
#   Or: TID_CLIENT_ID / TID_CLIENT_SECRET (auto-fetch via OAuth)

python -m dxp_support_mcp.chat_api
# or: dxp-support-api
```

**Endpoints:**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/v1/sessions` | POST | Create chat session |
| `/v1/chat` | POST | Send message (`{"message": "...", "session_id": "optional"}`) |
| `/v1/sessions/{id}/reset` | POST | Clear conversation history |
| `/v1/chat/completions` | POST | Raw Model Gateway passthrough (no MCP tools) |

## Chat UI (Gradio)

Simple browser chat to test without curl or Swagger.

```bash
# Direct mode (uses .env, no separate API server needed)
python -m dxp_support_mcp.chat_ui
# or: dxp-support-ui
```

Open **http://127.0.0.1:7860** in your browser.

To talk to a running Chat API instead, set in `.env`:

```env
CHAT_API_URL=http://localhost:8080
```

Then start the API (`python -m dxp_support_mcp.chat_api`) and the UI in separate terminals.

## Local chat CLI

```bash
# AI chat (needs TID_TOKEN or TID client credentials)
python -m dxp_support_mcp.cli

# Direct tools without LLM
python -m dxp_support_mcp.cli tool lookup <dealerAccountId> <customerAccountId>
python -m dxp_support_mcp.cli tool contract <contractId>
python -m dxp_support_mcp.cli tool list <accountId>
```

## Project layout

```
dxp-support-mcp/
├── src/dxp_support_mcp/
│   ├── support/            # RAG pipeline (context, intent, retriever, synthesizer)
│   └── tools/              # MCP tool implementations
├── knowledge/
│   ├── generate_kb.py      # Build chunks from DXP domain knowledge
│   └── chunks/             # Markdown RAG chunks (run generate_kb.py)
├── operations/
│   ├── reads/              # Allowlisted queries
│   └── writes/             # Mutations (tool-only)
├── docs/support-read-spec.md
└── pyproject.toml
```

## Contract workflow

1. `lookup_customer_context_tool` — gather bill-to, customer, products
2. `create_draft_contract_tool` — first call returns confirmation payload if strict writes enabled
3. `create_draft_contract_tool` with `confirmed=true` — creates DRAFT
4. `submit_contract_tool` with `confirmed=true` — submits via `convertContract`

## Future: `supportRead` on DXP API

See [docs/support-read-spec.md](docs/support-read-spec.md).
