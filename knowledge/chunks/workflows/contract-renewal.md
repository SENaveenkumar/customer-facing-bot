---
chunk_type: WORKFLOWS
id: contract-renewal
title: Contract Renewal
tags: [renewal, workflow]
related: []
needs_validation: false
---

**Purpose:** Renew an expiring or expired contract.

**Trigger:** Dealer starts renewal manually, or auto-renewal initiated by Salesforce.

**Prerequisites:** Contract Activated or Expired, renewal date in valid window (Early/Regular/Late), no pending amendment.

**Renewal Windows (Annual):** Early: 90-61 days before; Regular: 60-0 days; Late: 1-30 days after.
**Renewal Windows (Monthly):** Early: 30-15 days; Regular: 14-0 days; Late: 1-30 days after.

**Steps:**
1. Start renewal → Renewal Initiated.
2. Salesforce creates renewal quote (event-driven).
3. Dealer edits renewal quote (term, end date, promo, renewal type).
4. Submit renewal contract.
5. Renewal Completed when activated.

**Failure Scenarios:** Renewal date out of range, renewal already in progress, trial contract.