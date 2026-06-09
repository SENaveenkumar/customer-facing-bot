---
chunk_type: STATUSES
id: contract-status-pending_activation
title: Contract Status: Pending Activation
tags: [contract, status, pending_activation]
related: []
needs_validation: false
---

**Status:** PENDING_ACTIVATION (Pending Activation)

**Business Meaning:** The contract awaits end-customer activation. The account owner must accept their invitation and activate the subscription.

**When This Status Occurs:** Status is set when the contract or amendment reaches this stage in the order lifecycle. Most transitions after submission are driven by Salesforce/Middleware events, not direct dealer action.

**Allowed Actions:** Resend invitation, View activation status

**Restricted Actions:** Assign subscriptions to devices yet

**Possible Next Statuses:** ACTIVATION_IN_PROGRESS, ACTIVATED, CANCELLED

**Typical User Questions:** What does Pending Activation mean? Why is my contract in Pending Activation status? How long will it stay in Pending Activation?

**Example Support Response:** Your contract is currently in Pending Activation status. The contract awaits end-customer activation. The account owner must accept their invitation and activate the subscription. If you need to take action, you can: Resend invitation, View activation status.
