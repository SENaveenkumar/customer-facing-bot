---
chunk_type: WORKFLOWS
id: customer-amendment
title: Customer-Initiated Amendment
tags: [amendment, axp, workflow]
related: []
needs_validation: false
---

**Purpose:** Process amendment requests from customer via AXP portal.

**Trigger:** Customer submits request in AXP; arrives via Service Bus.

**Steps:**
1. DXP receives positive or negative request.
2. Dealer notified via in-app notification and dashboard.
3. Positive: dealer accepts (flows to order management) or declines.
4. Negative: dealer can delete request.
5. Requests expire after 7 days if not actioned.

**Failure Scenarios:** Request expired, dealer declined, order management error.