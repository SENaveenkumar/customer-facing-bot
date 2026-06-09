from __future__ import annotations

from datetime import date, datetime
from typing import Any

from dxp_support_mcp.config import AppConfig
from dxp_support_mcp.graphql.allowlist import OperationRegistry
from dxp_support_mcp.graphql.client import GraphQLClient
from dxp_support_mcp.tools.contracts import get_contract


def build_contract_context(
    client: GraphQLClient,
    registry: OperationRegistry,
    config: AppConfig,
    contract_id: str,
) -> dict[str, Any]:
    raw = get_contract(client, registry, contract_id)
    contract = _unwrap_contract(raw)
    if not contract:
        raise ValueError(f"Contract not found: {contract_id}")

    dealer_account_id = _dealer_account_id(contract, config)
    customer_account_id = _nested_id(contract, "customer")

    cid = str(contract.get("id") or contract_id)
    status = (contract.get("status") or "").upper()
    contract_type = contract.get("type")
    status_change_reason = contract.get("statusChangeReason")
    approval_status = _normalize_optional(contract.get("approvalStatus"))
    renewal_date = contract.get("renewalDate")
    error_reason = contract.get("errorReason")
    days_to_renewal = _days_until(renewal_date)

    quotes = contract.get("quotes") or []
    quote_valid_until = None
    quote_approval_status = None
    if quotes and isinstance(quotes[0], dict):
        quote_valid_until = quotes[0].get("validUntilDate")
        quote_approval_status = _normalize_optional(quotes[0].get("approvalStatus"))

    effective_approval = approval_status or quote_approval_status

    blockers = _infer_blockers(
        status=status,
        contract_type=contract_type,
        error_reason=error_reason,
        status_change_reason=status_change_reason,
        approval_status=effective_approval,
        days_to_renewal=days_to_renewal,
    )

    return {
        "contractId": cid,
        "contractNumber": contract.get("contractNumber"),
        "status": status,
        "type": contract_type,
        "statusChangeReason": status_change_reason,
        "approvalStatus": effective_approval,
        "errorReason": error_reason,
        "renewalDate": renewal_date,
        "startDate": contract.get("startDate"),
        "termQuantity": contract.get("termQuantity"),
        "termUOM": contract.get("termUOM"),
        "autoRenew": contract.get("autoRenew"),
        "customerName": contract.get("customerName"),
        "dealerAccountId": dealer_account_id,
        "customerAccountId": customer_account_id,
        "purchaseOrderNumber": contract.get("purchaseOrderNumber"),
        "quotes": quotes,
        "quoteValidUntil": quote_valid_until,
        "netPriceTotal": contract.get("netPriceTotal"),
        "blockers": blockers,
        "daysToRenewal": days_to_renewal,
        "_rawContract": contract,
    }


def _unwrap_contract(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    if "contract" in raw:
        c = raw["contract"]
        return c if isinstance(c, dict) else None
    return raw


def _dealer_account_id(contract: dict[str, Any], config: AppConfig) -> str | None:
    bill_to = contract.get("billToAccount")
    if isinstance(bill_to, dict):
        aid = bill_to.get("id")
        if aid:
            return str(aid)
    if config.account_ids:
        return config.account_ids.split(",")[0].strip()
    return None


def _nested_id(contract: dict[str, Any], key: str) -> str | None:
    node = contract.get(key)
    if isinstance(node, dict) and node.get("id"):
        return str(node["id"])
    return None


def _normalize_optional(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text.upper() if text else None


def _days_until(iso_date: str | None) -> int | None:
    if not iso_date:
        return None
    try:
        target = datetime.fromisoformat(iso_date.replace("Z", "+00:00")).date()
    except ValueError:
        try:
            target = date.fromisoformat(iso_date[:10])
        except ValueError:
            return None
    return (target - date.today()).days


def _infer_blockers(
    *,
    status: str,
    contract_type: str | None,
    error_reason: str | None,
    status_change_reason: str | None,
    approval_status: str | None,
    days_to_renewal: int | None,
) -> list[str]:
    blockers: list[str] = []

    if status == "ERROR":
        blockers.append("contract_in_error_status")
    if error_reason:
        blockers.append(f"error_reason:{error_reason}")
    if status_change_reason:
        blockers.append(f"status_change_reason:{status_change_reason}")
    if status == "ON_HOLD":
        blockers.append("contract_on_hold")
    if approval_status == "PENDING":
        blockers.append("approval_pending")
    if approval_status == "REJECTED":
        blockers.append("approval_rejected")
    if status.startswith("AMENDMENT_") and status not in {
        "AMENDMENT_DRAFT",
        "AMENDMENT_ACTIVATED",
    }:
        blockers.append("amendment_in_progress")
    if contract_type and str(contract_type).upper() == "TRIAL":
        blockers.append("trial_contract")
    if days_to_renewal is not None and 0 <= days_to_renewal <= 8:
        blockers.append("renewal_blackout_window")

    return blockers
