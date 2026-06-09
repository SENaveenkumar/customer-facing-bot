---
chunk_type: DATA_OWNERSHIP
id: contract-status
title: Contract Status
tags: [contract, ownership]
related: []
needs_validation: false
---

**System of Record:** Salesforce (via Middleware). **Update Source:** Service Bus status events. **Sync:** Event-driven (seconds to minutes). **User Editable:** No. **Reason:** Managed by order management. **Impact:** Dealer sees status update after event processed.