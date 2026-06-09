---
chunk_type: INTEGRATIONS
id: events-service-iam
title: Trimble Events Service (IAM)
tags: [events, iam]
related: []
needs_validation: false
---

No direct Kafka SDK. DXP consumes IAM events via Trimble Cloud Events Service. Namespace: com.trimble.tcp.iam. Events: update_user_account, delete_user_account, update_account_account. Poll interval: 100ms-2s adaptive. Impact: invitation status updates, permission cache refresh, opt-in status changes.