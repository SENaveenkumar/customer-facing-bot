SYSTEM_PROMPT = """You are a DXP dealer support assistant. You help dealers create and submit contracts.

Workflow for new contracts:
1. Use lookup_customer_context_tool with dealer_account_id and customer_account_id.
2. Present a summary and ask the user to confirm.
3. Call create_draft_contract_tool with confirmed=true only after explicit approval.
4. Share the contract id and status (should be DRAFT).
5. For submit, call submit_contract_tool with confirmed=true.

Rules:
- Never mutate without confirmed=true after showing the user what will happen.
- Use get_contract_tool or list_contracts_tool for status questions.
- For contract errors, renewal blockers, or "what next" questions, use explain_contract_tool.
- Use support_bot_sql_read_tool or support_bot_sql_template_tool for data lookups.
- Do not invent account IDs or product SKUs.
"""

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "dxp_read_tool",
            "description": "Execute allowlisted read GraphQL operation",
            "parameters": {
                "type": "object",
                "properties": {
                    "operation_name": {"type": "string"},
                    "variables": {"type": "object"},
                },
                "required": ["operation_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_contract_tool",
            "description": "Fetch a contract by ID",
            "parameters": {
                "type": "object",
                "properties": {"contract_id": {"type": "string"}},
                "required": ["contract_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_contracts_tool",
            "description": "List contracts for a dealer account",
            "parameters": {
                "type": "object",
                "properties": {
                    "account_id": {"type": "string"},
                    "first": {"type": "integer"},
                },
                "required": ["account_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "lookup_customer_context_tool",
            "description": "Load dealer account, customer, and products for drafting",
            "parameters": {
                "type": "object",
                "properties": {
                    "dealer_account_id": {"type": "string"},
                    "customer_account_id": {"type": "string"},
                    "term_uom": {"type": "string", "enum": ["MONTH", "YEAR"]},
                },
                "required": ["dealer_account_id", "customer_account_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "support_bot_sql_read_tool",
            "description": "Run read-only SQL via supportBotRead (must include :account_id)",
            "parameters": {
                "type": "object",
                "properties": {
                    "account_id": {"type": "string"},
                    "sql": {"type": "string"},
                    "max_rows": {"type": "integer"},
                },
                "required": ["account_id", "sql"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "support_bot_sql_template_tool",
            "description": "Run SQL from operations/sql/{template_name}.sql",
            "parameters": {
                "type": "object",
                "properties": {
                    "account_id": {"type": "string"},
                    "template_name": {"type": "string"},
                    "max_rows": {"type": "integer"},
                },
                "required": ["account_id", "template_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "renewal_eligible_contract_ids_tool",
            "description": "Return contract GUIDs eligible for renewal",
            "parameters": {
                "type": "object",
                "properties": {"account_id": {"type": "string"}},
                "required": ["account_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "prepare_contract_input_tool",
            "description": "Build CreateQuoteInput from user_input or last contract",
            "parameters": {
                "type": "object",
                "properties": {
                    "account_id": {"type": "string"},
                    "user_input": {"type": "object"},
                },
                "required": ["account_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_contract_smart_tool",
            "description": "Create draft using user_input or last-contract defaults",
            "parameters": {
                "type": "object",
                "properties": {
                    "account_id": {"type": "string"},
                    "user_input": {"type": "object"},
                    "confirmed": {"type": "boolean"},
                },
                "required": ["account_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_draft_contract_tool",
            "description": "Create a DRAFT contract (createDraftContract)",
            "parameters": {
                "type": "object",
                "properties": {
                    "input": {"type": "object"},
                    "confirmed": {"type": "boolean"},
                },
                "required": ["input"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "submit_contract_tool",
            "description": "Submit a DRAFT contract (convertContract)",
            "parameters": {
                "type": "object",
                "properties": {
                    "contract_id": {"type": "string"},
                    "purchase_order_number": {"type": "string"},
                    "confirmed": {"type": "boolean"},
                },
                "required": ["contract_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "explain_last_error_tool",
            "description": "Explain the most recent GraphQL error",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "explain_contract_tool",
            "description": "Answer contract support questions using live data and RAG",
            "parameters": {
                "type": "object",
                "properties": {
                    "contract_id": {"type": "string"},
                    "question": {"type": "string"},
                },
                "required": ["contract_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_contract_briefing_tool",
            "description": "Return full contract support briefing and next actions",
            "parameters": {
                "type": "object",
                "properties": {"contract_id": {"type": "string"}},
                "required": ["contract_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_knowledge_tool",
            "description": "Search RAG knowledge chunks without GraphQL calls",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "top_k": {"type": "integer"},
                },
                "required": ["query"],
            },
        },
    },
]
