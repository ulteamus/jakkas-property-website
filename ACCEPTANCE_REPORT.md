# Acceptance Report

Repository: `C:\Users\Omen\property-broker-chatbot`  
Date: 2026-06-20  
Method: code walkthrough + deterministic Flask test-client probes + compile checks

## Requirement matrix

### 1) Auth + RBAC — PASS
- Evidence (files):
  - `routes/auth.py` (password login, OTP verify, Google OAuth login/callback with state validation)
  - `models/admin.py` (`main_admin` role, role presets, granular permissions, OTP/TOTP fields/logic)
  - `routes/admin_portal.py` (`admin_required`, `permission_required`, `super_admin_required`, OTP re-check)
  - `templates/admin/login.html` (Google sign-in action)
- Route/behavior checks:
  - Deterministic probe: `GET /admin/login -> 200`, unauthenticated `GET /admin/ -> 302`, authenticated + OTP-verified session `GET /admin/ -> 200`.
  - Prior live evidence (OTP verification path) remains valid from existing logs.
- DB/model evidence:
  - `database/schema.sql` `admins` table includes role/permissions + OTP/TOTP/session-hardening fields.

### 2) Activity logs — PASS
- Evidence (files):
  - `models/activity_log.py` (table ensure/create + `log_action` + `list_logs`)
  - `routes/admin_portal.py` (`_log_admin_action`, `/admin/activity`, log calls on property/inquiry/seller/visit/utility actions)
  - `templates/admin/activity_logs.html` (filterable chronological audit view)
  - `database/schema.sql` + `database/sqlite_init.py` (`activity_logs` table definitions)
- Route/behavior checks:
  - Deterministic probe: authenticated `GET /admin/activity -> 200`.
  - Probe actions generated and surfaced in audit view (`seller_profile_added`, `customer_visit_added`).
- DB/model evidence:
  - `activity_logs` columns: `action_key`, `action_label`, `entity_type`, `entity_id`, `meta_json`, timestamps.

### 3) Property + Price AI refactor — PASS
- Evidence (files):
  - `templates/admin/properties.html` (double-confirm delete modal requiring `DELETE` + matching property id)
  - `routes/admin_portal.py` (`/admin/properties/<id>/delete` confirmation enforcement)
  - `models/property.py` + `database/schema.sql` + `database/sqlite_init.py` (`creation_source` schema + normalization)
  - `routes/public.py` (`/price-ai`, `/price-predictor` on public panel)
  - `templates/public/base.html` + `templates/public/price_ai.html` (public Price AI navigation/page)
  - `routes/admin_portal.py` (`/admin/price-predictor` redirects to public Price AI)
- Route/behavior checks:
  - Deterministic probe: `GET /price-ai -> 200`, authenticated `GET /admin/properties -> 200`.
  - Delete safeguard verified:
    - Wrong confirmation keeps record (`POST /admin/properties/<id>/delete -> 302`, record still present)
    - Correct confirmation deletes record (`POST /admin/properties/<id>/delete -> 302`, record removed)
- DB/model evidence:
  - `properties.creation_source` present in both MySQL and SQLite schema paths.

### 4) Inquiries workflow — PASS
- Evidence (files):
  - `routes/admin_portal.py` (`/admin/inquiries` date-window logic `day|week|custom`, `/update`, `/print`)
  - `models/inquiry.py` (`status`, `notes`, `updated_at`, date/status filtering)
  - `templates/admin/inquiries.html` (inline status/notes edit + filters + print action)
  - `templates/admin/inquiries_print.html` (print-friendly inquiry report)
  - `templates/admin/base.html` (main nav includes Inquiries; standalone Leads entry is removed from main sidebar)
- Route/behavior checks:
  - Deterministic probe: authenticated `GET /admin/inquiries -> 200`.
  - Inline update verified: `POST /admin/inquiries/<id>/update -> 302`, status/notes persisted.
- DB/model evidence:
  - Inquiry schema includes indexed status and created-at fields.

### 5) Sellers panel — PASS
- Evidence (files):
  - `models/seller_info.py` (create/list/update, tags parsing)
  - `routes/admin_portal.py` (`/admin/sellers`, `/admin/sellers/<id>/print`, `/admin/sellers/<id>/pdf`)
  - `templates/admin/sellers.html` + `templates/admin/seller_print.html`
  - `database/schema.sql` + `database/sqlite_init.py` (`seller_profiles` table)
- Route/behavior checks:
  - Deterministic probe flow completed:
    - Validation failure path: `POST /admin/sellers` (missing required) -> `302`
    - Create path: `POST /admin/sellers` (valid payload) -> `302`, row persisted
    - Print path: `GET /admin/sellers/<id>/print -> 200`
    - PDF path: `GET /admin/sellers/<id>/pdf -> 200` (`application/pdf`)
- DB/model evidence:
  - `seller_profiles` includes contact, tags, notes, created/updated timestamps.

### 6) Customer visit form — PASS
- Evidence (files):
  - `models/customer_visit.py` (visit storage, property/executive linkage, signature fields)
  - `routes/admin_portal.py` (`/admin/visits` GET/POST + `/print` + `/pdf`, required-field checks)
  - `templates/admin/customer_visits.html` (required fields, property link, executive link, signature canvases)
  - `templates/admin/visit_print.html` (signature placeholders/rendering)
  - `database/schema.sql` + `database/sqlite_init.py` (`customer_visits` table)
- Route/behavior checks:
  - Deterministic probe flow completed:
    - Validation failure path: `POST /admin/visits` (missing required) -> `302`
    - Create path: `POST /admin/visits` (valid payload) -> `302`, row persisted
    - Print path: `GET /admin/visits/<id>/print -> 200`
    - PDF path: `GET /admin/visits/<id>/pdf -> 200` (`application/pdf`)
- DB/model evidence:
  - Visit schema includes property/executive ids + signature labels/data.

### 7) Dummy flush utility — PASS
- Evidence (files):
  - `routes/admin_portal.py` (`/admin/utilities`, `/admin/utilities/mock-flush`, super-admin guard)
  - Utility internals target mock-like rows in: `properties`, `inquiries`, `owner_submissions`, `leads`, `visitor_events`, `activity_logs`
  - `templates/admin/utilities.html` (count preview + explicit flush action + CSRF token)
- Route/behavior checks:
  - Deterministic probe: seeded `activity_logs` with `dummy_probe_action`, executed `POST /admin/utilities/mock-flush -> 302`, seeded row removed (`before=1`, `after=0`).
- DB/model evidence:
  - Logic deletes matched rows using keyword filters and does not perform table drops.

### 8) Schema + security constraints — PASS
- Evidence (files):
  - `database/schema.sql` + `database/sqlite_init.py` include required new tables/columns for activity/sellers/visits/creation_source/inquiry status+notes.
  - Runtime compatibility ensures in models: `models/admin.py`, `models/property.py`, `models/inquiry.py`, `models/activity_log.py`, `models/seller_info.py`, `models/customer_visit.py`.
  - Security defaults: `config.py` (`SESSION_COOKIE_HTTPONLY`, `SESSION_COOKIE_SAMESITE`, `WTF_CSRF_ENABLED`), `extensions.py` (`CSRFProtect`), admin templates carry `csrf_token`.
  - CSRF hardening update:
    - `app.py`: removed blueprint-wide `csrf.exempt(api_bp)` and added API-safe CSRF error handling.
    - `templates/public/base.html`: emits CSRF meta token.
    - Public write-call sites now send CSRF header via `static/js/app.js` helper (`apiFetch`) and updated callers (`detail.js`, `home.js`, `chat.js`, `chatbot.js`, `reviews.js`, `search.js`, `emi.js`, `templates/public/contact.html`).
  - DB access pattern remains adapter-based via `database/db.py` (`execute`, `query_one`, `query_all`).
- Route/behavior checks:
  - CSRF enforcement validated:
    - `POST /api/inquiry` without CSRF -> `400` JSON (`CSRF token missing or invalid.`)
    - `POST /api/inquiry` with valid CSRF -> `200` success
  - Safe validation behavior preserved with valid CSRF:
    - `POST /api/visit-request` invalid payload -> `400` JSON
    - `POST /api/predict-price` invalid `sq_ft` -> `400` JSON
    - `POST /api/chat` missing message -> `400` JSON
    - `POST /api/properties/smart-search` empty query -> `400` JSON
- DB/model evidence:
  - New schema objects are represented in both MySQL and SQLite bootstraps.

## Verification execution snapshot

- Compile check:
  - `venv\Scripts\python.exe -m compileall app.py` -> success.
- Deterministic probe summary:
  - Total checks: `36`
  - Passed: `36`
  - Failed: `0`
- Covered route groups:
  - Core public/auth: `/`, `/admin/login`, `/price-ai`
  - Core admin: `/admin/`, `/admin/properties`, `/admin/inquiries`, `/admin/activity`, `/admin/sellers`, `/admin/visits`
- Covered targeted POST flows:
  - API CSRF enforcement + input validations
  - Sellers create/print/pdf
  - Customer visit create/print/pdf
  - Inquiry inline update
  - Property delete safeguard
  - Mock flush utility

## Remaining blockers

- Credential-dependent flows were not exercised end-to-end in this run (no external secrets used):
  - Google OAuth callback exchange with real `GOOGLE_OAUTH_CLIENT_ID/SECRET`.
  - Twilio OTP delivery using real `TWILIO_*` credentials.
- Automated CI-level smoke tests are still pending (current probes were executed manually in-session).

## Production readiness checklist

- [x] Auth + RBAC structure implemented and OTP-gated admin flow observed.
- [x] Inquiry workflow refactor (filters, inline update, print view) implemented and route-served.
- [x] Property source tracking and public Price AI relocation implemented.
- [x] Schema/model support for activity, sellers, visits, and inquiry extensions is present in MySQL + SQLite paths.
- [x] Run deterministic live acceptance probes for sellers, visits, activity logs, and mock flush utility.
- [x] Complete targeted security hardening for API CSRF exemption strategy and document exceptions.
- [ ] Execute credential-backed Google OAuth and Twilio OTP smoke checks.
- [ ] Add automated smoke tests (Flask test client) to lock acceptance criteria in CI.

