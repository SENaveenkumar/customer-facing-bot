from __future__ import annotations

import json
from typing import Any

from dxp_support_mcp.config import AppConfig
from dxp_support_mcp.graphql.allowlist import OperationRegistry
from dxp_support_mcp.graphql.client import GraphQLClient
from dxp_support_mcp import state


def _require_confirmation(
    config: AppConfig,
    confirmed: bool,
    action_type: str,
    summary: str,
    payload: dict[str, Any],
) -> str | None:
    if not config.strict_writes or confirmed:
        state.session_state["pending_action"] = None
        return None

    state.session_state["pending_action"] = {
        "type": action_type,
        "summary": summary,
        "payload": payload,
    }
    return json.dumps(
        {
            "status": "confirmation_required",
            "message": "Set confirmed=true after reviewing this action with the user.",
            "summary": summary,
            "payload": payload,
        },
        indent=2,
    )


def create_draft_contract(
    client: GraphQLClient,
    registry: OperationRegistry,
    config: AppConfig,
    input_data: dict[str, Any],
    confirmed: bool = False,
) -> str:
    summary = (
        f"Create draft contract for customer {input_data.get('customerAccountId')} "
        f"with {len(input_data.get('quoteLines', []))} line(s), "
        f"term {input_data.get('termQuantity')} {input_data.get('termUOM')}"
    )
    blocked = _require_confirmation(
        config, confirmed, "create_draft_contract", summary, {"input": input_data}
    )
    if blocked:
        return blocked

    op = registry.get_write("CreateDraftContract")
    data = client.execute(
        op.document,
        {"input": input_data},
        "CreateDraftContract",
        account_ids=input_data.get("billToAccountId"),
    )
    return json.dumps(data.get("createDraftContract"), indent=2)


def submit_contract(
    client: GraphQLClient,
    registry: OperationRegistry,
    config: AppConfig,
    contract_id: str,
    purchase_order_number: str | None = None,
    confirmed: bool = False,
) -> str:
    po_part = f" with PO {purchase_order_number}" if purchase_order_number else ""
    summary = f"Submit (convert) contract {contract_id}{po_part}"
    blocked = _require_confirmation(
        config,
        confirmed,
        "submit_contract",
        summary,
        {"contractId": contract_id, "purchaseOrderNumber": purchase_order_number},
    )
    if blocked:
        return blocked

    op = registry.get_write("ConvertContract")
    variables: dict[str, Any] = {"id": contract_id}
    if purchase_order_number is not None:
        variables["purchaseOrderNumber"] = purchase_order_number

    data = client.execute(op.document, variables, "ConvertContract")
    return json.dumps(data.get("convertContract"), indent=2)


def explain_last_error(client: GraphQLClient) -> str:
    errors = client.get_last_errors() or state.session_state.get("last_errors")
    if not errors:
        return json.dumps({"message": "No recent GraphQL errors recorded."}, indent=2)

    hints: list[str] = []
    for err in errors:
        msg = err.get("message", "")
        code = (err.get("extensions") or {}).get("code")
        if code == "AUTH_NOT_AUTHORIZED":
            hints.append(
                "Set DXP_ACCOUNT_IDS (dxp-Account-Ids header) to the dealer CDH account id, "
                "or pass accountId on the tool. Also verify JWT has DXP scope and View:Contract."
            )
        if "already converted" in msg:
            hints.append("Contract may not be in DRAFT; use get_contract to check status.")
        if "expired" in msg.lower():
            hints.append("Quote may be expired; create a new draft or reprice.")

    return json.dumps({"errors": errors, "hints": hints}, indent=2)
