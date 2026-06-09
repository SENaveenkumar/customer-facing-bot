---
chunk_type: STATUSES
id: contract-status-amendment_draft
title: Contract Status: Amendment Draft
tags: [contract, status, amendment_draft]
related: []
needs_validation: false
---

**Status:** AMENDMENT_DRAFT (Amendment Draft)

**Business Meaning:** An amendment has been priced but not submitted. Internal DXP status for mid-term changes to activated contracts.

**When This Status Occurs:** Status is set when the contract or amendment reaches this stage in the order lifecycle. Most transitions after submission are driven by Salesforce/Middleware events, not direct dealer action.

**Allowed Actions:** Reprice amendment, Save PO number, Place amendment order, Delete amendment draft

**Restricted Actions:** Submit initial sale

**Possible Next Statuses:** AMENDMENT_SUBMITTED, EXPIRED

**Typical User Questions:** What does Amendment Draft mean? Why is my contract in Amendment Draft status? How long will it stay in Amendment Draft?

**Example Support Response:** Your contract is currently in Amendment Draft status. An amendment has been priced but not submitted. Internal DXP status for mid-term changes to activated contracts. If you need to take action, you can: Reprice amendment, Save PO number, Place amendment order.
