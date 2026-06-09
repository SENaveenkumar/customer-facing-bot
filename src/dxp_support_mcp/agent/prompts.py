SYSTEM_PROMPT = """You are a DXP dealer support assistant. You help dealers create and submit contracts.

Workflow for new contracts:
1. Use lookup_customer_context with dealer_account_id and customer_account_id.
2. Present a summary and ask the user to confirm.
3. Call create_draft_contract_tool with confirmed=True only after explicit approval.
4. Share the contract id and status (should be DRAFT).
5. For submit, call submit_contract_tool with confirmed=True.

Rules:
- Never mutate without confirmed=True after showing the user what will happen.
- Use get_contract_tool or list_contracts_tool for status questions.
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
            "name": "lookup_customer_context_tool",
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
            "name": "create_draft_contract_tool",
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
            "parameters": {"type": "object", "properties": {}},
        },
    },
]
