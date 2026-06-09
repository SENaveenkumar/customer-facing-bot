---
chunk_type: ROLES
id: dealer-permission-model
title: Dealer Permission Model
tags: [permission, iam]
related: []
needs_validation: false
---

DXP uses IAM permissions in Category:Action format. Categories: Contract, Customer, Dealer, Device, Subscription, Notification, EmailSettings, Invoice, Audit, Organization. Actions: View, CreateAndManage, OptInAndManage, SecondaryOwnerManage, ManageSettings. Users need both the correct permission AND resource ownership (contract/device belongs to their dealer account).