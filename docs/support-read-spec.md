# Phase 2: `supportRead` GraphQL Query (Future DXP API)

This document specifies a generic read endpoint for the DXP GraphQL API. The MCP server in `dxp-support-mcp` can switch to this endpoint once it is implemented, replacing direct POST of allowlisted query documents.

## Proposed schema

```graphql
type Query {
  """
  Executes a pre-registered read-only operation by name.
  Used by support bots and MCP integrations.
  """
  supportRead(
    operationName: String!
    variables: JSON
  ): JSON! @authorize(policy: "View:Contract")
}
```

## Server-side requirements

| Requirement | Implementation |
|-------------|----------------|
| Persisted operations only | Map `operationName` → query document stored server-side (same set as MCP `operations/reads/`) |
| Read-only AST | Reject documents containing `mutation`, `subscription`, or introspection fields |
| Authorization | Reuse dealer permission middleware; scope to caller's CDH account IDs |
| Cost limits | Apply existing `@cost` / query depth limits |
| Audit | Log `operationName`, dealer account id, TID — no PII in log payload |
| Response | Return `data` JSON for the inner operation (not full GraphQL envelope) |

## MCP migration

When `supportRead` is available:

1. Add `operations/reads/SupportRead.graphql` wrapper (optional).
2. Update `dxpRead()` in `src/tools/dxp-read.ts` to call:

```graphql
query SupportRead($operationName: String!, $variables: JSON) {
  supportRead(operationName: $operationName, variables: $variables)
}
```

3. Keep client-side allowlist validation as defense in depth.

## Allowlisted operation names (initial)

- `GetContract`
- `ListContracts`
- `GetAccount`
- `GetDealerCustomer`
- `GetProducts`
