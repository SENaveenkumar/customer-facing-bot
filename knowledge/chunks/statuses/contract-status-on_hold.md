---
chunk_type: STATUSES
id: contract-status-on_hold
title: Contract Status: On Hold
tags: [contract, status, on_hold]
related: []
needs_validation: false
---

**Status:** ON_HOLD (On Hold)

**Business Meaning:** Order management has placed a hold on the contract. Common reasons: price change approval required, D-Country regulatory hold, or billing frequency change pending.

**When This Status Occurs:** Status is set when the contract or amendment reaches this stage in the order lifecycle. Most transitions after submission are driven by Salesforce/Middleware events, not direct dealer action.

**Allowed Actions:** View hold reason, Submit D-Country form if applicable, Dismiss or withdraw approval requests

**Restricted Actions:** Submit new order

**Possible Next Statuses:** SUBMITTED, CANCELLED, PENDING_ACTIVATION

**Typical User Questions:** What does On Hold mean? Why is my contract in On Hold status? How long will it stay in On Hold?

**Example Support Response:** Your contract is currently in On Hold status. Order management has placed a hold on the contract. Common reasons: price change approval required, D-Country regulatory hold, or billing frequency change pending. If you need to take action, you can: View hold reason, Submit D-Country form if applicable, Dismiss or withdraw approval requests.
