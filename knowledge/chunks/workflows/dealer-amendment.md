---
chunk_type: WORKFLOWS
id: dealer-amendment
title: Dealer-Initiated Amendment
tags: [amendment, workflow]
related: []
needs_validation: false
---

**Purpose:** Change an activated contract mid-term (add seats, upgrade, downgrade).

**Trigger:** Dealer creates amendment on activated contract.

**Prerequisites:** Contract Activated, no pending amendment, no active customer requests, not in renewal, not trial, not within 8 days of renewal date.

**Steps:**
1. Create amendment draft with desired changes.
2. Reprice if needed; save PO number.
3. Place amendment order.
4. If price change hold: approve and resubmit pricing.
5. Status: Amendment Submitted → Amendment Activated.

**Failure Scenarios:** Contract not amendable, future start date conflicts, product compatibility errors.