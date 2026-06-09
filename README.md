# DXP Support MCP (Python)

MCP server and support chatbot for the DXP GraphQL API. Helps dealers create draft contracts and submit them using the same mutations and queries as the web app.

**Does not modify** `bussys-dxp-gql-dotnet` — standalone sibling project.

## Stack

- **Python 3.11+**
- **[MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)** (`FastMCP`)
- **httpx** for GraphQL HTTP calls

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
| `list_products_by_account_tool` | Products for a dealer account (`products`) |
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

Optional env: `KNOWLEDGE_DIR`, `RAG_TOP_K`, `OPENAI_API_KEY`.

## Local chat CLI

```bash
# AI chat (needs OPENAI_API_KEY)
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
