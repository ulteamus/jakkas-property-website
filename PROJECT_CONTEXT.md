# JAKKASH PROPERTY CONSULTANCY — Project Context & Architecture Report

> Generated for external AI handoff (e.g. Gemini). Reflects the live Flask SSR codebase in `property-broker-chatbot` (production: https://property-broker-chatbot-jakkash.vercel.app/).

---

## 1. Project Overview & Business Goals

### 1.1 Primary purpose

**JAKKASH PROPERTY CONSULTANCY** is a Surat-focused real-estate brokerage platform. The website is the public storefront and CRM backend for:

- Discovering residential and commercial listings across Surat localities (Vesu, Adajan, Pal, Piplod, Ring Road, etc.).
- Capturing buyer/renter inquiries, site-visit requests, and WhatsApp/call engagement.
- Letting owners, brokers, and developers submit sell/rent listings for admin verification before they go public.
- Giving the brokerage team a permissioned admin “command center” for inventory, leads, inquiries, visits, reviews, and analytics.

Company constants (from `config.py`):

| Field | Value |
|--------|--------|
| Brand | JAKKASH PROPERTY CONSULTANCY |
| Office | 40, Ganesh Krupa Soc, Opp Gail Tower, Anand Mahal Road, Surat 395009 |
| Phone / WhatsApp | +91 85117-51119 |
| Map center | Lat 21.1702, Lng 72.8311 (Surat) |

### 1.2 Target audience

| Audience | Needs the product serves |
|----------|--------------------------|
| **Buyers** | Browse flats/bungalows/plots, filter by area/BHK/budget, inquire, request site visits, save listings, use map |
| **Renters** | Same discovery flows with listing intent `rent` |
| **Sellers / owners** | Submit property via Sell/Rent form; tracked as pending until admin approval |
| **Brokers / developers** | Same submission path with seller type tagged (`owner` / `broker` / `developer`) |
| **Internal staff** | Admins, managers, executives, callers, brokers — role-scoped CRM |

### 1.3 Core user journeys

1. **Discover → Detail → Inquire**  
   Home / `/properties` → `/property/<slug>` → Send Inquiry / Site Visit / WhatsApp / Call / Save / Share.

2. **Sell or Rent my property**  
   `/sell-property` → fill contact + property + media → creates `reserved` property + `owner_submissions` (pending) → admin approves → listing becomes `available`.

3. **Guided assistant**  
   `/chatbot` (menu-driven Property Assistant) → Browse / Sell / Broker / FAQ chips → deep links or WhatsApp.

4. **Staff operations**  
   `/admin/login` → dashboard → properties, sell-properties approvals, inquiries (3-way categories), leads, visits, reviews, analytics, employees.

---

## 2. Tech Stack & Architecture Structure

### 2.1 Stack summary

| Layer | Technology |
|-------|------------|
| **Backend** | Python 3.11+ / Flask 3.x monolith |
| **Auth** | Flask-Login (session cookies), optional TOTP (`pyotp`) + mobile OTP (Twilio path) |
| **Forms / CSRF** | Flask-WTF / WTForms on HTML forms; `/api` blueprint CSRF-exempt |
| **DB** | MySQL (`mysql-connector-python`) primary; SQLite fallback for local/Vercel (`USE_SQLITE`, `api/seed/jakkash.db`) |
| **Frontend** | Server-rendered Jinja2 HTML (not React/Next) |
| **UI kit** | Bootstrap 5, Bootstrap Icons |
| **Styling** | Custom CSS (`static/css/jakkash.css`, `admin.css`, theme helpers) — **frontend design is locked** |
| **Client JS** | Vanilla JS modules (`listings.js`, `detail.js`, `sell_property.js`, `chatbot.js`, `media_file_manager.js`, etc.) |
| **Maps** | Leaflet.js + OpenStreetMap |
| **ML (optional)** | scikit-learn / pandas / numpy joblib models under `ml/models` (lead scoring, price prediction) |
| **Hosting** | Vercel (`api/index.py` Python serverless + static assets); GitHub: `ulteamus/property-broker-chatbot-jakkash` |
| **State** | No Redux/Zustand — Flask server sessions (`session_id`, `visitor_id`, permanent cookies for saved properties) + DB |

### 2.2 Architecture style

**Flask SSR monolith + JSON API:**

```text
Browser (Jinja HTML + Bootstrap + vanilla JS)
    │
    ├─ Page routes  → routes/public.py | routes/admin_portal.py | routes/auth.py
    ├─ JSON /api/*  → routes/api.py
    │
    ▼
models/*.py  →  database/db.py  →  MySQL or SQLite
    │
services/*.py (scoring, recommendations, WhatsApp, OTP, price prediction)
```

**Vercel note:** On deploy, `scripts/vercel_bundle.py` embeds templates into `api/template_store.py` (DictLoader preferred over disk) and mirrors `static/` → `api/static/` + `public/`. Uploads on Vercel use `/tmp/uploads/properties`.

### 2.3 Directory map (active surface)

```text
property-broker-chatbot/
├── app.py                 # create_app(), blueprints, session IDs, uploads route
├── config.py              # company, DB, upload, property-type constants
├── extensions.py          # LoginManager, CSRFProtect
├── api/
│   ├── index.py           # Vercel WSGI entry
│   ├── template_store.py  # Embedded Jinja templates for serverless
│   ├── templates/         # Mirror of templates (also used when present)
│   ├── static/            # Mirror of static
│   └── seed/jakkash.db    # SQLite seed for serverless
├── database/
│   ├── db.py              # dual MySQL/SQLite connection + adapt_sql
│   ├── schema.sql         # canonical MySQL schema
│   └── sqlite_init.py     # SQLite bootstrap + INSERT OR IGNORE adaptation
├── models/                # admin, property, submission, inquiry, lead, reviews,
│                          # customer_visit, analytics, …
├── routes/
│   ├── public.py          # public pages + sell-property POST
│   ├── admin_portal.py    # active admin CRM
│   ├── api.py             # JSON APIs
│   └── auth.py            # login / OTP / logout
├── services/              # lead_scoring, recommendation, price_prediction,
│                          # whatsapp, mobile_otp, follow_up
├── templates/
│   ├── public/            # base, home, listings, detail, sell_property, chatbot, …
│   └── admin/             # base, dashboard, properties, inquiries, visits, …
├── static/css|js|img/
├── uploads/properties/    # local media
├── ml/                    # train_models.py + optional .pkl models
├── scripts/vercel_bundle.py
└── .agents/skills/        # Impeccable, Vercel skills (mostly unused for locked UI)
```

Legacy / unused: `routes/main.py`, `routes/admin.py`, root `templates/*.html` tied to old flows — **not registered** in `create_app()`.

### 2.4 Data fetching, routing, auth

**Routing**

- Blueprints: `public_bp`, `auth_bp`, `api_bp`, `admin_bp` (`url_prefix=/admin` for portal).
- Public pages are classic Flask `render_template(...)`.
- Listings load filters from query string; cards refresh via `GET /api/properties`.
- Detail page uses SSR property + client JS for inquiry/visit/share/save.

**Data access**

- Thin SQL helpers: `execute`, `query_one`, `query_all` in `database/db.py`.
- Models own `_ensure_schema()` / `_ensure_table()` for **idempotent** `ALTER TABLE ADD COLUMN` (MySQL `SHOW COLUMNS` / SQLite `PRAGMA table_info`) so MySQL and Vercel SQLite stay compatible without destructive migrations.
- Persistence rule: `owner_submissions`, `properties`, `inquiries`, `customer_visits`, `reviews` are permanent until an **explicit admin DELETE**.

**Authentication / authorization**

- Admin identity: `models.admin.Admin` loaded by Flask-Login `user_loader`.
- Login: `/admin/login` → optional OTP at `/admin/verify` → dashboard.
- Decorators: `@admin_required`, `@permission_required("manage_*")`, `@super_admin_required`.
- Roles: `super_admin`, `main_admin`, `manager`, `executive`, `caller`, `broker` with permission presets (`manage_properties`, `manage_leads`, `manage_inquiries`, `manage_submissions`, `manage_customer_visits`, etc.).
- Non-manager staff are often **owner-scoped** (`owner_admin_id` on properties/submissions/inquiries).
- Public users are anonymous; engagement uses permanent session cookies (`session.permanent = True`).

---

## 3. Features & Implementations (What We Did & How)

### 3.1 Public-facing features

| Page / route | Implementation notes |
|--------------|----------------------|
| **Home `/`** | Featured/latest listings, category entry points, About split (`.jv-about-split`), testimonials preview, CTAs to listings / sell / chatbot. Mobile About spacing tightened under `@media (max-width: 767.98px)` only. |
| **Properties `/properties`** | Filter drawer (area, type, price, BHK, listing intent buy/sell/rent, sort). Grid/list via `listings.js` + `/api/properties`. Cards from `public/_property_card.html`. |
| **Detail `/property/<slug>`** | Gallery, locality-masked public address, amenities, map, WhatsApp/Call, Send Inquiry (smooth-scroll + focus name), Site Visit, Save, Share (`navigator.share` + clipboard fallback). |
| **Map `/map`** | Leaflet markers from `/api/properties/map`. |
| **About `/about`** | Brand story + stats. |
| **Services `/services`** | Brokerage service summary. |
| **Testimonials `/testimonials`** | DB-backed `testimonials` + comments; public POST via `/api/reviews`. |
| **Contact `/contact`** | Contact / visit-request surface → inquiry APIs. |
| **Saved `/saved`** | Session-backed `saved_properties` via `/api/saved`. |
| **Compare `/compare`** | Client compare helper. |
| **Price AI `/price-ai`** | UI + `/api/predict-price`. |

**Property types supported:** apartment/flat, villa/bungalow, plot/land, shop, office, commercial/residential aliases (normalized in `models/property.py`).

**Listing intents:** `sell` / `rent` (stored as `listing_intent`; synced with `listing_type` `sale`/`rent`).

### 3.2 Sell / Rent property workflow

**Routes:** `/sell-property`, `/list-property`, `/list-your-property` → `routes/public.py::sell_property`.

**Form UX (`templates/public/sell_property.html` + `static/js/sell_property.js`):**

1. **Listing intent** — Sell vs Rent segmented chips.
2. **Seller type** — Owner / Broker / Developer (stored as `seller_type` + `submitter_type`).
3. **Contact** — Name, mobile, alt mobile, email, residential address (mandatory contact block).
4. **Property** — City, locality, type chips, title, conditional **BHK** (hidden for plot/land/shop/office), **Block/Wing** + **Unit Number** for apartments/flats.
5. **Area & price** — Area value + unit chips (sq ft / sq yard / vigha / sq meter) with dynamic labels; converted to `sq_ft`; expected INR price.
6. **Address & description**, amenities checkboxes.
7. **Media** — Multi-file images/videos via `media_file_manager.js` (DataTransfer list + per-file remove).

**Backend on POST:**

1. Validate required fields; normalize type and intent.
2. `prop_model.create(..., status="reserved", creation_source="user_submission", listing_intent, seller_type, block_wing, unit_number)`.
3. Save uploads under property media tables.
4. `submission_model.create_submission(...)` with `status="pending"`, linked `property_id`.
5. Create an inquiry (`inquiry_type="property"`, source `property_submission`).
6. Flash success — **not public until admin approval**.

**Admin approval (`/admin/sell-properties/<id>/approve`):**

- Sets submission status `approved` (**never deletes** the submission row).
- Sets linked property `available`; if `property_id` missing, creates property then `link_property`.
- Reject / pending similarly toggle property to `reserved` when applicable.
- Explicit delete only via dedicated DELETE action.

### 3.3 Admin portal

**Base:** `templates/admin/base.html` + `static/css/admin.css`.

| Module | Path | Behavior |
|--------|------|----------|
| Dashboard | `/admin/` | KPIs / shortcuts |
| Properties | `/admin/properties`, add/edit | Full CRUD + media; form parity with sell (intent, seller type, block/unit, BHK hide, media preview) |
| Sell properties | `/admin/sell-properties` | Pending/approved/rejected filters, **area** + **seller_type** filters, print view, approve/reject/edit/delete |
| Inquiries | `/admin/inquiries` | Date/status filters; **3-way tabs**: Site Visit / General / Property-Specific (`inquiry_type`); per-row update/delete; bulk delete; print with category badges |
| Leads | `/admin/leads` | Scoring tiers, notes, PDF export (role-scoped for brokers) |
| Customer visits | `/admin/visits` | Multi-select properties (tag pills + X), signatures, date filter, delete, print/PDF (JAKKASH-branded layout); Linked Executive removed |
| Reviews | `/admin/reviews` | Moderate testimonials/comments |
| Analytics | `/admin/analytics` | Visitor/search/trending aggregates |
| Employees | `/admin/employees` | Role/permission management, TOTP setup |
| Activity | `/admin/activity` | Audit log (super admin) |
| Utilities | `/admin/utilities` | Ops helpers |

Activity logging via `_log_admin_action` on sensitive views and mutations.

### 3.4 Property Assistant & Quick Inquiry

**Property Assistant (`/chatbot`, aliases `/ai-chatbot`, `/chat`):**

- **Not an LLM.** Static menu-driven guide in `static/js/chatbot.js`.
- Decision tree: Browse properties / Sell property / Talk to broker / FAQ.
- Chips open routes (`/properties`, `/sell-property`) or WhatsApp/tel deep links.
- `POST /api/chat` returns a static payload (`_static_chat_payload` in `routes/api.py`) for compatibility.

**Quick Inquiry / lead capture:**

- Detail & listing CTAs → `#inquiryPanel` / `#visitPanel`.
- `POST /api/inquiry` → `inquiry_model.create` + `lead_model.create_from_inquiry`; `inquiry_type` inferred (`general` / `property` / `site_visit`).
- `POST /api/visit-request` → site visit inquiry with `inquiry_type="site_visit"`.
- WhatsApp interest: `POST /api/whatsapp/interest` builds wa.me URL via `services/whatsapp.py`.
- Call clicks tracked: `POST /api/event/call` + analytics events.

---

## 4. Key Components & UI Elements

### 4.1 Layout wrappers

| Template | Role |
|----------|------|
| `templates/public/base.html` | Public chrome: nav, footer, company context, CSS/JS includes, mobile nav |
| `templates/admin/base.html` | Admin shell: sidebar, permission-gated nav, flash messages |
| `public/_property_card.html` | Reusable listing card (image, price, BHK, area, save) |

### 4.2 Primary UI / JS building blocks

| Asset | Role |
|-------|------|
| `jakkash.css` | Brand theme (orange `#F58220` / `#e67e22`, black, white); phone-only media queries |
| `admin.css` | Admin tables, KPI cards, filter chips |
| `sell_property.js` | Intent/seller/type chips, BHK visibility, area labels, validation |
| `media_file_manager.js` | Multi-file DataTransfer preview + remove |
| `listings.js` | Filter sync, fetch `/api/properties`, render cards |
| `detail.js` | Gallery, inquiry/visit scroll+focus, share, forms |
| `chatbot.js` | Menu-driven assistant |
| `app.js` | Shared `apiFetch`, save helpers |

### 4.3 Listing presentation & filters

- **Cards:** Image (primary), property name, locality, price (INR), BHK/sq ft badges, type, save heart.
- **Filters:** Area/locality, type, min/max price, BHK, listing intent, text query, sort — driven by query params and `/api/properties`.
- **Public privacy:** `property.to_dict(public=True)` strips owner PII and uses locality-only address + rounded coordinates.
- **Statuses:** `available` (public), `reserved` (pending approval), `sold`, `rented`.

### 4.4 Form schemas (conceptual)

**Sell/Rent (public):**  
`listing_intent`, `seller_type`/`submitter_type`, owner_*, `property_type`, `property_title`, `bhk?`, `block_wing?`, `unit_number?`, `area_value`+`area_unit`→`area_sq_ft`, `price`, `property_address`, `description`, amenities[], images[], videos[].

**Admin property form:** Same commercial fields + `status`, `listing_intent`, `seller_type`, geo, featured, creation_source, documents.

**Inquiry:** `name`, `mobile`, `email?`, `message?`, `property_id?`, `intent`/`inquiry_type`.

**Visit CRM:** `visit_date`, client_*, `property_ids[]`, executive_*, signature canvases.

---

## 5. Cursor Agents & Skills Used

### 5.1 Project-level governance (this repo)

| Mechanism | Path / note | Effect |
|-----------|-------------|--------|
| **Frontend design lock** | Workspace rule `frontend-design-final` (+ user rule for Jakkash) | **Do not** change `templates/**`, `static/**` UI/CSS unless the user explicitly authorizes a scoped change. Prefer backend-only work. |
| **Agents skills pack** | `.agents/skills/` | Includes `impeccable`, `design-motion-principles`, `vercel-composition-patterns`, `vercel-optimize`, `vercel-react-best-practices`, `deploy-to-vercel` — available but **UI design skills must not be applied** against the locked frontend. |
| **Hooks** | `.cursor/hooks.json` | Cursor hook configuration for the workspace. |
| **Context docs** | `CONTEXT.md`, `README.md` | Human/agent onboarding snapshots (this report supersedes for Gemini handoff). |

### 5.2 Cross-cutting agent preferences (operator machine)

These influence how Cursor agents work on this machine (not all are committed in-repo):

- **Ponytail** — YAGNI / minimal diffs.
- **Heavy Agentic / OmniRoute / Headroom** — routing and context compression preferences.
- **Codebase Memory MCP** — graph index for this repo (`~8k` nodes) for architecture/search.
- **No unsolicited commits** — commit/push/deploy only when the user asks (this project’s production deploy pattern: push `HEAD:main`, then Vercel prod from a no-`.git` staging copy when needed).

### 5.3 Implementation patterns agents must keep

1. Dual-DB idempotent schema ensures (`_ensure_schema`) — never truncate/drop live CRM tables.
2. Mobile CSS only inside `@media (max-width: 767.98px)` when UI edits are authorized.
3. After template/static edits: run `py -3 scripts/vercel_bundle.py` (or equivalent) so `api/template_store.py` and `api/static` stay in sync for Vercel.
4. Nested dirty clone `property-broker-chatbot/property-broker-chatbot/` is **not** the source of truth — edit the outer workspace.

---

## 6. Quick reference — important URLs

| Surface | URL |
|---------|-----|
| Production home | https://property-broker-chatbot-jakkash.vercel.app/ |
| Sell / Rent | https://property-broker-chatbot-jakkash.vercel.app/sell-property |
| Listings | https://property-broker-chatbot-jakkash.vercel.app/properties |
| Chatbot | https://property-broker-chatbot-jakkash.vercel.app/chatbot |
| Admin login | https://property-broker-chatbot-jakkash.vercel.app/admin/login |
| Admin submissions | https://property-broker-chatbot-jakkash.vercel.app/admin/sell-properties |
| Admin inquiries | https://property-broker-chatbot-jakkash.vercel.app/admin/inquiries |

Local default: `http://127.0.0.1:5000` (`py -3 app.py`). Bootstrap admin username historically `sam` (password from env / defaults — rotate in production).

---

## 7. Data model snapshot (CRM-critical)

```text
admins ──┬── properties (owner_admin_id, listing_intent, seller_type, block_wing, unit_number, …)
         │       ├── property_images / property_videos / property_documents
         │       ├── inquiries (inquiry_type: site_visit | general | property)
         │       ├── leads ←── lead_notes
         │       └── saved_properties (session_id)
         ├── owner_submissions (pending|approved|rejected, seller_type, listing_intent, …)
         ├── customer_visits (property_id + property_ids JSON)
         └── activity_logs

testimonials ── review_comments
visitors / visitor_events / search_analytics / area_demand
```

---

*End of Project Context & Architecture Report.*
