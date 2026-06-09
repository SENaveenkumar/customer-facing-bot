from __future__ import annotations

from typing import Any, Literal

from dxp_support_mcp.graphql.allowlist import OperationRegistry
from dxp_support_mcp.graphql.client import GraphQLClient
from dxp_support_mcp.tools.dxp_read import dxp_read


def get_contract(
    client: GraphQLClient, registry: OperationRegistry, contract_id: str
) -> Any:
    return dxp_read(client, registry, "GetContract", {"id": contract_id})


def list_contracts(
    client: GraphQLClient,
    registry: OperationRegistry,
    account_id: str,
    first: int = 10,
) -> Any:
    return dxp_read(
        client, registry, "ListContracts", {"accountId": account_id, "first": first}
    )


def list_products_by_account(
    client: GraphQLClient,
    registry: OperationRegistry,
    account_id: str,
    term_uom: Literal["MONTH", "YEAR"] = "YEAR",
    contract_type: Literal["NEW", "RENEWAL", "AMENDMENT"] = "NEW",
    currency_id: str | None = None,
) -> Any:
    variables: dict[str, Any] = {
        "accountId": account_id,
        "termUom": term_uom,
        "contractType": contract_type,
    }
    if currency_id:
        variables["currencyId"] = currency_id
    return dxp_read(client, registry, "ListProductsByAccount", variables)


def lookup_customer_context(
    client: GraphQLClient,
    registry: OperationRegistry,
    dealer_account_id: str,
    customer_account_id: str,
    term_uom: Literal["MONTH", "YEAR"] = "YEAR",
) -> dict[str, Any]:
    account = dxp_read(
        client,
        registry,
        "GetAccount",
        {"id": dealer_account_id},
        dealer_account_id=dealer_account_id,
    )
    customer = dxp_read(
        client,
        registry,
        "GetDealerCustomer",
        {
            "dealerAccountId": dealer_account_id,
            "customerAccountId": customer_account_id,
        },
    )
    products = dxp_read(
        client,
        registry,
        "GetProducts",
        {
            "accountId": dealer_account_id,
            "termUom": term_uom,
            "contractType": "NEW",
        },
    )
    return {"account": account, "customer": customer, "products": products}
