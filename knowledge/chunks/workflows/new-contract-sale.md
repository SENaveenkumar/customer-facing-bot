---
chunk_type: WORKFLOWS
id: new-contract-sale
title: New Contract Sale
tags: [contract, workflow]
related: []
needs_validation: false
---

**Purpose:** Sell a new subscription to a customer.

**Trigger:** Dealer selects Create Contract.

**Prerequisites:** Customer exists with verified organization and ship-to address. Dealer has Create and Manage Contract permission.

**Steps:**
1. Dealer creates draft contract with products, term, and billing frequency.
2. System prices the contract via Salesforce.
3. Dealer optionally reprices, applies promo/discount, saves PO number.
4. If discount or billing frequency change requires approval, contract may go On Hold until approved.
5. Dealer submits (converts) the contract.
6. Status progresses: Submitted → Pending Activation → Activation In Progress → Activated.
7. Dealer assigns subscriptions to devices or users.

**Decision Points:** Approval required? D-Country hold? Trial eligibility?

**Outcomes:** Activated contract with assignable subscriptions, or On Hold/Error/Cancelled.

**Failure Scenarios:** Missing organization, expired quote (30 days), pending approval blocks submission.