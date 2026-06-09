---
chunk_type: INTEGRATIONS
id: salesforce-overview
title: Salesforce Integration Overview
tags: [salesforce, integration]
related: []
needs_validation: true
---

DXP integrates with Salesforce through Middleware hub-and-spoke architecture. DXP sends quote/contract requests via REST Apex endpoints. Salesforce sends status, approval, and renewal events back via Azure Service Bus. Most contract status updates are event-driven, not real-time API polling. NEEDS VALIDATION: exact sync SLA timing.