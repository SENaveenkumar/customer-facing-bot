---
chunk_type: STATUSES
id: contract-status-draft
title: Contract Status: Draft
tags: [contract, status, draft]
related: []
needs_validation: false
---

**Status:** DRAFT (Draft)

**Business Meaning:** The contract has been priced but not yet submitted to order management. The dealer can edit pricing, add PO numbers, reprice, or delete the draft.

**When This Status Occurs:** Status is set when the contract or amendment reaches this stage in the order lifecycle. Most transitions after submission are driven by Salesforce/Middleware events, not direct dealer action.

**Allowed Actions:** Edit pricing, Reprice, Save PO number, Submit contract, Delete draft

**Restricted Actions:** Submit contract

**Possible Next Statuses:** SUBMITTED, EXPIRED, CANCELLED

**Typical User Questions:** What does Draft mean? Why is my contract in Draft status? How long will it stay in Draft?

**Example Support Response:** Your contract is currently in Draft status. The contract has been priced but not yet submitted to order management. The dealer can edit pricing, add PO numbers, reprice, or delete the draft. If you need to take action, you can: Edit pricing, Reprice, Save PO number.
