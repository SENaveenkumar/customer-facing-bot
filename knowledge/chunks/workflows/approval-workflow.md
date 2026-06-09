---
chunk_type: WORKFLOWS
id: approval-workflow
title: Discount and Billing Frequency Approval
tags: [approval, workflow]
related: []
needs_validation: false
---

**Purpose:** Handle holds when discount or billing frequency changes require order management approval.

**Trigger:** Reprice with discount outside auto-approve range, or billing frequency change.

**Steps:**
1. Approval Status set to Pending; contract/amendment On Hold.
2. Order management reviews in Salesforce.
3. Approved or Rejected event updates DXP.
4. Dealer can dismiss approval request or withdraw pending change.

**User Impact:** Contract stuck On Hold until approval resolves.