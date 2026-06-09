---
chunk_type: WORKFLOWS
id: dcountry-hold
title: D-Country Regulatory Hold
tags: [compliance, workflow]
related: []
needs_validation: false
---

**Purpose:** Handle regulatory compliance holds for certain countries.

**Trigger:** Contract placed On Hold with D-Country reason from Salesforce.

**Steps:**
1. Dealer and/or customer notified.
2. Dealer submits D-Country hold form (Annual or Individual type).
3. Forms reviewed; contract proceeds or is cancelled.

**Failure Scenarios:** Form rejected, manual cancellation by dealer.