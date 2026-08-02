# Project Context: property-broker-chatbot

This file documents the current codebase state for future development and agent onboarding.

## Project purpose and high-level architecture

- Purpose: a property brokerage platform centered on Surat, Gujarat, with:
  - Public discovery and inquiry experience
  - Admin operations panel for inventory, leads, inquiries, reviews, analytics, and employee access
  - Lightweight AI/ML helpers (lead scoring, recommendations, price estimation)
- Architecture style: Flask monolith serving server-rendered HTML templates plus JSON APIs.
- Request flow:
  1. Browser loads server-rendered pages from `routes/public.py` or `routes/admin_portal.py`.
  2. Frontend JS calls `/api/*` endpoints for dynamic data/actions.
  3. Models in `models/*.py` access DB through thin SQL helpers in `database/db.py`.
  4. Service modules in `services/*.py` implement scoring/prediction/OTP/utility logic.
- Data stores:
  - Primary: MySQL (`database/schema.sql`)
  - Optional local fallback: SQLite (`database/sqlite_init.py`, `data/jakkash.db`)

## Tech stack and runtime model

- Backend: Python + Flask (`app.py`)
- Auth/session: `Flask-Login`, session cookies, OTP/TOTP for admin
- Form security: `Flask-WTF` CSRF for template forms
- DB connectivity: `mysql-connector-python`, optional SQLite adapter/fallback
- ML/data libs: `numpy`, `pandas`, `scikit-learn`, `joblib` (optional model files under `ml/models`)
- Frontend: Jinja templates, Bootstrap 5, Bootstrap Icons, vanilla JS, Leaflet + OpenStreetMap
- Runtime model:
  - Single Flask app process
  - HTML pages + REST-like JSON API under `/api`
  - Session-based tracking (`session_id`, `visitor_id`) for analytics and saved properties

## Repo structure map (key directories/files)

```text
property-broker-chatbot/
  app.py                      # app factory, blueprint registration, session bootstrap
  config.py                   # app config, constants, env-driven settings
  extensions.py               # LoginManager + CSRF instances
  requirements.txt
  README.md
  .env.example

  database/
    __init__.py               # DB helper exports
    db.py                     # MySQL/SQLite switching + query helpers
    schema.sql                # canonical MySQL schema + seed inserts
    sqlite_init.py            # SQLite schema bootstrap + seed data

  routes/
    public.py                 # public pages
    auth.py                   # admin login + OTP verification + logout
    api.py                    # JSON API endpoints
    admin_portal.py           # active admin panel routes
    main.py                   # legacy route module (not registered)
    admin.py                  # legacy admin route module (not registered)

  models/
    admin.py                  # admin users, roles/permissions, OTP/TOTP, schema normalization
    property.py               # active property model/query logic
    lead.py
    inquiry.py
    submission.py
    analytics.py
    reviews.py
    property_model.py         # legacy property model
    user.py                   # legacy user model

  services/
    lead_scoring.py
    recommendation.py
    price_prediction.py       # active predictor for current API/admin panel
    mobile_otp.py
    whatsapp.py
    follow_up.py
    chatbot.py                # legacy chatbot service path
    price_predictor.py        # legacy predictor path

  templates/
    public/                   # active public pages
    admin/                    # active admin pages
    *.html                    # legacy template set tied to routes/main.py

  static/
    css/
      jakkash.css             # active public theme
      admin.css               # active admin theme
      style.css               # legacy theme
    js/
      app.js, home.js, listings.js, detail.js, map.js, chatbot.js, reviews.js, about.js
      main.js, search.js, compare.js, emi.js, chat.js   # mostly legacy usage

  ml/
    train_models.py           # current model training script
    train_model.py            # legacy RF training script path
```

## App boot flow (app.py, blueprints, auth/session)

1. `create_app()` creates Flask app and loads `Config`.
2. Bootstraps key directories:
   - uploads root (`uploads/properties`)
   - `ml/models`
   - `static/img`
3. Initializes extensions:
   - `login_manager.init_app(app)`
   - `csrf.init_app(app)`
4. Registers teardown DB close: `app.teardown_appcontext(close_connection)`.
5. Configures user loader: `Admin.get_by_id(int(user_id))`.
6. Registers active blueprints only:
   - `public_bp`
   - `auth_bp`
   - `api_bp`
   - `admin_bp` from `routes/admin_portal.py`
7. Injects company constants via context processor for templates.
8. `before_request` ensures `session_id` and `visitor_id` exist.
9. Adds `/uploads/<path:filename>` route for media serving from `uploads/`.
10. Exempts `api_bp` from CSRF (`csrf.exempt(api_bp)`).
11. App-context startup:
    - `test_connection()`
    - `Admin.ensure_default()` for bootstrap admin behavior (`sam` super-admin identity).

### Auth/session behavior

- Admin auth is session-based with `Flask-Login`.
- Login flow in `routes/auth.py`:
  1. Username/password check
  2. OTP verification page if required (`/admin/verify`)
  3. Finalized login and redirect to admin dashboard
- OTP methods supported:
  - TOTP (Google Authenticator style via `pyotp`)
  - Mobile OTP via Twilio (with optional dev fallback)
- Session keys used in OTP flow:
  - `pending_admin_id`, `pending_admin_next`, `pending_admin_dev_otp`
  - `admin_otp_verified`, `admin_otp_verified_admin_id`

## Database model overview (core tables/entities + key relations)

### Core entities

- `admins`
  - Admin accounts, role, permissions JSON, OTP/TOTP settings, phone verification
- `properties`
  - Main listing inventory with area/type/price/geo/status/media pointers
- `owner_submissions`
  - Public owner-submitted listing records (pending/approved/rejected workflow)
- `inquiries`
  - Contact and inquiry submissions
- `leads`
  - Lead records enriched with engagement signals and scoring
- `lead_notes`
  - Follow-up notes/history for a lead
- `testimonials`, `review_comments`
  - Public testimonials and attached comments

### Analytics/session entities

- `saved_properties` (session-based saved list)
- `property_views` (property view events)
- `visitors` (visitor/session profile)
- `visitor_events` (event stream: page_view/search/call/whatsapp/etc.)
- `search_analytics` (search filters entered)
- `area_demand` (aggregated demand counters)

### Important relationships

- `property_images/property_videos/property_documents.property_id -> properties.id`
- `inquiries.property_id -> properties.id`
- `leads.property_id -> properties.id`
- `leads.inquiry_id -> inquiries.id`
- `lead_notes.lead_id -> leads.id`
- `saved_properties.property_id -> properties.id`
- `property_views.property_id -> properties.id`
- `review_comments.testimonial_id -> testimonials.id`
- `owner_submissions.property_id -> properties.id` (nullable link during review flow)

## Backend modules summary (routes/models/services/utils)

### Routes

- `routes/public.py`
  - Public pages (`/`, `/properties`, `/property/<slug>`, `/map`, `/contact`, etc.)
  - Public property submission flow (`/sell-property` aliases)
  - Visitor/event tracking hooks
- `routes/auth.py`
  - `/admin/login`, `/admin/verify`, `/admin/logout`
  - Safe next-url handling and OTP session lifecycle
- `routes/api.py`
  - Property search/map/similar/nearby/suggestions
  - Inquiry/review/comment/site-visit submission
  - Saved list, recommendations, analytics snippets, chat assistant, price prediction
- `routes/admin_portal.py` (active admin panel)
  - Permissions + role checks
  - Inventory/lead/inquiry/submission/review/analytics/employee operations
  - Owner scoping for non-super-admin users

### Models

- `models/admin.py`
  - Role constants, permission presets, runtime schema alignment, admin CRUD, OTP/TOTP
- `models/property.py`
  - Property CRUD/search/filter/media/nearby/similar/category logic
- `models/lead.py`
  - Lead create-from-inquiry, status updates, notes, score refresh
- `models/submission.py`
  - Owner submission table management + approval/rejection status ops
- `models/analytics.py`
  - Visitor/event/search capture + dashboard/trending aggregations
- `models/reviews.py`
  - Review and comment moderation APIs for admin/public usage

### Services

- `services/lead_scoring.py`
  - Hybrid rule-based + optional model scoring, tier assignment
- `services/recommendation.py`
  - Query-based recommendation helper over property search
- `services/price_prediction.py`
  - Heuristic + optional model blended price estimate
- `services/mobile_otp.py`
  - Twilio send path with controlled fallback behavior
- `services/whatsapp.py`
  - WhatsApp deep-link message generation
- `services/follow_up.py`
  - Marks stale leads urgent

### Utilities

- `utils/helpers.py`
  - Slug generation
  - INR formatting helper
  - Upload storage helpers with extension checks
  - WhatsApp URL helper

## Public panel flows and important pages

### Main public journey

1. Home (`/`)
   - Category overview, testimonials preview, nearby properties (location-enabled)
2. Listings (`/properties`)
   - Drawer filters + list/grid mode + saved action
3. Property detail (`/property/<slug>`)
   - Media gallery, map, inquiry form, site-visit request, WhatsApp/call, save/share
4. Compare (`/compare`) and Saved (`/saved`)
   - Session-based compare/saved workflows
5. AI chatbot (`/ai-chatbot`)
   - Prompt chat + property card responses from `/api/chat`
6. Contact/testimonials/about/services pages for engagement and branding
7. Sell property (`/sell-property`, `/list-property`, `/list-your-property`)
   - Owner submits listing + media
   - Creates `properties` record with `reserved` status and `owner_submissions` row
   - Admin must approve before listing becomes `available`

### Public tracking hooks

- Visitor/session tracking executes for public blueprint requests.
- Property detail views, search usage, save events, call/WhatsApp clicks emit analytics events.

## Admin panel flows (including employee roles/permissions/OTP)

### Authentication and OTP

- Admin login requires username/password.
- If account has OTP requirements, user is redirected to `/admin/verify`.
- Supported verification methods:
  - TOTP code (if configured)
  - Mobile OTP code (SMS or controlled dev fallback)

### Roles and permission model

- Roles in active code:
  - `super_admin`
  - `manager`
  - `executive`
  - `caller`
- Granular permission keys:
  - `manage_properties`
  - `manage_leads`
  - `manage_inquiries`
  - `manage_reviews`
  - `view_analytics`
  - `manage_settings`
  - `manage_users`
  - `manage_submissions`
- Enforcement:
  - `admin_required`, `permission_required`, and `super_admin_required` decorators
  - OTP-verification re-check on sensitive admin routes

### Admin operations flow

- Dashboard (`/admin/`)
  - KPI cards, urgent leads, trending areas, top viewed properties
- Property inventory
  - Add/edit/delete properties
  - Upload images/videos/documents
  - Non-super admins are owner-scoped via `owner_admin_id`
- Submissions
  - Pending owner submissions reviewed at `/admin/submissions`
  - Approve -> property status to `available`, optional lead bootstrap
  - Reject -> property status remains `reserved`
- Leads/inquiries/reviews/analytics
  - Standard operational and moderation screens
- Employee management (`/admin/employees`, super admin only)
  - Create/update/deactivate admins
  - Assign role + permission overrides
  - Configure/regenerate/disable TOTP for employee accounts

### Caller-role constraint

- `caller` role is restricted to a smaller lead workflow and can only move lead status into:
  - `contacted`
  - `interested`
  - `site_visit_scheduled`

## API endpoints overview (major routes and payload expectations)

All API routes are under `/api` and return JSON.

### Property retrieval and discovery

- `GET /api/properties`
  - Query params: `q`, `property_id`, `area`, `location`, `city`, `type`, `bhk`, `min_price`, `max_price`, `min_sq_ft`, `max_sq_ft`, `listing_intent`, `status`, `sort`, `limit`
  - Returns: `{"success": true, "properties": [...]}` serialized records
- `GET /api/properties/map`
  - Returns marker payload for Leaflet map
- `GET /api/properties/<pid>/similar`
  - Returns similar listings based on area/type/price window
- `GET /api/properties/nearby`
  - Required query: `lat`, `lng`; optional `radius_km`, `limit`
- `GET /api/properties/suggest`
  - Query: `q` (min 2 chars), lightweight top suggestions
- `POST /api/properties/smart-search`
  - Body: `{"query": "...", "limit": 12}`
  - Returns parsed query structure + matched properties

### Inquiry and engagement

- `POST /api/inquiry`
  - Required: `name`, `mobile`
  - Optional: `email`, `message`, `property_id`, `source`
  - Side effects: creates inquiry + lead
- `POST /api/visit-request`
  - Required: `name`, `mobile`, `property_id`
  - Optional: `preferred_date`, `message`, `email`
  - Side effects: inquiry + lead
- `POST /api/whatsapp/interest`
  - Body: optional `property_id`, `name`, `mobile`
  - Returns WhatsApp deep link
- `POST /api/event/call`
  - Body: optional `property_id`, `mobile`
  - Records call click signal/event
- `GET|POST|DELETE /api/saved`
  - Session-based saved properties
  - POST/DELETE body expects `property_id`

### Recommendations/AI/analytics

- `GET /api/recommendations`
  - Uses viewed + saved history and inferred preferences
- `POST /api/chat`
  - Body: `{"message": "..."}`
  - Returns assistant text + optional property list + parsed intent hints
- `POST /api/predict-price`
  - Body keys: `area_name`, `bhk`, `sq_ft`, `property_type`
  - Returns estimated value, range, per-sqft, method
- `GET /api/analytics/trending`
  - Returns top areas and demand by property type

### Reviews

- `POST /api/reviews`
  - Required: `name`, `review_text` (or `message`)
- `POST /api/reviews/<review_id>/comments`
  - Required: `name`/`commenter_name`, `comment_text`

## Frontend JS/CSS responsibilities

### Active public JS

- `static/js/app.js`
  - Save property handler, quick inquiry widget behavior, generic utility usage
- `static/js/home.js`
  - Smart search UX, suggestion chips, GPS-based nearby listings polling/tracking
- `static/js/listings.js`
  - Filter drawer lifecycle, API query composition, grid/list rendering
- `static/js/detail.js`
  - Gallery interaction, detail map, inquiry and visit submission, share/call/WhatsApp tracking
- `static/js/map.js`
  - Leaflet initialization and marker rendering from `/api/properties/map`
- `static/js/chatbot.js`
  - `/api/chat` interaction and result card rendering
- `static/js/reviews.js`
  - Review posting and nested comment posting
- `static/js/about.js`
  - Scroll reveal and animated counters

### Active CSS

- `static/css/jakkash.css`
  - Main public design system, responsive layout, cards, filters, chat UI, about page animations
- `static/css/admin.css`
  - Admin command-center theme, sidebar/nav/KPI/table/form styling

### Legacy frontend assets (not part of active route registration)

- `static/css/style.css`, `static/js/main.js`, `static/js/search.js`, `static/js/chat.js`, `static/js/compare.js`, `static/js/emi.js`
- These pair with legacy root templates and legacy `routes/main.py`/`routes/admin.py`.

## Configuration & env vars (non-secret names only)

### Core Flask/runtime

- `FLASK_SECRET_KEY`
- `FLASK_DEBUG`
- `FLASK_RUN_HOST`
- `FLASK_RUN_PORT`
- `FLASK_ENV`

### Database mode and connectivity

- `USE_SQLITE` (`0`/`1`/`auto`)
- `MYSQL_HOST`
- `MYSQL_PORT`
- `MYSQL_USER`
- `MYSQL_PASSWORD`
- `MYSQL_DATABASE`

### Bootstrap/admin identity

- `DEFAULT_ADMIN_PASSWORD` (defaults to `jodika` when not set outside production)

### Company info

- `COMPANY_EMAIL`
- `COMPANY_ADDRESS`
- `COMPANY_WHATSAPP`

### OTP/SMS delivery

- `SMS_PROVIDER`
- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN`
- `TWILIO_FROM_NUMBER`
- `ALLOW_DEV_OTP_FALLBACK`

## Security/auth notes and constraints

- Passwords are stored as hashes (`werkzeug.security`).
- Admin portal uses session auth (`Flask-Login`) with role/permission decorators.
- OTP controls:
  - Password check may require second factor (TOTP/mobile OTP).
  - Super-admin-only routes require stronger checks.
- CSRF:
  - Enabled globally via `Flask-WTF`.
  - Entire API blueprint is CSRF-exempt by design.
- Upload controls:
  - Extension allowlists for images/videos/docs
  - Maximum upload size set via config (`MAX_CONTENT_LENGTH`)
- Cookie/session hardening:
  - `SESSION_COOKIE_HTTPONLY=True`
  - `SESSION_COOKIE_SAMESITE='Lax'`
  - Weekly session lifetime configured

## Current known caveats/technical debt

- Dual codepaths exist:
  - Active app uses `public/auth/api/admin_portal` route set.
  - Legacy route/modules/templates/assets remain in repo and are not registered by `app.py`.
- Legacy assets reference endpoints that do not exist in active API (examples: `/api/compare`, `/api/emi`, `/api/properties/search`, `/api/visits`).
- Schema evolution is partially runtime-driven:
  - `models/admin.py` and `models/submission.py` perform ad-hoc column checks/ALTERs.
  - No formal migration framework is present.
- MySQL seed schema role enum differs from active role model (`admin/agent` vs `super_admin/executive/...`) and is normalized at runtime.
- No automated test suite or lint configuration is present in repo root.
- `static/img/*` assets referenced by templates are expected by UI; verify these files exist in deployment packaging.
- API CSRF exemption is broad; route-level review is recommended for sensitive write endpoints.

## Run/test/check commands

### Setup and run

```bash
copy .env.example .env
py -3 -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

If using MySQL mode:

```bash
mysql -u root -p < database/schema.sql
```

Optional ML model training:

```bash
py -3 ml\train_models.py
```

Run app:

```bash
py -3 app.py
```

### Current test/check reality

- No dedicated unit/integration test suite is currently configured.
- No lint/format config is present at repo root.
- Practical smoke checks:
  - Public pages: `/`, `/properties`, `/property/<slug>`, `/ai-chatbot`
  - Admin auth: `/admin/login` -> OTP verify -> `/admin/`
  - API sanity: `/api/properties`, `/api/properties/map`, `/api/recommendations`

