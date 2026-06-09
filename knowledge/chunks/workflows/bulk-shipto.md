---
chunk_type: WORKFLOWS
id: bulk-shipto
title: Bulk Ship-To Updates
tags: [customer, workflow]
related: []
needs_validation: false
---

**Purpose:** Update ship-to contact or address across all customer contracts when defaults change.

**Trigger:** Customer default ship-to changes, or organization verification with address update.

**Steps:**
1. Bulk operation initiated.
2. Updates sent to Salesforce via Service Bus.
3. Status events report Processing → Completed or Failed.
4. Retry available for failed individual contract address updates.