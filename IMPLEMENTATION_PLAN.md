# Implementation Plan

This plan is organized in phases and maps each checklist item to requirements A-G.

## Phase 1 - Auth, RBAC, and Security Baseline

### A) Auth + RBAC updates
- [x] Add Google OAuth admin login flow in `routes/auth.py` with secure state validation and callback handling.
- [x] Preserve Flask-Login session lifecycle and existing OTP/TOTP second-factor behavior.
- [x] Extend role model to support `main_admin` and keep `super_admin` full-control behavior.
- [x] Keep `executive` default scope limited to operational data-entry/view/edit modules.
- [x] Preserve granular permission assignment and enforce via existing route-level permission decorators.
- [x] Update login UI to expose Google sign-in option.

### Security constraints applied in this phase
- [x] Keep secrets in environment variables (Google OAuth and SMS credentials).
- [x] Do not bypass existing Flask-Login guards and decorator checks.

## Phase 2 - Schema and Model Foundations

### G) DB schema + compatibility
- [x] Update MySQL schema (`database/schema.sql`) for all new columns/tables.
- [x] Update SQLite bootstrap schema (`database/sqlite_init.py`) for all new columns/tables.
- [x] Add safe runtime schema-ensure logic in models for MySQL + SQLite compatibility.
- [x] Keep all DB interactions through existing `database/db.py` adapters (`execute`, `query_one`, `query_all`).

### B) Activity logging (data layer)
- [x] Add `activity_logs` model/table with compatibility-safe creation/ensure logic.
- [x] Provide reusable logging helper for admin actions.

### C/D/E/F data model changes
- [x] Add `properties.creation_source` (`admin`/`user_submission`) support.
- [x] Extend inquiries model with editable status/notes and date filtering support.
- [x] Add sellers info storage model/table.
- [x] Add customer visit form storage model/table (property link + executive link + signature fields).

## Phase 3 - Admin Route and Workflow Implementation

### B) Activity logging (route integration)
- [x] Log: add property action.
- [x] Log: property status change action.
- [x] Log: sensitive detail-view action (inquiries and related sensitive modules).
- [x] Add super-admin activity dashboard route/page with chronological listing.

### C) Property management + Price AI migration
- [x] Add double-confirm delete safeguard on admin properties page (modal-based secondary confirmation).
- [x] Wire `creation_source` through property create flows (admin vs user submission).
- [x] Remove Price AI from admin navigation/workflow.
- [x] Add public Price AI route/page using existing prediction backend service.

### D) Leads/Inquiries workflow updates
- [x] Remove/hide standalone Leads entry from main admin navigation.
- [x] Add inquiries date-range filtering (`day`, `week`, `custom`).
- [x] Add inquiries inline status/notes editing.
- [x] Add print-friendly inquiries output action/page.

### E) New admin modules
- [x] Add Sellers Info panel (create/list records with tags/notes).
- [x] Add Sellers print output + PDF download endpoints.
- [x] Add Customer Visit Form module with required fields and property linkage.
- [x] Add executive linkage fields for customer visit form when available.
- [x] Add customer/executive signature capture placeholders/areas.

### F) Admin utility
- [x] Add super-admin-only dummy/mock data flush tool route/page.
- [x] Flush mock rows from listings, inquiries, and event/log-like datasets without dropping tables.

## Phase 4 - Templates, CSRF, and UX Hardening

- [x] Ensure all new admin POST forms include CSRF token fields.
- [x] Add/update admin templates for activity, inquiries, sellers, visits, and utility workflows.
- [x] Add/update public template for Price AI page while preserving existing user panel styling.

## Phase 5 - Verification and Debugging

- [x] Run Python compile checks for touched Python files.
- [x] Run route checks for `/`, `/admin/login`, `/admin/`, `/admin/properties`, `/admin/inquiries`, new activity/sellers/visit routes, and public Price AI route.
- [x] Run key POST flow checks where feasible (property create/update/delete safeguards, inquiry inline updates, sellers/visit create, utility flush).
- [x] Document final completion summary with implemented scope, changed files, schema updates, verification output, and any caveats.

Verification note: deterministic Flask test-client probes were executed successfully for core route coverage, targeted POST validations, and admin workflows (activity, sellers, visits, mock flush), plus compile checks for touched Python files.
