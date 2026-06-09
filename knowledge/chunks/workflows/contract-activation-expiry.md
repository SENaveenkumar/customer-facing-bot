---
chunk_type: WORKFLOWS
id: contract-activation-expiry
title: Contract Activation and Expiry
tags: [contract, workflow]
related: []
needs_validation: false
---

**Purpose:** Manage contract lifecycle completion and draft expiry.

**Activation:** Customer owner accepts invitation → Pending Activation → Activated.

**Draft Expiry:** Unsubmitted drafts expire after 30 days (background job every 10 minutes).

**Amendment Expiry:** On-hold amendments auto-cancelled if reprice window (24h before start) passes.

**Customer Request Expiry:** Positive requests expire after 7 days.