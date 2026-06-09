---
chunk_type: INTEGRATIONS
id: sf-product-sync
title: Salesforce Product Catalog Sync
tags: [salesforce, product]
related: []
needs_validation: false
---

Direction: Salesforce to DXP. Trigger: product events on dxp.product.events topic. Consumer: ProductSyncService Azure Function. Syncs products, pricing, bundles, add-ons to DXP database. User sees current product catalog and pricing. Failure: outdated products until sync completes.