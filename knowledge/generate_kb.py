#!/usr/bin/env python3
"""Generate DXP RAG knowledge base chunks from structured data."""
import os
from pathlib import Path

BASE = Path(__file__).parent
CHUNKS = BASE / "chunks"

def write_chunk(category: str, chunk_id: str, title: str, tags: list, content: str, related=None, needs_validation=False):
    frontmatter = f"""---
chunk_type: {category.upper().replace('-', '_') if category != 'business-rules' else 'BUSINESS_RULE'}
id: {chunk_id}
title: {title}
tags: [{', '.join(tags)}]
related: [{', '.join(related or [])}]
needs_validation: {str(needs_validation).lower()}
---

"""
    path = CHUNKS / category / f"{chunk_id}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(frontmatter + content, encoding="utf-8")

# --- ENTITY CHUNKS ---
entities = {
    "contract": ("Contract", ["contract", "subscription", "order"],
        "A Contract represents a dealer's subscription agreement with an end customer. It includes contract number, status, term, billing frequency, pricing totals, purchase order number, renewal settings, and links to the customer account. Contracts progress from Draft through Submitted to Activated. Dealers create and manage contracts; final status updates come from Salesforce via Middleware events."),
    "quote": ("Quote", ["contract", "amendment", "pricing"],
        "A Quote is a priced proposal attached to a contract. Quote types include Initial Sale, Amendment, Renewal, Trial, Multi-Year, and Co-Term. Quotes have validity dates, approval status for discounts, and line items with SKU quantities and pricing. Dealers work with quotes while contracts are in draft or amendment states."),
    "contract-line": ("Contract Line (Subscription)", ["contract", "subscription", "license"],
        "A Contract Line represents a subscription SKU on a contract—quantity, product, list price, and net price. Contract lines are the source of licenses that dealers assign to devices or users. Each line tracks how many entitlements are available versus assigned."),
    "positive-request": ("Positive Request", ["amendment", "customer-request"],
        "A Positive Request is a customer-initiated amendment request from the AXP customer portal asking to add products, seats, or upgrades. The dealer receives a notification, reviews the request, and can accept (processed through order management) or decline it."),
    "negative-request": ("Negative Request", ["amendment", "customer-request", "downgrade"],
        "A Negative Request is a customer-initiated request to downgrade or cancel subscription quantities. Dealers can delete negative requests. These flow from AXP through Service Bus to DXP."),
    "dealer-customer": ("Dealer Customer", ["customer", "account"],
        "A Dealer Customer links a dealer account to an end-customer account. Includes company name, admin contact, organization, opt-in status, and default ship-to settings. Dealers create new customers or link existing IAM customers."),
    "account": ("Dealer Account", ["dealer", "account"],
        "A Dealer Account is the reseller's own business account in DXP. Stores company name, currency, pricing country, bill-to defaults, and portfolio access types from Salesforce. Each dealer user operates within one or more dealer accounts."),
    "user": ("User", ["customer", "role", "invitation"],
        "A User is a person on a customer account with a role: Owner, Secondary Owner, Admin, or Product User. Users have invitation and commitment status. Owners and Admins cannot receive subscription assignments; Secondary Owners and Product Users can."),
    "dealer-device": ("Dealer Device", ["device", "inventory"],
        "A Dealer Device is hardware in the dealer's inventory—serial number, part number, device type (IoT or Non-IoT), transfer status, and dealer reference label. Devices can be transferred to customers and have subscriptions assigned."),
    "device-transfer-request": ("Customer Device Transfer Request", ["device", "transfer"],
        "When a customer requests to claim a device from dealer inventory, a transfer request is created. Statuses: Requested, Approved, Declined, Cancelled, Failed. Dealer approves or declines through DXP."),
    "superkey": ("SuperKey", ["device", "license", "trial"],
        "A SuperKey is a temporary multi-SKU entitlement key on a dealer-owned device, limited to 5 uses per device. Dealers create, add SKUs to, and revoke superkeys for demonstration or evaluation purposes."),
    "product": ("Product", ["catalog", "sku"],
        "A Product is a subscription SKU from the Salesforce-synchronized catalog. Includes description, family, type (Base or Add-on), subscription model (Seat-based or Account-based), trial flag, and country-specific pricing."),
    "dealer-invoice": ("Dealer Invoice", ["invoice", "billing"],
        "A Dealer Invoice shows billing information for a contract—invoicenumber, total with tax, balance, and download URL. Invoices are read-only in DXP; sourced from external billing. NEEDS VALIDATION: exact billing system name."),
    "bulk-operation": ("Bulk Operation", ["customer", "ship-to"],
        "Bulk Operations update ship-to contact or address across multiple contracts for a customer. Statuses: Processing, Completed, Failed. Triggered when customer defaults change."),
    "notification": ("Notification", ["notification", "alert"],
        "In-app notifications alert dealers to contract status changes, renewals, customer requests, approvals, device events, and opt-in updates. Dealers can mark read and configure preferences by category and event."),
    "attention-event": ("Attention Event (Dashboard)", ["dashboard", "alert"],
        "Dashboard Attention Events highlight items needing dealer action: contract errors, on-hold orders, expiring contracts, pending device assignments, and transfer requests. Dealers can ignore resolved items."),
    "organization": ("Organization", ["customer", "iam"],
        "An Organization is the customer's business entity in Trimble IAM. Must be verified before contracts, amendments, or renewals. Dealers create, assign, and verify organizations for customers."),
    "address": ("Address", ["customer", "ship-to", "bill-to"],
        "Addresses include ship-to and bill-to locations with street, city, state, country, and postal code. Ship-to address is required before transactional operations. Validated through address services."),
}

for eid, (title, tags, content) in entities.items():
    write_chunk("entities", eid, title, tags, content)

# --- STATUS CHUNKS (Contract lifecycle) ---
contract_statuses = {
    "DRAFT": ("Draft", "The contract has been priced but not yet submitted to order management. The dealer can edit pricing, add PO numbers, reprice, or delete the draft.",
              ["Edit pricing", "Reprice", "Save PO number", "Submit contract", "Delete draft"],
              ["Submit contract"], ["SUBMITTED", "EXPIRED", "CANCELLED"]),
    "SUBMITTED": ("Submitted", "The dealer has submitted the contract as an order. It is being processed by order management and Salesforce.",
                  ["View status", "Wait for activation"],
                  ["Edit pricing", "Delete draft"], ["ON_HOLD", "PENDING_ACTIVATION", "ERROR", "CANCELLED"]),
    "ON_HOLD": ("On Hold", "Order management has placed a hold on the contract. Common reasons: price change approval required, D-Country regulatory hold, or billing frequency change pending.",
                ["View hold reason", "Submit D-Country form if applicable", "Dismiss or withdraw approval requests"],
                ["Submit new order"], ["SUBMITTED", "CANCELLED", "PENDING_ACTIVATION"]),
    "PENDING_ACTIVATION": ("Pending Activation", "The contract awaits end-customer activation. The account owner must accept their invitation and activate the subscription.",
                           ["Resend invitation", "View activation status"],
                           ["Assign subscriptions to devices yet"], ["ACTIVATION_IN_PROGRESS", "ACTIVATED", "CANCELLED"]),
    "ACTIVATION_IN_PROGRESS": ("Activation In Progress", "Customer activation has started and is being processed.",
                               ["Monitor status", "Prepare device/subscription assignment"],
                               [], ["ACTIVATED", "ERROR"]),
    "ACTIVATED": ("Activated", "The contract is live and ready for customer use. Subscriptions can be assigned to devices or users.",
                  ["Create amendment", "Start renewal", "Assign subscriptions", "Transfer devices", "Update auto-renew"],
                  ["Edit draft pricing"], ["AMENDMENT_DRAFT", "RENEWAL states via renewal workflow"]),
    "ERROR": ("Error", "A processing error occurred during contract lifecycle. Check dashboard attention events and status reason for details.",
              ["Contact support", "Review dashboard alerts"],
              ["Most edits"], ["May return to processing states depending on resolution"]),
    "EXPIRED": ("Expired", "The contract draft expired before submission. Draft quotes are valid for 30 days.",
                ["Create new contract", "Start renewal if previously activated contract expired"],
                ["Submit expired draft"], ["DRAFT recreation"]),
    "CANCELLED": ("Cancelled", "The contract was cancelled before or during activation. May result from manual cancellation, D-Country rejection, or auto-cancellation rules.",
                  ["View cancellation reason", "Create new contract if needed"],
                  ["Reactivate"], []),
    "AMENDMENT_DRAFT": ("Amendment Draft", "An amendment has been priced but not submitted. Internal DXP status for mid-term changes to activated contracts.",
                        ["Reprice amendment", "Save PO number", "Place amendment order", "Delete amendment draft"],
                        ["Submit initial sale"], ["AMENDMENT_SUBMITTED", "EXPIRED"]),
    "AMENDMENT_SUBMITTED": ("Amendment Submitted", "The dealer submitted an amendment order for processing.",
                            ["Monitor status", "Cancel amendment if needed"],
                            [], ["AMENDMENT_ON_HOLD", "AMENDMENT_ACTIVATION_IN_PROGRESS", "AMENDMENT_ACTIVATED"]),
    "AMENDMENT_ON_HOLD": ("Amendment On Hold", "The amendment is blocked by order management, often for price change approval.",
                          ["Approve and resubmit pricing", "View hold reason"],
                          [], ["AMENDMENT_SUBMITTED", "AMENDMENT_ACTIVATION_IN_PROGRESS", "AMENDMENT_CANCELLED"]),
    "AMENDMENT_ACTIVATION_IN_PROGRESS": ("Amendment Activation In Progress", "The amendment activation process has started.",
                                         ["Monitor status"],
                                         [], ["AMENDMENT_ACTIVATED", "AMENDMENT_ACTIVATION_AWAITING_START_DATE", "ERROR"]),
    "AMENDMENT_ACTIVATION_AWAITING_START_DATE": ("Amendment Awaiting Start Date", "Amendment is activated in Salesforce but has a future start date. Will become fully active when start date passes.",
                                                 ["Wait for start date", "View scheduled activation date"],
                                                 [], ["AMENDMENT_ACTIVATED"]),
    "AMENDMENT_ACTIVATED": ("Amendment Activated", "The amendment is live. New quantities and products are available for assignment.",
                            ["Assign new subscriptions", "View updated contract"],
                            [], []),
}

for sid, (name, meaning, allowed, restricted, next_s) in contract_statuses.items():
    content = f"""**Status:** {sid} ({name})

**Business Meaning:** {meaning}

**When This Status Occurs:** Status is set when the contract or amendment reaches this stage in the order lifecycle. Most transitions after submission are driven by Salesforce/Middleware events, not direct dealer action.

**Allowed Actions:** {', '.join(allowed) if allowed else 'Monitor only'}

**Restricted Actions:** {', '.join(restricted) if restricted else 'None specific to this status'}

**Possible Next Statuses:** {', '.join(next_s) if next_s else 'Terminal or workflow-dependent'}

**Typical User Questions:** What does {name} mean? Why is my contract in {name} status? How long will it stay in {name}?

**Example Support Response:** Your contract is currently in {name} status. {meaning} If you need to take action, you can: {', '.join(allowed[:3]) if allowed else 'monitor the status for updates'}.
"""
    write_chunk("statuses", f"contract-status-{sid.lower()}", f"Contract Status: {name}", ["contract", "status", sid.lower()], content)

# Renewal statuses
renewal_statuses = {
    "RENEWAL_INITIATED": "The dealer has started the renewal process. A renewal quote will be created in Salesforce.",
    "RENEWAL_IN_PROGRESS": "Renewal quote exists and dealer is editing or preparing to submit the renewal contract.",
    "RENEWAL_COMPLETED": "Renewal contract has been activated successfully.",
    "RENEWAL_ERROR": "An error occurred during renewal initiation or processing. Check dashboard for details.",
}
for sid, meaning in renewal_statuses.items():
    write_chunk("statuses", f"renewal-status-{sid.lower().replace('_','-')}", f"Renewal Status: {sid.replace('_',' ').title()}",
                ["renewal", "status"], f"**Business Meaning:** {meaning}")

# Approval statuses
for sid, meaning in [("PENDING", "Discount or billing frequency change awaits approval from order management."),
                     ("APPROVED", "The requested discount or billing frequency change was approved."),
                     ("REJECTED", "The requested discount or billing frequency change was declined.")]:
    write_chunk("statuses", f"approval-status-{sid.lower()}", f"Approval Status: {sid.title()}",
                ["approval", "discount"], f"**Business Meaning:** {meaning}")

# Opt-in statuses
optin = {
    "NONE": "No opt-in relationship exists between dealer and customer.",
    "REQUESTED": "Dealer has requested permission to manage the customer account.",
    "PENDING": "Opt-in request is awaiting customer response.",
    "APPROVED": "Customer approved dealer management access.",
    "COMMITTED": "Opt-in is fully active and committed.",
    "GRANTED": "Customer granted management permission.",
    "DECLINED": "Customer declined the opt-in request.",
    "REJECTED": "Opt-in request was rejected.",
    "EXPIRED": "Opt-in request expired without response (7-day window).",
    "REVOKED": "Customer revoked previously granted opt-in.",
    "CANCELLED": "Opt-in request was cancelled.",
}
for sid, meaning in optin.items():
    write_chunk("statuses", f"optin-status-{sid.lower()}", f"Opt-In Status: {sid.title()}",
                ["opt-in", "customer"], f"**Business Meaning:** {meaning}")

# Device transfer statuses
for sid, meaning in [
    ("PENDING", "Device transfer has been initiated and is awaiting processing."),
    ("SCHEDULED", "Transfer is scheduled for a future date or contract activation."),
    ("APPROVED", "Transfer completed successfully."),
    ("FAILED", "Transfer failed. Check dashboard attention event."),
    ("CANCELED", "Transfer was cancelled by dealer or system."),
    ("REQUESTED", "Customer requested to claim a device from dealer inventory."),
    ("DECLINED", "Dealer declined the customer device transfer request."),
]:
    write_chunk("statuses", f"device-transfer-{sid.lower()}", f"Device Transfer: {sid.title()}",
                ["device", "transfer"], f"**Business Meaning:** {meaning}")

# EMS, Bulk, User statuses
for sid, meaning in [
    ("ACTIVE", "License is active and in use on device or user."),
    ("NOT_ACTIVATED", "License exists but has not been activated yet."),
    ("EXPIRED", "License has expired."),
    ("DISABLED", "License has been disabled."),
    ("PROCESSING", "Bulk ship-to operation is in progress."),
    ("COMPLETED", "Bulk ship-to operation finished successfully."),
    ("COMMITTED", "User has accepted invitation and is active on account."),
    ("PENDING", "User invitation is pending acceptance."),
]:
    cat = "bulk" if sid in ("PROCESSING", "COMPLETED") else "ems" if sid in ("ACTIVE", "NOT_ACTIVATED", "EXPIRED", "DISABLED") else "user"
    write_chunk("statuses", f"{cat}-status-{sid.lower()}", f"{cat.upper()} Status: {sid.title()}",
                [cat, "status"], f"**Business Meaning:** {meaning}")

# Contract status reasons (subset - key ones)
reasons = {
    "PRICE_CHANGE": "Pricing changed and requires review or approval.",
    "PRICE_CHANGE_APPROVAL_REQUIRED": "A price change hold is active; approval needed before proceeding.",
    "D_COUNTRY_HOLD": "Regulatory hold for D-Country compliance. Dealer and/or customer must submit forms.",
    "MANUALLY_CANCELLED": "Contract or amendment was manually cancelled by the dealer.",
    "DISCOUNT_APPROVED": "Requested discount was approved by order management.",
    "DISCOUNT_DECLINED": "Requested discount was declined.",
    "INVITATION_NOT_ACCEPTED_BY_ACCOUNT_OWNER": "Contract on hold because account owner has not accepted invitation.",
    "QUOTE_AUTO_CANCELLED_REPRICE_WINDOW_EXPIRED": "Amendment auto-cancelled because reprice window (24 hours before start) expired.",
}
for rid, meaning in reasons.items():
    write_chunk("statuses", f"contract-reason-{rid.lower().replace('_','-')}", f"Contract Status Reason: {rid.replace('_',' ').title()}",
                ["contract", "reason"], f"**Business Meaning:** {meaning}")

# --- WORKFLOW CHUNKS ---
workflows = {
    "new-contract-sale": ("New Contract Sale", ["contract", "workflow"],
        """**Purpose:** Sell a new subscription to a customer.

**Trigger:** Dealer selects Create Contract.

**Prerequisites:** Customer exists with verified organization and ship-to address. Dealer has Create and Manage Contract permission.

**Steps:**
1. Dealer creates draft contract with products, term, and billing frequency.
2. System prices the contract via Salesforce.
3. Dealer optionally reprices, applies promo/discount, saves PO number.
4. If discount or billing frequency change requires approval, contract may go On Hold until approved.
5. Dealer submits (converts) the contract.
6. Status progresses: Submitted → Pending Activation → Activation In Progress → Activated.
7. Dealer assigns subscriptions to devices or users.

**Decision Points:** Approval required? D-Country hold? Trial eligibility?

**Outcomes:** Activated contract with assignable subscriptions, or On Hold/Error/Cancelled.

**Failure Scenarios:** Missing organization, expired quote (30 days), pending approval blocks submission."""),
    "dealer-amendment": ("Dealer-Initiated Amendment", ["amendment", "workflow"],
        """**Purpose:** Change an activated contract mid-term (add seats, upgrade, downgrade).

**Trigger:** Dealer creates amendment on activated contract.

**Prerequisites:** Contract Activated, no pending amendment, no active customer requests, not in renewal, not trial, not within 8 days of renewal date.

**Steps:**
1. Create amendment draft with desired changes.
2. Reprice if needed; save PO number.
3. Place amendment order.
4. If price change hold: approve and resubmit pricing.
5. Status: Amendment Submitted → Amendment Activated.

**Failure Scenarios:** Contract not amendable, future start date conflicts, product compatibility errors."""),
    "customer-amendment": ("Customer-Initiated Amendment", ["amendment", "axp", "workflow"],
        """**Purpose:** Process amendment requests from customer via AXP portal.

**Trigger:** Customer submits request in AXP; arrives via Service Bus.

**Steps:**
1. DXP receives positive or negative request.
2. Dealer notified via in-app notification and dashboard.
3. Positive: dealer accepts (flows to order management) or declines.
4. Negative: dealer can delete request.
5. Requests expire after 7 days if not actioned.

**Failure Scenarios:** Request expired, dealer declined, order management error."""),
    "contract-renewal": ("Contract Renewal", ["renewal", "workflow"],
        """**Purpose:** Renew an expiring or expired contract.

**Trigger:** Dealer starts renewal manually, or auto-renewal initiated by Salesforce.

**Prerequisites:** Contract Activated or Expired, renewal date in valid window (Early/Regular/Late), no pending amendment.

**Renewal Windows (Annual):** Early: 90-61 days before; Regular: 60-0 days; Late: 1-30 days after.
**Renewal Windows (Monthly):** Early: 30-15 days; Regular: 14-0 days; Late: 1-30 days after.

**Steps:**
1. Start renewal → Renewal Initiated.
2. Salesforce creates renewal quote (event-driven).
3. Dealer edits renewal quote (term, end date, promo, renewal type).
4. Submit renewal contract.
5. Renewal Completed when activated.

**Failure Scenarios:** Renewal date out of range, renewal already in progress, trial contract."""),
    "approval-workflow": ("Discount and Billing Frequency Approval", ["approval", "workflow"],
        """**Purpose:** Handle holds when discount or billing frequency changes require order management approval.

**Trigger:** Reprice with discount outside auto-approve range, or billing frequency change.

**Steps:**
1. Approval Status set to Pending; contract/amendment On Hold.
2. Order management reviews in Salesforce.
3. Approved or Rejected event updates DXP.
4. Dealer can dismiss approval request or withdraw pending change.

**User Impact:** Contract stuck On Hold until approval resolves."""),
    "dcountry-hold": ("D-Country Regulatory Hold", ["compliance", "workflow"],
        """**Purpose:** Handle regulatory compliance holds for certain countries.

**Trigger:** Contract placed On Hold with D-Country reason from Salesforce.

**Steps:**
1. Dealer and/or customer notified.
2. Dealer submits D-Country hold form (Annual or Individual type).
3. Forms reviewed; contract proceeds or is cancelled.

**Failure Scenarios:** Form rejected, manual cancellation by dealer."""),
    "customer-onboarding": ("Customer Onboarding", ["customer", "workflow"],
        """**Purpose:** Add a new or existing customer to dealer portfolio.

**Steps:**
1. Create new customer OR link existing IAM customer.
2. Set up organization (create/assign/verify).
3. Configure ship-to address and contact defaults.
4. Invite users (owner, secondary owners, product users).
5. Optionally request opt-in for full management access.

**Prerequisites:** Create and Manage Customer permission."""),
    "device-transfer": ("Device Inventory and Transfer", ["device", "workflow"],
        """**Purpose:** Move devices from dealer inventory to customer ownership.

**Dealer-initiated:** Transfer multiple devices immediately or scheduled (on contract activation).

**Customer-initiated:** Customer requests device claim in AXP; dealer approves or declines.

**Schedule options:** Now, Deferred, On Contract Activated, On Contract Activated Deferred.

**Failure Scenarios:** Active subscriptions on device, duplicate transfer request, device not owned by dealer."""),
    "subscription-assignment": ("Subscription Assignment", ["subscription", "workflow"],
        """**Purpose:** Assign contract line licenses to devices or users.

**Device assignment:** For device-based products on IoT/Non-IoT hardware.

**User assignment:** For seat-based products; requires approved opt-in; Secondary Owner or Product User only.

**Prerequisites:** Contract in Activated, Pending Activation, or Activation In Progress. Entitlement capacity available.

**Failure Scenarios:** Account-based subscription cannot assign to device; owner/admin cannot receive user assignment; capacity exhausted."""),
    "superkey-management": ("SuperKey Management", ["device", "superkey", "workflow"],
        """**Purpose:** Create temporary multi-SKU entitlements on dealer devices for demos.

**Steps:** Create superkey → Add SKUs → Revoke when done.

**Limit:** Maximum 5 superkey uses per device."""),
    "bulk-shipto": ("Bulk Ship-To Updates", ["customer", "workflow"],
        """**Purpose:** Update ship-to contact or address across all customer contracts when defaults change.

**Trigger:** Customer default ship-to changes, or organization verification with address update.

**Steps:**
1. Bulk operation initiated.
2. Updates sent to Salesforce via Service Bus.
3. Status events report Processing → Completed or Failed.
4. Retry available for failed individual contract address updates."""),
    "contract-activation-expiry": ("Contract Activation and Expiry", ["contract", "workflow"],
        """**Purpose:** Manage contract lifecycle completion and draft expiry.

**Activation:** Customer owner accepts invitation → Pending Activation → Activated.

**Draft Expiry:** Unsubmitted drafts expire after 30 days (background job every 10 minutes).

**Amendment Expiry:** On-hold amendments auto-cancelled if reprice window (24h before start) passes.

**Customer Request Expiry:** Positive requests expire after 7 days."""),
}
for wid, (title, tags, content) in workflows.items():
    write_chunk("workflows", wid, title, tags, content)

# --- ROLE/PERMISSION CHUNKS ---
roles = {
    "dealer-permission-model": ("Dealer Permission Model", ["permission", "iam"],
        "DXP uses IAM permissions in Category:Action format. Categories: Contract, Customer, Dealer, Device, Subscription, Notification, EmailSettings, Invoice, Audit, Organization. Actions: View, CreateAndManage, OptInAndManage, SecondaryOwnerManage, ManageSettings. Users need both the correct permission AND resource ownership (contract/device belongs to their dealer account)."),
    "permission-contract-view": ("View Contract Permission", ["permission", "contract"],
        "Allows viewing contracts, quotes, amendments, renewals, dashboard events, and audit logs related to contracts. Required for all contract read operations."),
    "permission-contract-manage": ("Create and Manage Contract Permission", ["permission", "contract"],
        "Allows creating drafts, submitting contracts, amendments, renewals, repricing, cancellations, D-Country forms, and positive request actions."),
    "permission-customer-view": ("View Customer Permission", ["permission", "customer"],
        "Allows viewing dealer customers, addresses, settings, and bulk operation status."),
    "permission-customer-manage": ("Create and Manage Customer Permission", ["permission", "customer"],
        "Allows creating customers, linking customers, saving defaults, bulk ship-to operations, and user management."),
    "permission-customer-optin": ("Opt-In and Manage Customer Permission", ["permission", "opt-in"],
        "Allows requesting and managing dealer opt-in to customer accounts."),
    "permission-customer-secondary": ("Secondary Owner Manage Permission", ["permission", "customer"],
        "Allows inviting, updating, and removing secondary owners on customer accounts."),
    "permission-device-view": ("View Device Permission", ["permission", "device"],
        "Allows viewing dealer device inventory and export status."),
    "permission-device-manage": ("Create and Manage Device Permission", ["permission", "device"],
        "Allows device transfers, superkeys, subscription assignment to devices, and transfer request approval."),
    "permission-subscription-manage": ("Create and Manage Subscription Permission", ["permission", "subscription"],
        "Allows assigning subscriptions to users and revoking licenses."),
    "permission-organization": ("Organization Permission", ["permission", "organization"],
        "Allows creating, assigning, verifying organizations and searching organization directory."),
    "role-owner": ("Customer Role: Owner", ["role", "customer"],
        "Account owner. Cannot receive subscription assignments. Visible in user lists. Must accept invitation for contract activation."),
    "role-secondary-owner": ("Customer Role: Secondary Owner", ["role", "customer"],
        "Admin-level customer role. Can receive seat-based subscription assignments."),
    "role-product-user": ("Customer Role: Product User", ["role", "customer"],
        "End user role. Can receive subscriptions. Only visible to dealer when opt-in is Approved, Committed, or Granted."),
    "role-dealer-owner": ("Dealer Role: Dealer Owner", ["role", "dealer"],
        "Highest priority dealer identity. Permissions determined by IAM, not dealer role directly."),
    "resource-ownership": ("Resource Ownership Guards", ["permission", "security"],
        "Even with broad permissions, users can only access resources belonging to their dealer account. Attempting to access another dealer's contract, device, or customer returns Access Denied."),
}
for rid, (title, tags, content) in roles.items():
    write_chunk("roles", rid, title, tags, content)

# --- BUSINESS RULE CHUNKS ---
rules = {
    "amendment-start-date-window": ("Amendment Start Date Window", ["amendment", "rule"],
        "Amendment start date must be 2-30 days in the future. Cannot start in the last 8 days of the contract term. Impact: Dealer cannot set immediate or far-future amendment dates outside this window."),
    "renewal-amendment-blackout": ("Renewal Amendment Blackout", ["renewal", "amendment", "rule"],
        "Contracts cannot be amended within 8 days of the renewal date. Auto-renew changes also blocked in this window. Impact: Dealer must wait until after renewal processes or complete renewal first."),
    "quote-validity-30-days": ("Quote Validity 30 Days", ["contract", "rule"],
        "Draft quotes and amendment quotes are valid for 30 days. Unsubmitted drafts expire automatically. Impact: Dealer must reprice and resubmit if draft expires."),
    "customer-request-expiry-7-days": ("Customer Request 7-Day Expiry", ["customer-request", "rule"],
        "Customer-initiated amendment requests expire after 7 days without dealer action. Impact: Dealer must respond within a week or request auto-expires."),
    "organization-required": ("Organization Verification Required", ["customer", "rule"],
        "Customer must have a verified organization before creating contracts, amendments, or renewals. Impact: Transactional operations blocked until organization verified."),
    "shipto-address-required": ("Ship-To Address Required", ["customer", "rule"],
        "Valid ship-to address required before contracts, amendments, renewals. Impact: Operations blocked until address configured."),
    "optin-for-product-users": ("Opt-In Required for Product Users", ["opt-in", "rule"],
        "Dealer opt-in must be Approved or Committed to view product users and assign seat-based subscriptions. Impact: User list hidden and assignment blocked without opt-in."),
    "trial-no-amend-renew": ("Trial Contract Restrictions", ["trial", "rule"],
        "Trial contracts cannot be amended or renewed. Impact: Dealer must convert to paid contract through new sale workflow."),
    "max-sku-quantity-999": ("Maximum SKU Quantity 999", ["contract", "rule"],
        "Maximum quantity per SKU line is 999. Impact: Cannot order more than 999 seats/units per product line."),
    "superkey-limit-5": ("SuperKey 5 Uses Per Device", ["superkey", "rule"],
        "Maximum 5 superkey uses per device. Impact: Cannot create more superkeys once limit reached."),
    "discount-range": ("Discount Range 0.5% to 99.4%", ["pricing", "rule"],
        "Discretionary discounts must be between 0.5% and 99.4%. Outside range may trigger approval. Impact: Extreme discounts require order management approval."),
    "no-concurrent-approval": ("No Concurrent Approval Requests", ["approval", "rule"],
        "Cannot apply new discount or promo while approval is pending. Impact: Dealer must wait or withdraw existing approval request."),
    "subscription-revocation-rules": ("Subscription Revocation Rules", ["subscription", "rule"],
        "External subscriptions cannot be revoked. Non-transferable Non-IoT devices: revocable only pre-activation. Non-transferable IoT on customer-owned device: blocked. Impact: Some revocations unavailable depending on device type and ownership."),
    "owner-admin-no-assignment": ("Owner and Admin Cannot Receive Subscriptions", ["subscription", "rule"],
        "Account Owners and Admins cannot be assigned seat-based subscriptions. Impact: Dealer must assign to Secondary Owner or Product User."),
    "account-based-no-device": ("Account-Based Subscriptions Not Device-Assignable", ["subscription", "rule"],
        "Account-based subscription products cannot be assigned to individual devices. Impact: Use user assignment or account-level activation instead."),
    "amendment-reprice-24h": ("Amendment Reprice 24-Hour Window", ["amendment", "rule"],
        "Amendment must be repriced within 24 hours before start date or it auto-cancels. Impact: On-hold amendments cancelled if reprice window missed."),
    "renewal-date-ranges": ("Renewal Date Range Windows", ["renewal", "rule"],
        "Annual Early: 90-61 days before renewal. Regular: 60-0 days. Late: 1-30 days after. Monthly Early: 30-15. Regular: 14-0. Late: 1-30. Impact: Renewal only available in appropriate window."),
    "coterm-minimum-days": ("Co-Term Minimum Days", ["renewal", "rule"],
        "Co-term alignment requires minimum 30 days (annual) or 14 days (monthly) before end date. Impact: Cannot co-term too close to contract end."),
    "email-domain-match": ("Email Domain Must Match Dealer", ["customer", "rule"],
        "Customer user email domain must match dealer business domain for invitations. Impact: Cross-domain invites blocked."),
    "contract-assignable-statuses": ("Contract Statuses for Assignment", ["subscription", "rule"],
        "Subscriptions assignable only when contract is Activated, Pending Activation, or Activation In Progress. Impact: Cannot assign on Draft, On Hold, or Cancelled contracts."),
}
for rid, (title, tags, content) in rules.items():
    write_chunk("business-rules", rid, title, tags, content)

# --- INTEGRATION CHUNKS ---
integrations = {
    "salesforce-overview": ("Salesforce Integration Overview", ["salesforce", "integration"],
        "DXP integrates with Salesforce through Middleware hub-and-spoke architecture. DXP sends quote/contract requests via REST Apex endpoints. Salesforce sends status, approval, and renewal events back via Azure Service Bus. Most contract status updates are event-driven, not real-time API polling. NEEDS VALIDATION: exact sync SLA timing."),
    "sf-quote-create": ("Salesforce Quote Creation", ["salesforce", "quote"],
        "Direction: DXP to Salesforce. Triggered when dealer creates draft contract, amendment, or edits renewal quote. Data: products, quantities, term, billing frequency, customer account, contacts, addresses, promo/discount. User sees priced contract in DXP after Salesforce responds."),
    "sf-contract-status": ("Salesforce Contract Status Events", ["salesforce", "contract"],
        "Direction: Salesforce to DXP via Middleware. Event: contract.status.changed. Updates DXP contract status (Submitted, On Hold, Pending Activation, etc.). User sees status change in contract list and receives notification. Failure: status stuck until event reprocessed."),
    "sf-product-sync": ("Salesforce Product Catalog Sync", ["salesforce", "product"],
        "Direction: Salesforce to DXP. Trigger: product events on dxp.product.events topic. Consumer: ProductSyncService Azure Function. Syncs products, pricing, bundles, add-ons to DXP database. User sees current product catalog and pricing. Failure: outdated products until sync completes."),
    "sf-approval-events": ("Salesforce Approval Events", ["salesforce", "approval"],
        "Direction: Salesforce to DXP. Event: contract.approval.status.changed. Updates discount/billing frequency approval status. Releases On Hold contracts when approved."),
    "sb-contract-events-out": ("Service Bus: DXP Contract Events Outbound", ["service-bus", "contract"],
        "Topic: dxp.contract.events. Producer: DXP. Messages: contract created, amended, status changed, renewal started, negative requests, bulk updates, D-Country forms. Consumer: Middleware/Salesforce. Business impact: initiates order processing."),
    "sb-status-events-in": ("Service Bus: Middleware Status Events Inbound", ["service-bus", "contract"],
        "Topic: middleware.dxp.status.events. Subscription: dxp.status.gql.events. Consumer: DXP ServiceBusEventProcessor. Messages: SF contract status, activation, approval, renewal, bulk operation status. Business impact: updates what dealer sees in DXP."),
    "sb-axp-amendments": ("Service Bus: AXP Customer Amendments", ["service-bus", "axp"],
        "Topic: axp.subscriptions.amendments.topic. Direction: AXP to DXP. Messages: customer amendment create, update, delete. Business impact: dealer receives customer request notifications."),
    "sb-axp-device": ("Service Bus: AXP Device Transfer", ["service-bus", "axp", "device"],
        "Topic: axp.device.topic. Messages: device claim request, claim cancel. Business impact: dealer sees transfer requests on dashboard."),
    "sb-device-events-out": ("Service Bus: DXP Device Events", ["service-bus", "device"],
        "Topic: dxp.device.topic. Messages: device claim approved, rejected, failed. Consumer: AXP/Accounts. Business impact: customer notified of transfer outcome."),
    "sb-internal-notification": ("Service Bus: Internal Email Notifications", ["service-bus", "email"],
        "Topic: dxp.internal.notification.events. Triggers Email Notification Azure Function for on-hold contract/amendment emails. NEEDS VALIDATION: exact email delivery timing."),
    "sb-license-sf-trigger": ("License Events to Salesforce", ["service-bus", "salesforce", "ems"],
        "Messages: license assign/revoke trigger update salesforce. Direction: DXP to Middleware to Salesforce. Triggered when dealer assigns or revokes subscriptions. NEEDS VALIDATION: SF update timing."),
    "events-service-iam": ("Trimble Events Service (IAM)", ["events", "iam"],
        "No direct Kafka SDK. DXP consumes IAM events via Trimble Cloud Events Service. Namespace: com.trimble.tcp.iam. Events: update_user_account, delete_user_account, update_account_account. Poll interval: 100ms-2s adaptive. Impact: invitation status updates, permission cache refresh, opt-in status changes."),
    "ems-integration": ("EMS Entitlement Management", ["ems", "integration"],
        "EMS is system of record for licenses. DXP assigns/revokes entitlements via EMS API. Capacity checks enforced by EMS. User sees license status (Active, Not Activated, Expired, Disabled) on devices and users."),
    "iam-integration": ("Trimble IAM Integration", ["iam", "integration"],
        "IAM manages accounts, users, organizations, and dealer permissions. DXP reads permissions per request and caches them. User invitation, role assignment, and organization verification flow through IAM."),
    "axp-integration": ("AXP Customer Portal", ["axp", "integration"],
        "AXP is the customer-facing portal. Customers submit amendment requests and device transfer requests that arrive in DXP via Service Bus. DXP sends acknowledgements back. NEEDS VALIDATION: full AXP UI behavior."),
    "middleware-mdm": ("Middleware MDM", ["middleware", "integration"],
        "Master data management for customers and dealers. Used for customer creation, linking, and invitations."),
    "middleware-tes": ("Middleware Transactional Email", ["middleware", "email"],
        "Sends transactional emails for invitations, opt-in, device transfers, and renewals."),
    "scheduled-expiry-job": ("Scheduled Expiry Job", ["scheduled", "integration"],
        "HandleExpiryHostedService runs every 10 minutes. Expires draft contracts/quotes, auto-cancels on-hold amendments past reprice window, expires customer requests, cleans dashboard events."),
    "scheduled-amendment-activation": ("Scheduled Amendment Activation", ["scheduled", "integration"],
        "AmendmentActivationHostedService runs every 5 minutes. Activates amendments whose Salesforce activation completed and start date has passed."),
    "scheduled-renewal-notifications": ("Scheduled Renewal Notifications", ["scheduled", "notification"],
        "RenewalNotificationJob runs every 10 minutes. Creates in-app renewal reminders at configured thresholds (60/14/7/-15/-30 day windows)."),
}
for iid, (title, tags, content) in integrations.items():
    nv = "NEEDS VALIDATION" in content
    write_chunk("integrations", iid, title, tags, content, needs_validation=nv)

# --- ERROR CHUNKS ---
errors = {
    "auth-not-authenticated": ("Not Authenticated", ["error", "auth"],
        "**Meaning:** User is not logged in or session/token is invalid/expired. **Cause:** Missing or expired JWT. **User explanation:** Please sign in again. **Resolution:** Log out and log back in."),
    "auth-not-authorized": ("Not Authorized", ["error", "auth"],
        "**Meaning:** User is logged in but lacks permission or resource access. **Cause:** Missing IAM permission or resource belongs to different dealer. **User explanation:** You do not have permission to perform this action. **Resolution:** Contact dealer administrator to grant appropriate permission."),
    "resource-not-dealer": ("Resource Does Not Belong to Dealer", ["error", "auth"],
        "**Meaning:** Contract, device, customer, or invoice belongs to a different dealer account. **Resolution:** Verify you are operating under the correct dealer account header."),
    "contract-not-activated": ("Contract Not Activated", ["error", "validation"],
        "**Meaning:** Operation requires activated contract. **Cause:** Contract still in draft, submitted, or on hold. **Resolution:** Wait for activation or complete submission."),
    "contract-in-renewal": ("Contract In Renewal State", ["error", "validation"],
        "**Meaning:** Cannot amend while renewal is in progress. **Resolution:** Complete or cancel renewal first."),
    "contract-has-pending-amendment": ("Pending Amendment Exists", ["error", "validation"],
        "**Meaning:** Only one amendment at a time. **Resolution:** Complete or cancel existing amendment."),
    "contract-has-active-requests": ("Active Customer Requests", ["error", "validation"],
        "**Meaning:** Customer-initiated requests pending. **Resolution:** Accept, decline, or wait for expiry before new amendment."),
    "organization-missing": ("Organization Missing", ["error", "validation"],
        "**Meaning:** Customer has no organization assigned. **Resolution:** Create or assign organization and verify."),
    "organization-unverified": ("Organization Unverified", ["error", "validation"],
        "**Meaning:** Organization exists but not verified in IAM. **Resolution:** Complete organization verification."),
    "shipto-missing": ("Ship-To Address Missing", ["error", "validation"],
        "**Meaning:** Customer lacks valid ship-to address. **Resolution:** Add and validate ship-to address."),
    "entitlement-capacity-exhausted": ("No Available Licenses", ["error", "subscription"],
        "**Meaning:** All seats on contract line are assigned. **Resolution:** Create amendment to add seats or revoke existing assignment."),
    "user-role-not-assignable": ("User Cannot Receive Subscription", ["error", "subscription"],
        "**Meaning:** User is Owner, Admin, or has no role. **Resolution:** Assign to Secondary Owner or Product User."),
    "user-already-has-subscription": ("User Already Has Subscription", ["error", "subscription"],
        "**Meaning:** Duplicate assignment attempt. **Resolution:** Select different user or different product."),
    "dealer-opt-in-required": ("Dealer Opt-In Required", ["error", "opt-in"],
        "**Meaning:** Opt-in not approved for customer management. **Resolution:** Request opt-in and wait for customer approval."),
    "device-not-owned": ("Device Not Owned by Dealer", ["error", "device"],
        "**Meaning:** Device not in dealer inventory. **Resolution:** Verify serial number and dealer account."),
    "device-active-subscriptions": ("Device Has Active Subscriptions", ["error", "device"],
        "**Meaning:** Cannot transfer device with active licenses. **Resolution:** Revoke subscriptions first or use revoke-and-transfer."),
    "superkey-limit-reached": ("SuperKey Limit Reached", ["error", "superkey"],
        "**Meaning:** 5 superkey uses exceeded on device. **Resolution:** Revoke existing superkey before creating new."),
    "subscription-revocation-blocked": ("Subscription Revocation Blocked", ["error", "subscription"],
        "**Meaning:** Business rules prevent revocation (external sub, non-transferable device). **Resolution:** Review device type and ownership rules."),
    "account-based-device-blocked": ("Account-Based Subscription Device Block", ["error", "subscription"],
        "**Meaning:** Account-based products cannot assign to devices. **Resolution:** Use user assignment instead."),
    "customer-already-linked": ("Customer Already Linked", ["error", "customer"],
        "**Meaning:** Customer already associated with this dealer. **Resolution:** Search existing customers instead of creating duplicate link."),
    "renewal-date-out-of-range": ("Renewal Date Out of Range", ["error", "renewal"],
        "**Meaning:** Current date outside Early/Regular/Late renewal window. **Resolution:** Wait until renewal window opens or contact support for late renewal."),
    "renewal-already-initiated": ("Renewal Already Initiated", ["error", "renewal"],
        "**Meaning:** Renewal workflow already in progress. **Resolution:** Complete existing renewal before starting another."),
    "amendment-start-date-invalid": ("Invalid Amendment Start Date", ["error", "amendment"],
        "**Meaning:** Start date outside 2-30 day window or in last 8 days of term. **Resolution:** Adjust start date within allowed range."),
    "product-pricing-not-found": ("Product Pricing Not Found", ["error", "pricing"],
        "**Meaning:** Product not priced for customer's country/currency. **Resolution:** Verify product availability or contact support."),
    "email-domain-not-allowed": ("Email Domain Not Allowed", ["error", "customer"],
        "**Meaning:** Email domain doesn't match dealer business domain. **Resolution:** Use email address on dealer's business domain."),
    "middleware-generic-error": ("Order Processing Error", ["error", "integration"],
        "**Meaning:** Middleware or Salesforce returned an error. **Cause:** Downstream system issue. **Resolution:** Retry operation; if persists, contact support with contract number."),
}
for eid, (title, tags, content) in errors.items():
    write_chunk("errors", eid, title, tags, content)

# --- DATA OWNERSHIP CHUNKS ---
ownership = {
    "contract-status": ("Contract Status", ["contract", "ownership"],
        "**System of Record:** Salesforce (via Middleware). **Update Source:** Service Bus status events. **Sync:** Event-driven (seconds to minutes). **User Editable:** No. **Reason:** Managed by order management. **Impact:** Dealer sees status update after event processed."),
    "contract-draft": ("Contract Draft and Pricing", ["contract", "ownership"],
        "**System of Record:** DXP + Salesforce (pricing). **User Editable:** Yes while Draft. **Reason:** Dealer creates and prices locally; Salesforce provides pricing engine."),
    "product-catalog": ("Product Catalog", ["product", "ownership"],
        "**System of Record:** Salesforce. **Sync:** ProductSyncService on product events. **User Editable:** No. **Reason:** Catalog managed in Salesforce."),
    "licenses": ("Licenses and Entitlements", ["subscription", "ownership"],
        "**System of Record:** EMS. **Update Source:** DXP assign/revoke operations. **User Editable:** Assign and revoke only. **Reason:** EMS enforces capacity and activation."),
    "customer-users": ("Customer Users and Roles", ["customer", "ownership"],
        "**System of Record:** Trimble IAM. **Update Source:** DXP invitations and role updates. **User Editable:** Invite, update roles, cancel invitations via DXP."),
    "dealer-permissions": ("Dealer Permissions", ["permission", "ownership"],
        "**System of Record:** Trimble IAM. **Sync:** Per-request fetch with cache. **User Editable:** No in DXP. **Reason:** Administered in IAM by account administrators."),
    "invoices": ("Invoices", ["invoice", "ownership"],
        "**System of Record:** External billing (NEEDS VALIDATION). **User Editable:** No — view and download only."),
    "devices": ("Device Inventory", ["device", "ownership"],
        "**System of Record:** PCS/IAM. **User Editable:** Transfer, dealer reference label, subscription assignment. **Reason:** Hardware registry external to DXP."),
    "organizations": ("Organizations", ["organization", "ownership"],
        "**System of Record:** Trimble IAM. **User Editable:** Create, assign, verify via DXP."),
    "notifications": ("Notifications", ["notification", "ownership"],
        "**System of Record:** DXP. **User Editable:** Mark read, configure preferences."),
    "customer-requests": ("Customer Requests", ["customer-request", "ownership"],
        "**System of Record:** DXP (received from AXP). **Update Source:** AXP via Service Bus. **User Editable:** Accept, decline, delete by dealer."),
    "addresses": ("Addresses", ["address", "ownership"],
        "**System of Record:** CDH/IAM. **User Editable:** Create and update via DXP with validation."),
    "renewal-quotes": ("Renewal Quotes", ["renewal", "ownership"],
        "**System of Record:** Salesforce creates; DXP stores copy. **User Editable:** Edit term, promo, end date while renewal in progress."),
    "approvals": ("Approval Status", ["approval", "ownership"],
        "**System of Record:** Salesforce. **Update Source:** Approval status events. **User Editable:** Request via reprice; dismiss or withdraw in DXP."),
    "audit-logs": ("Audit Logs", ["audit", "ownership"],
        "**System of Record:** DXP. **User Editable:** No — read only. **Reason:** Immutable activity history."),
    "dashboard-events": ("Dashboard Attention Events", ["dashboard", "ownership"],
        "**System of Record:** DXP. **User Editable:** Ignore/dismiss. **Source:** Generated from contract, device, and request state changes."),
    "bulk-operations": ("Bulk Operations", ["bulk", "ownership"],
        "**System of Record:** DXP initiates; Salesforce processes. **Status updates:** Via Service Bus events."),
    "auto-renew-setting": ("Auto-Renew Setting", ["renewal", "ownership"],
        "**System of Record:** Salesforce/Middleware. **User Editable:** Toggle via DXP when business rules allow. **Blocked:** Within 8 days of renewal, during renewal, on cancelled/expired contracts."),
}
for oid, (title, tags, content) in ownership.items():
    nv = "NEEDS VALIDATION" in content
    write_chunk("data-ownership", oid, title, tags, content, needs_validation=nv)

# --- FAQ CHUNKS (generate from FAQ list - loaded from companion data) ---
faqs = []  # populated below

FAQ_DATA = [
    ("What does Draft mean?", "Draft means your contract has been priced but not yet submitted to order management. You can still edit pricing, apply discounts, add a PO number, or delete the draft. Submit the contract when ready to place the order."),
    ("What does Submitted mean?", "Submitted means you have placed the order. It is being processed by order management and Salesforce. You cannot edit pricing at this stage. Status will update automatically when processing completes."),
    ("What does On Hold mean?", "On Hold means order management has paused processing. Common reasons include price change approval required, D-Country regulatory compliance, or billing frequency change pending review. Check the status reason for specific details."),
    ("What does Pending Activation mean?", "Pending Activation means the contract is waiting for the customer account owner to accept their invitation and activate the subscription. You can resend the invitation if needed."),
    ("What does Activated mean?", "Activated means the contract is live. You can assign subscriptions to devices or users, create amendments, and start renewals."),
    ("What does Error status mean?", "Error means a processing problem occurred. Check your dashboard attention events for details and contact support if the issue persists."),
    ("What does Expired mean for a contract?", "Expired means the draft was not submitted within 30 days and automatically expired. Create a new contract or start a renewal if the previously activated contract has expired."),
    ("What does Cancelled mean?", "Cancelled means the contract or amendment was cancelled before completion. Check the status reason for whether it was manual, regulatory, or automatic cancellation."),
    ("What does Amendment Draft mean?", "Amendment Draft is an internal status meaning you have priced a mid-term change but not yet submitted it. You can reprice, edit, or delete before placing the amendment order."),
    ("What does Amendment On Hold mean?", "Amendment On Hold means the amendment is blocked, often for price change approval. You may need to approve and resubmit pricing or wait for order management review."),
    ("Why is my contract stuck in Submitted?", "Contracts in Submitted status are being processed by order management. This typically takes from a few seconds to several minutes. If it remains stuck for an extended period, there may be an integration delay—check for On Hold or Error status, or contact support."),
    ("Why is my contract On Hold?", "Your contract is On Hold because order management requires additional action. Check the status reason: it may be price change approval, D-Country compliance, discount review, or the account owner has not accepted their invitation."),
    ("How do I create a contract?", "Go to your customer, ensure organization is verified and ship-to address is set, then Create Contract. Add products, set term and billing frequency, review pricing, and Submit."),
    ("How do I submit a contract?", "Open the draft contract, verify pricing and details, then Submit (Convert Contract). The status changes from Draft to Submitted."),
    ("How do I create an amendment?", "Open an Activated contract and select Create Amendment. Add your changes, reprice if needed, and Place Amendment Order."),
    ("Why can't I create an amendment?", "Common reasons: contract not activated, trial contract, renewal in progress, pending amendment exists, active customer requests, within 8 days of renewal, or missing verified organization."),
    ("How do I start a renewal?", "Open an Activated or Expired contract within the renewal window and select Start Renewal. Edit the renewal quote as needed and submit."),
    ("What is Early vs Regular vs Late renewal?", "Early renewal opens before the standard window (90-61 days for annual). Regular is the standard window (60-0 days). Late renewal is after expiration (1-30 days grace)."),
    ("Why can't I start a renewal?", "Renewal may be unavailable if: date is outside the renewal window, renewal already in progress, pending amendment exists, contract is trial, or organization is not verified."),
    ("How long does Salesforce synchronization take?", "Most status updates are event-driven and typically appear within seconds to a few minutes. There is no guaranteed SLA. NEEDS VALIDATION."),
    ("Why don't I see my latest Salesforce changes?", "DXP receives Salesforce updates via event messages. If events are delayed or failed, DXP may show stale status. Try refreshing; if issue persists, contact support."),
    ("Why is my Salesforce data not updated?", "License assignments and some changes trigger async events to Salesforce through Middleware. Updates may not be immediate. NEEDS VALIDATION on exact timing."),
    ("What happens when a contract is submitted?", "DXP sends the order to Salesforce via Middleware. Status progresses through Submitted, possibly On Hold, then Pending Activation, and finally Activated when the customer accepts."),
    ("What happens if an integration fails?", "The contract may show Error status or remain in the previous status. Dashboard attention events highlight issues. Retry the operation or contact support. Messages are reprocessed by Service Bus when possible."),
    ("Who can approve a contract?", "Discount and billing frequency approvals are handled by order management in Salesforce, not by dealer users directly. Dealers can dismiss or withdraw their approval requests."),
    ("Why can't I edit this field?", "Fields may be read-only because: the contract is not in Draft status, data is owned by Salesforce/IAM/EMS, or you lack the required permission."),
    ("Why is contract status read only?", "Contract status is managed by Salesforce order management. DXP displays status received via integration events. Dealers change status by submitting, cancelling, or completing workflows—not by editing the field directly."),
    ("Why can't I edit pricing?", "Pricing can only be edited on Draft contracts or Amendment Drafts. Submitted or Activated contracts require an amendment to change products or quantities."),
    ("What can a Dealer Owner do?", "Dealer Owner is the highest dealer identity role. Actual capabilities depend on IAM permissions assigned to the user, not the role title alone."),
    ("What can a Dealer Technician do?", "Technician is a dealer role identity. Permissions (View/Create and Manage per category) are assigned separately in IAM."),
    ("What is Create and Manage Contract permission?", "Allows creating, submitting, amending, renewing, repricing, and cancelling contracts and quotes."),
    ("What is View Contract permission?", "Allows viewing contracts, quotes, amendments, renewals, and related dashboard events. Required for read-only contract access."),
    ("Why do I get Access Denied?", "Either you lack the required IAM permission for this action, or the resource (contract, device, customer) belongs to a different dealer account."),
    ("What is opt-in?", "Opt-in is customer permission allowing the dealer to fully manage their account, including viewing product users and assigning seat-based subscriptions."),
    ("How do I request opt-in?", "Open the customer record and Request Opt-In. The customer receives a notification and must approve. Request expires in 7 days."),
    ("Why can't I see product users?", "Product users are only visible when opt-in status is Approved, Committed, or Granted."),
    ("Why can't I assign subscriptions to a user?", "Common reasons: opt-in not approved, user is Owner or Admin, user invitation not accepted (not Committed), no available license capacity, or contract not in assignable status."),
    ("Why can't I assign subscriptions to a device?", "Common reasons: account-based subscription (not device-assignable), contract not activated, device not owned by dealer, or no available entitlements."),
    ("What is a SuperKey?", "A temporary multi-SKU license key on a dealer device for demos or evaluation. Limited to 5 uses per device."),
    ("How do I transfer a device to a customer?", "Select the device(s) in inventory and Transfer. Choose immediate or scheduled transfer. Resolve any active subscription conflicts first."),
    ("What is a customer device transfer request?", "When a customer requests to claim your device through their AXP portal, you receive a request to Approve or Decline in DXP."),
    ("Why did my device transfer fail?", "Transfers fail due to active subscriptions on the device, duplicate requests, device not in your inventory, or downstream system errors. Check dashboard attention events."),
    ("What does Pending device transfer mean?", "Transfer has been initiated and is awaiting processing completion."),
    ("What does Scheduled transfer mean?", "Transfer will execute on the specified date or when the linked contract activates."),
    ("How do I assign devices to a subscription?", "From the contract line (subscription), use Assign Devices to Subscription to link specific hardware to that SKU."),
    ("What is a positive customer request?", "A customer-initiated request from AXP to add products, seats, or upgrades. Review and accept or decline in DXP."),
    ("What is a negative customer request?", "A customer-initiated request to downgrade or cancel quantities. You can delete the request if not proceeding."),
    ("How long do customer requests last?", "Customer requests expire after 7 days without dealer action."),
    ("What is D-Country hold?", "A regulatory compliance hold for certain countries. You and/or the customer may need to submit compliance forms before the order proceeds."),
    ("How do I submit a D-Country form?", "Open the on-hold contract and Submit D-Country Hold Request with the required form type (Annual or Individual)."),
    ("What is a bulk ship-to update?", "When you change a customer's default ship-to contact or address, DXP can update all their contracts at once via a bulk operation."),
    ("Why is my bulk operation failed?", "Individual contracts may fail address/contact updates in Salesforce. Use Retry on the failed contract to reattempt."),
    ("Where does product pricing come from?", "Product catalog and pricing are synchronized from Salesforce via the Product Sync service. You cannot edit pricing in DXP directly—only apply discounts and promo codes on drafts."),
    ("Where does contract status come from?", "Contract status after submission is updated by Salesforce order management events sent through Middleware to DXP."),
    ("Where do invoices come from?", "Invoices are retrieved from the external billing system. DXP provides view and download only. NEEDS VALIDATION: billing system name."),
    ("Can I edit an invoice?", "No. Invoices are read-only in DXP."),
    ("What notifications will I receive?", "Notifications cover contract status changes, renewals, customer requests, approvals, device transfers, opt-in updates, and bulk operations. Configure preferences in notification settings."),
    ("How do I mark all notifications as read?", "Use Mark All as Read from the notifications panel."),
    ("What are dashboard attention events?", "Priority items needing your action: contract errors, on-hold orders, expiring contracts, pending assignments, and device transfer requests."),
    ("What is auto-renew?", "When enabled, the contract automatically renews at end of term through Salesforce. You can toggle auto-renew on eligible activated contracts."),
    ("Why can't I change auto-renew?", "Blocked when: contract is cancelled/expired/error, renewal in progress, renewal contract exists, or within 8 days of renewal date."),
    ("What is co-term renewal?", "Aligning renewal end dates across multiple contracts. Requires minimum 30 days (annual) or 14 days (monthly) before end date."),
    ("What is a trial contract?", "A trial subscription with limited term. Trial contracts cannot be amended or renewed—convert to paid via new sale."),
    ("What is seat-based vs account-based subscription?", "Seat-based: assign to individual users. Account-based: applies at account level; cannot assign to individual devices."),
    ("What does EMS Active license mean?", "The license is activated and in use on the assigned device or user."),
    ("What does EMS Not Activated mean?", "License exists but has not been activated on the target device or user yet."),
    ("Why is subscription revocation blocked?", "External subscriptions, non-transferable devices, or customer-owned IoT devices may block revocation. Rules depend on device type and ownership."),
    ("How do I revoke a license?", "Select the subscription on the device or user and Revoke License. If transfer is pending, options include revoke-and-transfer or revoke-and-cancel-transfer."),
    ("What is the amendment reprice window?", "Amendments must be repriced within 24 hours before the start date. On-hold amendments auto-cancel if this window is missed."),
    ("What is the maximum quantity per product?", "999 units per SKU line on a quote or contract."),
    ("What is the maximum discount?", "Discretionary discounts can range from 0.5% to 99.4%. Values requiring approval may place the contract On Hold."),
    ("Why was my amendment auto-cancelled?", "Likely the reprice window (24 hours before start date) expired while the amendment was on hold."),
    ("Why was my draft contract deleted?", "Drafts not submitted within 30 days automatically expire."),
    ("How often is product catalog synchronized?", "Product catalog syncs event-driven when Salesforce publishes product changes. Not on a fixed schedule."),
    ("How often are expired drafts cleaned up?", "A background job runs every 10 minutes to expire drafts and clean up related records."),
    ("How often are renewal notifications sent?", "Renewal notification job runs every 10 minutes, checking contracts against configured day thresholds."),
    ("What is Middleware?", "Middleware is the integration hub between DXP, Salesforce, AXP, and email services. Most contract status and order events flow through Middleware."),
    ("What is AXP?", "AXP is the Accounts Experience Platform—the customer-facing portal where end customers view subscriptions, submit amendment requests, and request device transfers."),
    ("What is EMS?", "EMS (Entitlement Management System) is the system of record for licenses. DXP assigns and revokes entitlements through EMS."),
    ("What is IAM?", "Trimble IAM manages user accounts, organizations, dealer permissions, and invitations across Trimble cloud products."),
    ("What happens when I decline a positive request?", "The customer is notified that the dealer declined their amendment request. The request status updates to Declined."),
    ("What happens when I place an amendment order?", "DXP sends the amendment to Salesforce. Status progresses through Amendment Submitted, possibly On Hold, to Amendment Activated."),
    ("Can I cancel an amendment?", "Yes, you can cancel an amendment that has not yet activated. Cancelled amendments cannot be reactivated—you must create a new amendment."),
    ("Can I cancel a contract?", "Contracts can be cancelled before activation or when on regulatory hold. Activated contracts typically require amendment for cancellation of quantities."),
    ("What is a purchase order number?", "An optional customer PO reference you can save on draft contracts and amendment quotes before submission."),
    ("Why is approval status Pending?", "Your discount or billing frequency change requires order management approval. The contract or amendment is On Hold until approved or rejected."),
    ("What happens when approval is rejected?", "The discount or billing frequency change is declined. Status reason updates. You may withdraw the change and reprice without the discount."),
    ("How do I withdraw an approval request?", "Use Withdraw Approval on the contract to cancel your pending discount, promo, or billing frequency change request."),
    ("What is organization verification?", "Confirming the customer's business organization in Trimble IAM. Required before transactional operations."),
    ("How do I verify an organization?", "Use Verify Organization on the customer record. If address update is needed, use Verify Organization With Address."),
    ("Why is my customer missing organization?", "Organization must be created or assigned before contracts can be created. Use Create or Assign Organization."),
    ("What email format is required for customers?", "Valid email format required. Phone numbers must be E.164 format (e.g., +12025551234)."),
    ("Why is email domain blocked?", "Customer user email domain must match your dealer business domain for security."),
    ("How do I invite a secondary owner?", "Use Update Secondary Owners or Update Customer Users on the customer record. Requires Secondary Owner Manage permission."),
    ("How do I resend an invitation?", "Use Resend Invitation on the pending user. Invitations can expire if not accepted."),
    ("What does invitation Pending mean?", "User has been invited but has not yet accepted. Contract activation may be blocked until owner accepts."),
    ("What does invitation Expired mean?", "Invitation was not accepted in time. Resend invitation or invite a new user."),
    ("How do I link an existing customer?", "Use Link Existing Customer to connect an IAM account already in Trimble's system to your dealer portfolio."),
    ("What is a portfolio access type?", "Dealer account capability from Salesforce determining which products and services the dealer can sell. NEEDS VALIDATION on display labels."),
    ("Why do I see Contract Missing Base Products?", "Renewal or amendment validation detected add-on products without required base products. Add the base product to proceed."),
    ("What is device export?", "Export dealer device inventory to CSV. Initiated asynchronously; progress shown via real-time subscription."),
    ("How do I change notification preferences?", "Go to Notification Settings. Configure by category or by specific event. Requires Manage Notification or Email Settings permission."),
    ("What is the difference between in-app and email notifications?", "In-app notifications appear in DXP. Email notifications are sent separately via Middleware TES. Each can be configured independently."),
    ("Why is my renewal quote not appearing?", "After starting renewal, Salesforce creates the quote asynchronously. Wait for the renewal.created event. If delayed, check for Renewal Error status."),
    ("What is Renewal Error?", "An error occurred during renewal initiation. Check dashboard events. You may need to retry starting renewal."),
    ("What is Renewal Initiated?", "You have started renewal. The system is waiting for Salesforce to create the renewal quote."),
    ("What is Renewal In Progress?", "Renewal quote exists and you are editing or preparing to submit the renewal."),
    ("What is Renewal Completed?", "Renewal contract has been successfully activated."),
    ("Can I edit renewal term?", "Yes, while renewal is in progress use Edit Renewal Quote to change term, end date, promo code, or renewal type."),
    ("What is manual vs auto renewal type?", "Manual renewal requires dealer action to start and submit. Auto renewal is initiated by Salesforce based on auto-renew settings."),
    ("What notifications happen at 60 days before renewal?", "For annual contracts, regular renewal notifications begin at 60 days before renewal date."),
    ("What notifications happen at 14 days before renewal?", "For monthly contracts, regular renewal notifications begin at 14 days before renewal date."),
    ("What is late renewal grace period?", "Late renewal is available 1-30 days after contract expiration (grace period)."),
    ("Why can't I delete a negative request?", "You may lack permission or the request has already been processed. Ensure you have contract manage permission."),
    ("What is a discretionary discount?", "A dealer-applied discount within the 0.5%-99.4% range. May require approval depending on amount and product rules."),
    ("What is a promo code?", "A promotional discount code applied during repricing. Cannot apply new promo while approval is pending."),
    ("What is billing frequency?", "How the customer is billed: Upfront, Monthly, or Annual. Changes may require approval."),
    ("Why was my billing frequency change declined?", "Order management rejected the billing frequency change. Status reason shows Billing Frequency Changes Declined."),
    ("What is an add-on product?", "A product that requires a base product. Validation ensures compatible base exists before ordering."),
    ("What is a base product?", "The primary subscription product. Add-ons attach to base products."),
    ("How do I validate add-on and base compatibility?", "Use the add-on base validation query when building quotes. System checks product family compatibility."),
    ("What is migrated contract restriction?", "Contracts migrated from legacy systems may have restrictions on certain amendment types."),
    ("Why is entitlement not found?", "The requested entitlement does not exist in EMS for this contract line. Verify contract is activated and product is on the contract."),
    ("What is duplicate transfer request?", "A transfer request already exists for this device. Cancel or complete the existing request first."),
    ("How do I cancel a device transfer?", "Use Cancel Transfer on the device while transfer is Pending or Scheduled."),
    ("What is revoke and transfer?", "Revokes active subscription on device and completes the transfer in one operation when license conflicts exist."),
    ("What is revoke and cancel transfer?", "Revokes subscription and cancels a pending transfer simultaneously."),
    ("What is an external subscription?", "A subscription managed outside standard EMS assignment. Cannot be revoked through DXP."),
    ("What is a non-IoT device?", "Non-IoT (e.g., Arrowhead) hardware with different transfer and revocation rules than IoT devices."),
    ("What is an IoT device?", "Connected IoT hardware. Different subscription and transfer rules apply when customer-owned."),
    ("How do I save dealer account defaults?", "Use Save Dealer Account Defaults for bill-to address and contact defaults applied to new contracts."),
    ("How do I save customer defaults?", "Use Save Dealer Customer Defaults for ship-to contact and address defaults applied to new contracts for that customer."),
    ("What is audit log?", "Read-only history of actions on contracts, customers, devices, and dealer settings. Requires View Audit permission."),
    ("Can I view another dealer's contracts?", "No. Resource ownership guards prevent cross-dealer access even if you have broad permissions."),
    ("What header is required for dealer context?", "API requests require the dealer account ID header so DXP scopes data and permissions correctly. NEEDS VALIDATION on UI behavior."),
    ("What is a contract version?", "Snapshot of contract state saved at activation. View historical version by ID."),
    ("What is co-term contract?", "Contracts aligned to end on the same date. Query co-term contracts for renewal alignment."),
    ("What is product term compatibility?", "Check which terms (monthly/yearly) are valid for selected products before creating a contract."),
    ("What is trial eligibility?", "System checks via DxTrial Service whether customer/product qualifies for trial. Trial products flagged in catalog."),
    ("Why is my contract activation reminder sent?", "EMS sends reminders when account owner has not activated within expected timeframe."),
    ("What is price change hold?", "When repricing changes the total, order management may hold the amendment for review before processing."),
    ("How do I approve and resubmit pricing?", "On a price-change hold, review the new pricing and use Approve and Resubmit Pricing to continue amendment processing."),
    ("What is dismiss approval request?", "Dismisses a pending approval notification without withdrawing the underlying request. Different from withdraw approval."),
    ("What is the difference between cancel and delete for amendments?", "Delete removes an amendment draft. Cancel cancels a submitted amendment before activation."),
    ("What is mark amendment cancelled as processed?", "Marks a cancelled amendment notification as handled in your workflow."),
    ("What is align end date renewal?", "Co-term renewal by aligning end dates across contracts, then repricing."),
    ("What is update term UOM renewal?", "Change renewal term between monthly and yearly, then reprice."),
    ("What is partial vs full upgrade?", "Partial upgrade adds quantity of higher-tier product. Full upgrade replaces entire quantity."),
    ("What is partial cancellation?", "Reduces quantity of a product without removing entirely."),
    ("What is full cancellation?", "Removes all quantity of a product from the contract."),
    ("What is add seats?", "Amendment action to increase seat quantity on existing product."),
    ("What is add product?", "Amendment action to add a new product to the contract."),
    ("Why can't I upgrade from product A to B?", "Product upgrade path may not be valid for this account or product family. Check upgrade compatibility."),
    ("Why can't I downgrade?", "Downgrade quantity, product compatibility, or entitlement rules may block the operation."),
    ("What is license selection type Random vs Manual?", "For negative requests specifying which licenses to remove: system selects randomly or dealer selects manually."),
    ("What is a attention event Contract Error?", "Dashboard alert for a contract in Error status needing investigation."),
    ("What is attention event Contract Expiring?", "Dashboard alert that contract is approaching expiration and renewal action may be needed."),
    ("What is attention event Pending Assignment?", "Activated contract has subscriptions not yet assigned to devices or users."),
    ("What is attention event Transfer Request?", "Customer has requested device transfer requiring your approval."),
    ("How do I ignore a dashboard event?", "Use Ignore on the attention event once addressed. Event can be unresolved if issue persists."),
    ("What is Service Bus?", "Azure Service Bus messaging used for async communication between DXP, Middleware, Salesforce, and AXP."),
    ("What is Kafka in DXP?", "DXP does not use Kafka directly. IAM events are consumed via Trimble Cloud Events Service which is Kafka-backed internally."),
    ("What happens if Service Bus message fails?", "Messages are typically retried by Service Bus. Persistent failures may leave status stale until manual intervention."),
    ("What is ProductSyncService?", "Azure Function that syncs Salesforce product catalog changes into DXP database."),
    ("What is EmailNotificationScheduler?", "Azure Function that sends contract, amendment, renewal, and on-hold emails triggered by Service Bus events and timers."),
    ("What is HandleExpiryHostedService?", "Background service running every 10 minutes to expire drafts, requests, and clean dashboard."),
    ("What is AmendmentActivationHostedService?", "Background service every 5 minutes activating amendments whose start date has passed."),
    ("What is EventsServiceMonitor?", "Background service polling Trimble Events Service for IAM account and user changes."),
    ("What is permission cache?", "DXP caches IAM permissions for performance. Cache invalidated on IAM user/account update events."),
    ("Why did my permission change not take effect?", "Permission cache may need refresh. IAM update events trigger invalidation. Try logging out and back in."),
    ("What is feature flag USER_SUBSCRIPTIONS?", "Feature flag enabling seat-based user subscription assignment. If disabled, only device assignment available."),
    ("What is feature flag organization guard?", "When enabled, strictly enforces organization verification before transactional operations."),
    ("What currencies are supported?", "Product pricing is country and currency specific. Dealer account has configured currency (e.g., USD, EUR)."),
    ("How do I search for organizations?", "Use Search Organizations to find existing IAM organizations to assign to customers."),
    ("What is CDH?", "Customer Data Hub—Trimble's account and address registry. Bill-to and ship-to account IDs reference CDH."),
    ("What is PCS?", "Product Catalog Service—source for device part numbers and hardware catalog information."),
    ("What is real-time contract status?", "DXP offers contractStatusChanged GraphQL subscription for live status updates in the UI without manual refresh."),
    ("What is notificationReceived subscription?", "Real-time push when new in-app notification arrives."),
    ("What is dashboardEventChanged subscription?", "Real-time push when dashboard attention events change."),
    ("What is deviceExportChanged subscription?", "Real-time push for device CSV export progress and completion."),
]

for i, (q, a) in enumerate(FAQ_DATA):
    slug = f"faq-{i+1:03d}"
    write_chunk("faq", slug, q, ["faq"], f"**Q:** {q}\n\n**A:** {a}")

print(f"Generated chunks. FAQ count: {len(FAQ_DATA)}")
total = sum(1 for _ in CHUNKS.rglob("*.md"))
print(f"Total chunk files: {total}")

