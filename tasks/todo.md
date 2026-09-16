# Todo: Client Feedback (Vercel Live)

> Source plan: `C:\Users\asw\jakkas-property-website\tasks\plan.md`  
> Constraint: standing frontend FINAL rule is overridden **only** for client-authorized UI items (About, co-founder, tab slider, admin form parity).

## Phase 1 — Media & listings foundations

- [x] **Task 1 (M):** Fix Discover “JAKKASH Spaces” broken images (URL resolution / remote storage / fallback)
  - AC: cards show remote or `/static/img/default-property.jpg`; no systematic 404s
    - Verify: `/` Discover Network tab; `/api/properties?sort=newest&limit=9`
  - Files: `models/property.py`, `routes/public.py`, `static/js/listing-media.js`, `static/js/home.js`, `_listing_media.html`
  - Deps: none

- [x] **Task 2 (M):** Sell upload persistence + post-submit image visibility
  - AC: remote HTTPS paths stored; My Listings (or success) shows thumbs; warn if all uploads fail
  - Verify: sell with images → DB URLs → `/my-listings` thumbs
  - Files: `routes/public.py`, `services/storage_service.py`, `templates/public/my_listings.html`, `static/js/sell_property.js`
  - Deps: Task 1

- [x] **Task 3 (S–M):** Fix empty `/properties` (remove forced `city=Surat` default; confirm search)
  - AC: unfiltered browse shows public listings; Surat filter still works when chosen
  - Verify: `/properties` first API call; compare with/without `city`
  - Files: `templates/public/listings.html`, `static/js/listings.js`, maybe `models/property.py` / `routes/api.py`
  - Deps: none (∥ Task 1)

### Checkpoint — Public listings & media
- [x] Discover images OK
- [x] Sell media persists + visible to submitter
- [x] `/properties` not empty for real available rows
- [ ] Human review before Phase 2

## Phase 2 — Public UI (client-authorized)

- [x] **Task 4 (S):** About Us homepage minor styling
  - AC: polished `#about` only; mobile + desktop
  - Verify: `/#about` screenshots
  - Files: `templates/public/home.html`, `static/css/jakkash.css`
  - Deps: open Q on exact prefs (else judgment)

- [x] **Task 5 (S):** Co-founder placeholder name + photo alignment
  - AC: no “JAKKASH Leadership” placeholder; uses `[INSERT_NAME_HERE]`; alignment matches founder
  - Verify: `/` and `/about`
  - Files: `home.html`, `about.html`, `jakkash.css`
  - Deps: user will replace `[INSERT_NAME_HERE]` in HTML later

- [x] **Task 6 (M):** Horizontal tab slider on Sell form (Owner, Contact, Property Details, Listing Intent)
  - AC: horizontal scroll tabs; no awkward tab wrap; POST contract unchanged
  - Verify: mobile tab scroll + successful submit
  - Files: `templates/public/sell_property.html`, `static/js/sell_property.js`, `static/css/jakkash.css`
  - Deps: none (better after Task 2 for E2E)

- [x] **Task 7 (M):** Horizontal tab slider on property details (same four tabs; respect PII)
  - AC: matching UX; no new public PII leaks
  - Verify: `/property/<slug>` mobile + desktop; view-source PII check
  - Files: `templates/public/detail.html`, CSS (+ small JS if needed)
  - Deps: Task 6

### Checkpoint — Public UI
- [ ] About + co-founder accepted
- [ ] Sell + detail tabs OK
- [x] Run `py -3 scripts/vercel_bundle.py` after template/static edits

## Phase 3 — Admin parity & moderation

- [x] **Task 8 (M):** Admin Add/Edit Property form matches Sell layout/fields/design
  - AC: visual/field parity for shared fields; create + edit work
  - Verify: admin form vs `/sell-property` side-by-side
  - Files: `templates/admin/property_form.html`, `static/css/admin.css`, maybe `routes/admin_portal.py`
  - Deps: Task 6

- [x] **Task 9 (S–M):** Admin-only strip — Status, PDF docs, Listing Type, Seller Type, Creation Source
  - AC: present only in admin; PDF persists; sell form stays clean
  - Verify: admin save/reload; sell page has no admin-only controls
  - Files: `property_form.html`, `admin_portal.py`
  - Deps: Task 8

- [x] **Task 10 (M):** Image moderation — preview all + per-image delete before go-live
  - AC: thumbnail grid; delete updates DB (+ best-effort remote); primary_image corrected
  - Verify: remove image → public cards omit it after approve
  - Files: `models/property.py`, `routes/admin_portal.py`, `templates/admin/property_form.html`, maybe `storage_service.py`
  - Deps: Tasks 2, 8/9

### Checkpoint — Complete
- [x] All 10 tasks done
- [ ] Bundle + preview/prod smoke: Discover, `/properties`, sell, detail tabs, admin form + delete image
- [ ] Client review ready

## Open questions (RESOLVED)
- [x] Co-founder name: placeholder is exact string `[INSERT_NAME_HERE]` (user will edit HTML later). Role: Co-Founder. Agent judgment used for bio/quote.
- [x] About Us: agent judgment for light polish (Phase 2).
- [x] Post-submit thumbs: BOTH My Listings AND submission confirmation.
- [x] Detail Owner/Contact: public = Call/WhatsApp CTAs only (no owner PII); admin = full owner details.
- [x] Seller Type: keep Developer + Owner + Broker.
- [x] Dual-write Listing Intent AND Listing Type: YES.

## Phase 2 blockers
- [x] **Task 5 unblocked** — using `[INSERT_NAME_HERE]` until real name is pasted in templates

## Reminder before each deploy
- [x] Edit `templates/` + `static/` (canonical) — Phase 1 + Phase 2 + Phase 3 done
- [x] `py -3 scripts/vercel_bundle.py` — ran after Phase 1; re-run after Phase 2; re-run after Phase 3
- [ ] Confirm Vercel storage env (no secrets in plan/todo) — deploy still needed for live verify of sell uploads
