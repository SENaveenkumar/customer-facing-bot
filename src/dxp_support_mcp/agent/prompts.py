SYSTEM_PROMPT = """You are a DXP dealer support assistant. You help dealers create and submit contracts.

Workflow for new contracts:
1. If user asks to create a new draft contract, start by calling list_products_by_account_tool.
2. Ask the user to choose product(s) and quantity.
3. Build the draft payload and present a clear summary.
4. Call create_draft_contract_tool with confirmed=true only after explicit approval.
5. Share the contract id and status (should be DRAFT).
6. For submit, call submit_contract_tool with confirmed=true.

Rules:
- Never mutate without confirmed=true after showing the user what will happen.
- Use get_contract_tool or list_contracts_tool for status questions.
- For product-list requests (no specific customer context), use list_products_by_account_tool.
- For drafting context (account + customer + products together), use lookup_customer_context_tool.
- If customer id is missing for a product-list request, do not ask for it; continue with dealer-account product listing.
- For dashboard alert requests (for example "top 5 alerts"), use list_top_alerts_tool.
- For notification requests (for example "top 10 notifications for account id X"), call dxp_read_tool with operation_name="Notifications" and variables:
  {"accountId":"X","first":10,"after":"LTE=","order":[{"notificationStatus":"DESC"},{"createdDateTime":"DESC"}]}.
- For device requests (for example "top 20 devices for dealer account id X"), call dxp_read_tool with operation_name="DevicesV2" and variables:
  {"dealerAccountId":"X","initialise":false,"first":20,"after":"LTE=","order":[],"unassignedOnly":false}.
- For dealer dashboard alert summaries, prefer list_top_alerts_tool before asking follow-up questions.
- For contract errors, renewal blockers, or "what next" questions, use explain_contract_tool.
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
            "name": "list_products_by_account_tool",
            "description": "List products for a dealer account only (customer id not required)",
            "parameters": {
                "type": "object",
                "properties": {
                    "account_id": {"type": "string"},
                    "term_uom": {"type": "string", "enum": ["MONTH", "YEAR"]},
                    "contract_type": {
                        "type": "string",
                        "enum": ["NEW", "RENEWAL", "AMENDMENT"],
                    },
                    "currency_id": {"type": "string"},
                },
                "required": ["account_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_top_alerts_tool",
            "description": "List top unresolved/unignored dealer dashboard alerts (default top 5)",
            "parameters": {
                "type": "object",
                "properties": {
                    "first": {"type": "integer"},
                    "after": {"type": "string"},
                    "search_term": {"type": "string"},
                    "module": {"type": "string"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "lookup_customer_context_tool",
            "description": "Load dealer account + specific customer + products for contract drafting",
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
