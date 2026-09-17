# Todo: Client Feedback Round 2 (Storage + Sell UX + Admin Sync)

> Source plan: `C:\Users\asw\jakkas-property-website\tasks\plan.md`  
> **Supersedes** prior *Client Feedback (Vercel Live)* todo (Phases 1–3 marked complete). New scope only.  
> Frontend FINAL overridden **only** for: sell wizard, detail privacy tabs, About layout, responsive polish on authorized surfaces, admin table/inventory UI.

## Phase 1 — Storage fail-fast (PRIORITY)

- [x] **Task 1 (S–M):** Diagnose prod storage (env, bucket, keys, policies, sample upload)
  - AC: written root cause; know which backend Vercel selects and why upload fails/succeeds
  - Verify: one controlled upload + logs; compare DB URL vs failure case
  - Files: `services/storage_service.py` (read), Vercel/Supabase ops
  - Deps: none
  - **Done:** Root cause = `SUPABASE_SERVICE_KEY` (`sb_secret_*`) preferred over working JWT `SUPABASE_KEY` → Invalid API key. Backend=`supabase`, bucket=`property-media`.

- [x] **Task 2 (M):** Fix upload → remote store → DB link; fail loud
  - AC: HTTPS URLs in `property_images` + submission; clear error/warning when uploads fail
  - Verify: sell 2 photos → thumbs; forced fail → visible warning
  - Files: `services/storage_service.py`, `routes/public.py`, maybe `models/property.py`, `routes/admin_portal.py`
  - Deps: Task 1
  - **Done:** Prefer JWT keys for Storage; retry on auth fail; log provider/status/reason; reject non-remote on Vercel; sell warning includes failure detail.

- [x] **Task 3 (S):** Admin `_upload_media` not silent `except: pass`
  - AC: flash warning on media failure; success still attaches remote URLs
  - Verify: admin edit attach photo; forced fail shows flash
  - Files: `routes/admin_portal.py`, maybe `property_form.html`
  - Deps: Task 2
  - **Done:** `_upload_media` returns attempted/uploaded/errors; `_flash_media_result`; API upload surfaces exceptions.

### Checkpoint — Storage
- [x] Prod/preview: photos persist as remote URLs *(local e2e against live Supabase OK; deploy for prod smoke)*
- [x] Failures visible (not silent empty gallery)
- [ ] Delete still works for new remote images *(spot-check after deploy)*
- [ ] **Human review before Phase 2**

## Phase 2 — Sell flow, price, public privacy

- [x] **Task 4 (M):** Sell wizard order + Next / Submit-only-at-end
  - AC: 1 Intent → 2 Owner → 3 Contact (dynamic) → 4 Property → Submit only at end; Next on earlier steps
  - Verify: mobile+desktop walkthrough; POST still creates reserved + submission
  - Files: `templates/public/sell_property.html`, `static/js/sell_property.js`, maybe CSS → `vercel_bundle.py`
  - Deps: prefer after Storage checkpoint
  - **Done:** Strict order Intent→Owner→Contact→Property; Next/Back; Submit only on final step; contact labels retitle by Owner/Broker/Developer.

- [x] **Task 5 (S):** Expected price lock (no predict/alter/deduct)
  - AC: typed INR == stored price; no AI/predict hooks on sell (or admin form price field)
  - Verify: known price round-trip; grep sell/admin form JS
  - Files: `static/js/sell_property.js`, maybe `admin_property_form.js` / templates
  - Deps: none (∥ Task 4)
  - **Done:** No predict hooks on sell/admin form; user-price lock + exact `price` on POST; helper text on sell + admin property form.

- [x] **Task 6 (S):** Public detail — hide Owner & Contact tabs; clean team CTA
  - AC: no Owner/Contact tabs; no seller PII; brokerage CTA remains
  - Verify: `/property/<slug>` + view-source
  - Files: `templates/public/detail.html`, `static/js/detail.js`, CSS → bundle
  - Deps: none (∥ Task 4/5)
  - **Done:** Owner/Contact tabs removed; Property Details + Listing Intent remain; single team CTA (WhatsApp/Call/Inquiry/Visit/Share).

### Checkpoint — Public sell + detail
- [x] Step order + Submit gating OK
- [x] Price unchanged by scripts
- [x] Privacy tabs gone
- [x] Bundle run after template/static edits *(python scripts/vercel_bundle.py)*

## Phase 3 — My Listings approval sync

- [x] **Task 7 (M):** Derive/sync approval status (submission ↔ property)
  - AC: mobile search shows Approved after admin approve **or** property→available; Rejected unchanged
  - Verify: both approve paths; pending reserved still Pending
  - Files: `templates/public/my_listings.html`, `routes/public.py`, `routes/admin_portal.py`, maybe `models/submission.py`
  - Deps: none (∥ Phase 4 OK)
  - **Done:** Badge uses `display_status` from `properties.status` (available/approved/active→Approved, sold/rented labels, reserved→Pending; rejected submission stays Rejected). `property_form` status change syncs linked `owner_submissions` via `sync_submission_from_property_status`.

### Checkpoint — Approval sync
- [x] My Listings matches live property state
- [x] View link when approved + slug
  - *(Human smoke still recommended: Sell Properties approve + property_form → available, then mobile search)*

## Phase 4 — Admin table scroll, inventory filter, print

- [x] **Task 8 (S):** Horizontal scroll — actions not clipped
  - AC: Sell Properties (+ inventory) Actions reachable; fix `.admin-table-wrap { overflow: hidden }`
  - Verify: `/admin/sell-properties` + `/admin/properties` at 1024 + mobile
  - Files: `static/css/admin.css`, maybe table wrappers → bundle
  - Deps: none
  - **Done:** `.admin-table-wrap` → `overflow-x: auto`; table min-width 720px (desktop + mobile).

- [x] **Task 9 (S–M):** Property Inventory area filter (Adajan, Vesu, …)
  - AC: area select filters list; works with status chips + pagination
  - Verify: filter combo reserved + area
  - Files: `routes/admin_portal.py`, `models/property.py`, `templates/admin/properties.html`
  - Deps: none (∥ Task 8)
  - **Done:** Area select on inventory; `areas_list(all_statuses=True)` + known Surat options; status chips preserve area.

- [x] **Task 10 (M):** Property Inventory Print View (filtered)
  - AC: print respects filters; readable print layout (cap documented if any)
  - Verify: filter → print rows match
  - Files: `routes/admin_portal.py`, new `templates/admin/properties_print.html`, `properties.html` button → bundle
  - Deps: Task 9
  - **Done:** Print View button → `/admin/properties/print` HTML report of filtered set (cap 1000).

### Checkpoint — Admin inventory
- [x] Actions scrollable
- [x] Area filter + print OK
  - *(Human smoke: 1024px scroll, Adajan filter, Print View match)*

## Phase 5 — About + responsive polish

- [ ] **Task 11 (S):** About Us layout improvements
  - AC: clearer layout on `/about`; brand-consistent; 375/768/1280 OK
  - Verify: screenshots
  - Files: `templates/public/about.html`, CSS → bundle
  - Deps: open Q on exact prefs (else judgment)

- [ ] **Task 12 (M):** Mobile + tablet pass (authorized surfaces only)
  - AC: no critical overflow; sell Next/Submit usable; admin actions reachable
  - Verify: sell, detail, about, my-listings, admin tables at 375/768
  - Files: `jakkash.css`, `admin.css`, small authorized template tweaks
  - Deps: Tasks 4, 6, 8, 11

### Checkpoint — Complete
- [ ] All ACs met
- [ ] Bundle + deploy smoke: storage, sell, my-listings, admin inventory
- [ ] Ready for client review

## Open questions — answered (do not block Phase 1)

- [x] Storage: assume Vercel secrets present; fail-fast logging; document `vercel env` CLI if misconfigured (no invented secrets). Root cause: `SUPABASE_SERVICE_KEY` (`sb_secret_*`) preferred over working JWT `SUPABASE_KEY` → Invalid API key
- [x] Approval sync: **property Status only** (Phase 3 later)
- [x] Expected price: sell form — **disable scripts altering input** (Phase 2 later)
- [x] Print: **HTML print** (Phase 4 later)
- [x] About/responsive: **agent judgment** (Phase 5 later)
- [x] Area filter: **all statuses** (Phase 4 later)

## Vercel env check (if storage still fails after deploy)

List names only (no values printed by CLI for secrets):

```bash
vercel env ls
```

Confirm these exist for **Production** (and Preview if used): `SUPABASE_URL`, `SUPABASE_KEY` (or `SUPABASE_SERVICE_ROLE_KEY` — classic JWT `eyJ…` service role), `SUPABASE_BUCKET` or `SUPABASE_STORAGE_BUCKET` (e.g. `property-media`), `STORAGE_BACKEND=supabase`. Optional fallback: Cloudinary trio / `CLOUDINARY_URL`.

Add or replace a missing var (CLI prompts for value — do not paste secrets into chat/docs):

```bash
vercel env add SUPABASE_KEY production
vercel env add SUPABASE_URL production
vercel env add SUPABASE_BUCKET production
vercel env add STORAGE_BACKEND production
```

Pull locally to inspect names (gitignored): `vercel env pull .env.vercel.local --environment=production`

If `SUPABASE_SERVICE_KEY` is a new `sb_secret_*` key that Storage rejects, either remove it from Vercel or set a valid JWT as `SUPABASE_KEY` / `SUPABASE_SERVICE_ROLE_KEY` (app prefers JWT for Storage).
