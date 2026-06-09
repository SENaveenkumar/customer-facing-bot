---
chunk_type: INTEGRATIONS
id: sf-contract-status
title: Salesforce Contract Status Events
tags: [salesforce, contract]
related: []
needs_validation: false
---

Direction: Salesforce to DXP via Middleware. Event: contract.status.changed. Updates DXP contract status (Submitted, On Hold, Pending Activation, etc.). User sees status change in contract list and receives notification. Failure: status stuck until event reprocessed.