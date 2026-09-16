# Implementation Plan: Client Feedback (Vercel Live)

## Overview

Address client feedback from the live deploy at [jakkas-property-website.vercel.app](https://jakkas-property-website.vercel.app): fix broken Discover / listing media, restore non-empty `/properties` results, make sell/detail tab UX scroll horizontally, update About / co-founder copy+alignment, and bring admin Add/Edit Property into visual/field parity with the public Sell form—including admin-only fields and per-image moderation before go-live.

**Design-lock conflict:** Standing Jakkash rule treats frontend as FINAL for some workstreams. This client feedback **explicitly authorizes** scoped UI changes for About Us styling, co-founder name/alignment, horizontal tab slider (sell + detail), and admin form UI parity. Plan and implement those UI edits; do not broaden into unrelated redesign.

**Stack:** Flask + Jinja (`templates/`, mirrored via `scripts/vercel_bundle.py` → `api/template_store.py` / `api/static` / `public/`), Supabase Postgres, Vercel Python serverless (`api/index.py`), media via `services/storage_service.py` (Supabase → Cloudinary → local). Live admin is `routes/admin_portal.py`.

## Architecture Decisions

- **Edit canonical sources, then bundle:** Change `templates/**` and `static/**` first; run `py -3 scripts/vercel_bundle.py` before deploy so Vercel DictLoader + mirrors stay in sync. Prefer not hand-editing `api/template_store.py`.
- **Static on Vercel:** `.vercelignore` excludes `api/static/` and `static/property-uploads/`. Root `static/` is what `@vercel/static` serves. Property media must be **remote URLs** (Supabase/Cloudinary), never reliance on ephemeral `/tmp` or ignored `property-uploads/`.
- **Listings are JS-first:** `/properties` SSR is thin; `static/js/listings.js` loads `/api/properties`. Empty grid is primarily an API/filter/data problem, not a missing Jinja loop.
- **Default city filter is high-risk:** `templates/public/listings.html` sets `name="city"` to `value="Surat"`, and listings.js always sends non-empty filters → every browse hits `prop_model.search(city="Surat")` (city OR location ILIKE). Fix filter defaults / empty-city semantics before blaming “no data.”
- **Sell submissions stay `status=reserved`:** Public Discover / `/properties` / detail only show `available|approved|active`. Post-submit image visibility belongs on My Listings / admin moderation, not the public feed, until approved.
- **Admin form parity = shared structure, not shared auth:** Rebuild admin property form layout/sections to match sell (chips, sections/tabs, media picker UX) while keeping Status, PDF documents, Listing Type, Seller Type, Creation Source admin-only.
- **Image moderation needs new delete path:** Today admin shows existing gallery as links only; `models/property.py` has `add_image` / `get_media` but **no** delete-media helper or route. Add delete + preview before go-live.
- **Horizontal tabs are new UI:** Sell currently uses stacked headings + wrapping chips (`flex-wrap: wrap`). Detail uses a flat meta list. Client wants tabs: Owner, Contact, Property Details, Listing Intent with smooth horizontal scroll (no awkward wrap).

## Dependency Graph

```
Remote storage health (Supabase/Cloudinary env)
    │
    ├── Discover / listing card media URLs
    │
    ├── Sell upload persistence → My Listings / admin gallery
    │
    └── Admin per-image delete (must not leave orphan local-only paths)

City/filter defaults + public status set
    │
    └── /properties empty results + Discover card count

Sell form section/tab structure + CSS scroll
    │
    ├── Property detail tab slider (same pattern)
    │
    └── Admin form parity (reuse section model; add admin-only strip)

Co-founder name (human input) + About styling prefs
    │
    └── Home + About templates/CSS
```

## Task List

### Phase 1: Media & listings foundations (fail fast)

- [x] Task 1: Diagnose and fix Discover “JAKKASH Spaces” broken images
- [x] Task 2: Fix sell-upload persistence + post-submit image visibility
- [x] Task 3: Fix empty `/properties` (city default + API search)

### Checkpoint: Public listings & media
- [x] Homepage Discover cards show real images or intentional placeholder
- [x] Sell with photos stores remote URLs; thumbs visible where expected post-submit
- [x] `/properties` with no user filters shows available listings (not forced empty by `city=Surat`)
- [ ] Review with human before UI polish / admin parity

### Phase 2: Public UI (client-authorized)

- [x] Task 4: About Us homepage visual adjustments
- [x] Task 5: Co-founder name placeholder `[INSERT_NAME_HERE]` + profile image alignment
- [x] Task 6: Horizontal tab slider on Sell Property form
- [x] Task 7: Horizontal tab slider on property details

### Checkpoint: Public UI
- [ ] About / leadership look acceptable on mobile + desktop
- [ ] Sell + detail tabs scroll horizontally without wrap jank
- [x] `vercel_bundle.py` run after template/static edits

### Phase 3: Admin parity & moderation

- [x] Task 8: Admin Add/Edit form layout/fields match Sell (user-visible parity)
- [x] Task 9: Admin-only field strip (Status, PDF, Listing Type, Seller Type, Creation Source)
- [x] Task 10: Image moderation — preview all uploads + per-image delete before go-live

### Checkpoint: Complete
- [ ] Admin create/edit mirrors sell UX; admin-only controls still present
- [ ] Admin can remove bad images before setting status available
- [ ] Smoke on production/preview: Discover, `/properties`, sell, detail tabs, admin form
- [ ] Ready for client review

---

## Task 1: Diagnose and fix Discover “JAKKASH Spaces” broken images

**Description:** Homepage Discover section (`templates/public/home.html` → `#jvDiscoverGrid`) renders SSR cards via `render_listing_media` and/or JS via `static/js/home.js` + `listing-media.js`. Broken images on Vercel typically mean DB paths pointing at `/uploads/...` or ignored `static/property-uploads/`, failed remote storage, or `media_url` / `primary_image_url` mismatch. Fix URL resolution and ensure cards fall back cleanly to `/static/img/default-property.jpg` (file exists under root `static/img/`).

**Acceptance criteria:**
- [ ] Discover cards on live/preview show working image src (HTTPS remote or valid static fallback)
- [ ] No systematic 404s for card images when `primary_image` / `property_images` exist
- [ ] Missing media still shows default placeholder, not a broken icon

**Verification:**
- [ ] Browser: open `/` → Discover section → Network tab image requests succeed or hit default
- [ ] Flask/test client or curl: `/api/properties?sort=newest&limit=9` returns `primary_image_url` that starts with `http` or `/static/`
- [ ] Confirm `.vercelignore` is not required for the serving path used

**Dependencies:** None (high-risk; first)

**Files likely touched:**
- `models/property.py` (`public_image_url`, serialization)
- `routes/public.py` (`_attach_listing_media`, home)
- `static/js/listing-media.js` / `static/js/home.js`
- `templates/public/_listing_media.html` (only if macro URL path wrong)

**Estimated scope:** M (3–5 files)

---

## Task 2: Fix sell-upload persistence + post-submit image visibility

**Description:** Sell POST (`routes/public.py`) creates `status=reserved`, uploads via `save_upload` → `storage_service`, and swallows media exceptions. On Vercel, local fallback is ephemeral. Client report “images not displaying after submission” may mean (a) upload never persisted remotely, (b) My Listings shows no thumbs (`templates/public/my_listings.html` is text-only), and/or (c) detail/public feed correctly hides reserved. Fix remote upload reliability, surface upload failures to the user when all images fail, and show thumbnails on My Listings / success path for the submitter.

**Acceptance criteria:**
- [ ] Successful sell with images stores absolute remote URLs in `property_images` / `owner_submissions.images_json`
- [ ] Submitter sees uploaded image previews on My Listings (or dedicated success view) without needing public approval
- [ ] If storage backend fails for all files, user gets a clear error/warning (not silent success with empty media)

**Verification:**
- [ ] Submit sell form with 1–2 images on preview/prod; inspect DB paths start with `https://`
- [ ] Open `/my-listings` with same mobile/session → thumbs render
- [ ] Confirm `STORAGE_BACKEND` / Supabase env on Vercel (no secrets in docs)

**Dependencies:** Task 1 (shared URL/storage understanding)

**Files likely touched:**
- `routes/public.py` (sell + my_listings context)
- `services/storage_service.py` / `utils/helpers.py`
- `templates/public/my_listings.html`
- `static/js/sell_property.js` (error messaging)

**Estimated scope:** M

---

## Task 3: Fix empty `/properties` (city default + API search)

**Description:** `listings.js` always sends `city` when the filter input is non-empty; HTML defaults city to `"Surat"`. Combined with sparse rows, blank/null `city` columns, or non-matching values, `/api/properties?city=Surat` can return 0 while “View all properties” feels broken. Align defaults: empty city means “all cities,” keep optional Surat hint as placeholder not value; verify `prop_model.search` city/location ILIKE and public status set; ensure reset/browse-all clears city.

**Acceptance criteria:**
- [ ] Loading `/properties` with no intentional filters returns all publicly available listings (status in `available|approved|active`)
- [ ] Choosing city Surat still filters correctly when user intends it
- [ ] Empty state only when DB truly has zero public rows

**Verification:**
- [ ] Browser: `/properties` → resultsCount > 0 when DB has available rows
- [ ] Network: first `/api/properties` call does **not** force `city=Surat` unless user set it
- [ ] Compare with `/api/properties?sort=newest&limit=120` (no city) vs `?city=Surat`

**Dependencies:** None (can parallel Task 1 after storage sanity)

**Files likely touched:**
- `templates/public/listings.html` (city input default)
- `static/js/listings.js`
- `models/property.py` (`search` city/location) — only if still wrong after UI default fix
- `routes/api.py` — only if API mishandles empty city

**Estimated scope:** S–M

---

## Task 4: About Us homepage visual adjustments

**Description:** Client asked for minor About Us styling on the homepage (`#about` in `home.html`, styles in `jakkash.css`: `.jv-about-split`, leadership). Apply restrained spacing/typography/alignment tweaks only—no full redesign. Exact visual preferences are an open question; start from current layout and tighten inconsistency vs About page.

**Acceptance criteria:**
- [ ] Homepage About block looks polished and consistent on mobile + desktop
- [ ] No unrelated homepage sections restyled
- [ ] Changes limited to About/leadership-related CSS/markup

**Verification:**
- [ ] Browser screenshot `/#about` mobile + desktop
- [ ] Compare with `/about` for consistency if shared classes

**Dependencies:** None (UI; can follow Phase 1 checkpoint)

**Files likely touched:**
- `templates/public/home.html`
- `static/css/jakkash.css`
- optionally `templates/public/about.html` if shared classes

**Estimated scope:** S

---

## Task 5: Co-founder name + profile image alignment

**Description:** Replace placeholder name `JAKKASH Leadership` with the real second co-founder name on home + about (+ `api/template_store` via bundle). Fix co-founder photo alignment/spacing relative to founder card (`.founder-photo`, `.leadership-card`). Asset exists at `static/images/team/co-founder.jpeg` (and `.jpg` fallback).

**Acceptance criteria:**
- [ ] Co-founder displays the agreed real name (not placeholder)
- [ ] Photo alignment/spacing matches founder card visually
- [ ] Home and About stay in sync

**Verification:**
- [ ] Browser `/` and `/about` leadership rows
- [ ] Image loads; no layout jump vs founder column

**Dependencies:** Open question — exact co-founder name (and optional quote/bio) from client

**Files likely touched:**
- `templates/public/home.html`
- `templates/public/about.html`
- `static/css/jakkash.css`

**Estimated scope:** S

---

## Task 6: Horizontal tab slider on Sell Property form

**Description:** Refactor sell form into tabbed sections: Owner, Contact, Property Details, Listing Intent (map existing fields into those groups; Amenities/Media can sit under Property Details or a following panel). Replace wrapping chip rows that cause awkward wrap with a horizontal scroll tab bar (`overflow-x: auto`, nowrap, snap optional). Keep existing field names/POST contract so `routes/public.py` sell handler stays stable.

**Acceptance criteria:**
- [ ] Tabs listed: Owner, Contact, Property Details, Listing Intent
- [ ] Tab bar scrolls horizontally on narrow viewports; labels do not wrap awkwardly
- [ ] All mandatory fields still submit; validation still works
- [ ] Chip groups inside panels may still wrap where needed; tab labels do not

**Verification:**
- [ ] Browser mobile width: drag/swipe tab bar
- [ ] Submit valid sell payload (test client or manual)
- [ ] Keyboard: tabs reachable / focus visible

**Dependencies:** None for structure; better after Task 2 if testing full sell flow

**Files likely touched:**
- `templates/public/sell_property.html`
- `static/js/sell_property.js`
- `static/css/jakkash.css` (and `mobile.css` if needed)

**Estimated scope:** M

---

## Task 7: Horizontal tab slider on property details

**Description:** Apply the same horizontal tab pattern on property detail for Owner, Contact, Property Details, Listing Intent. Detail currently mixes gallery + flat meta + inquiry panels; introduce a tabbed content region for those four info groups without removing CTA buttons (WhatsApp/Call/Inquiry). Owner/Contact may be limited by public PII stripping (`to_dict(public=True)`)—show only what product already allows publicly, or “contact broker” CTAs where owner fields are stripped.

**Acceptance criteria:**
- [ ] Detail page has matching horizontal tab slider UX
- [ ] Public PII rules respected (no leaking stripped owner fields)
- [ ] Gallery/CTAs remain usable

**Verification:**
- [ ] Browser `/property/<slug>` mobile + desktop
- [ ] Confirm no new owner PII in HTML source vs current public rules

**Dependencies:** Task 6 (reuse CSS/JS tab pattern)

**Files likely touched:**
- `templates/public/detail.html`
- `static/css/jakkash.css`
- small JS if tabs need behavior (new or shared module)

**Estimated scope:** M

---

## Task 8: Admin Add/Edit form layout/fields match Sell (user-visible parity)

**Description:** Rebuild `templates/admin/property_form.html` (served by `routes/admin_portal.py` `property_form`) so user-facing layout/fields/design match the Sell form: same sections/tabs, chip-style intent/type/seller controls where applicable, amenities, media picker via `media_file_manager.js`. Preserve admin POST handling (`_form_property`, `_upload_media`).

**Acceptance criteria:**
- [ ] Side-by-side, admin form mirrors sell structure for shared fields
- [ ] Create + edit both work; existing property values hydrate correctly
- [ ] Admin CSS does not break admin shell (`admin/base.html`)

**Verification:**
- [ ] Login admin → Add Property / Edit Property vs `/sell-property`
- [ ] Save new + edit existing property successfully

**Dependencies:** Task 6 (sell tab structure becomes the parity target)

**Files likely touched:**
- `templates/admin/property_form.html`
- `static/css/admin.css`
- `routes/admin_portal.py` (only if field name mapping needed)
- optional small admin JS

**Estimated scope:** M (split further if markup balloons)

---

## Task 9: Admin-only field strip while keeping user UI

**Description:** On the parity admin form, keep a clearly separated admin-only group: Status, Document Upload (PDF), Listing Type (Sell/Rent), Seller Type (Owner/Broker[/Developer if already supported]), Creation Source. These must not appear on the public sell form. Wire documents through existing `_upload_media` / `add_document` paths.

**Acceptance criteria:**
- [ ] Admin-only fields visible and editable only in admin
- [ ] Public sell form unchanged regarding these fields
- [ ] PDF upload persists and lists under documents

**Verification:**
- [ ] Admin save with each admin-only field set; reload edit form shows values
- [ ] Public `/sell-property` has no Status / Creation Source / admin PDF controls

**Dependencies:** Task 8

**Files likely touched:**
- `templates/admin/property_form.html`
- `routes/admin_portal.py` (`_form_property`, `_upload_media`)
- `models/property.py` (if document helpers need extension)

**Estimated scope:** S–M

---

## Task 10: Image moderation — preview all uploads + per-image delete before go-live

**Description:** Admin must preview **all** user-uploaded images for a property and remove individual images before setting status to available. Implement `delete_image` (and optional storage object delete best-effort) in the property model, an authenticated admin route, and UI controls on the existing gallery (not view-only links). After deletes, refresh `primary_image` if the primary was removed.

**Acceptance criteria:**
- [ ] Admin sees thumbnail grid of all images for the property
- [ ] Per-image Remove deletes DB row (and best-effort remote object)
- [ ] Primary image pointer updated if needed
- [ ] Cannot go live with removed images still showing on public cards

**Verification:**
- [ ] Admin edit: remove one of N images → reload → gone
- [ ] Approve/set available → public card/detail omit deleted image
- [ ] Unauthorized POST to delete endpoint returns 401/403

**Dependencies:** Tasks 2 and 8/9 (media must be viewable; form hosts UI)

**Files likely touched:**
- `models/property.py` (delete helpers)
- `routes/admin_portal.py` (delete route)
- `templates/admin/property_form.html`
- optionally `services/storage_service.py` (remote delete)

**Estimated scope:** M

---

## Parallelization Opportunities

| Parallel-safe | Sequential |
|---------------|------------|
| Task 3 (listings filter) ∥ Task 1 (Discover media) after storage env check | Task 6 → Task 7 → Task 8 → Task 9 |
| Task 4 (About CSS) ∥ Task 5 (co-founder) once name known | Task 2 before relying on admin moderation demos |
| Task 10 after Task 2 storage paths known | Bundle + deploy after each UI phase |

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Vercel ephemeral FS / ignored `property-uploads` | High — broken images everywhere | Require Supabase/Cloudinary; store absolute URLs; never ship media only under ignored paths |
| Default `city=Surat` empties listings | High — “0 properties” | Clear default; treat empty as no city filter; verify API |
| Silent sell media `except: pass` | High — submit “works” without images | Fail loudly when images were attached but none stored |
| Admin↔Sell parity scope creep | Med — XL form rewrite | Parity = layout/fields/tabs only; reuse CSS patterns from Task 6 |
| Public detail Owner/Contact tabs vs PII strip | Med — empty tabs or leaks | Tab content = public-safe fields + CTAs only |
| Design-lock vs client UI asks | Med — agent hesitation | This plan documents explicit authorization for listed UI items only |
| Dual template/static mirrors drift | Med — local OK, Vercel stale | Always run `vercel_bundle.py` after template/static edits |
| No media delete today | Med — moderation blocked | Task 10 adds model + route + UI |

## Open Questions (RESOLVED)

1. **Co-founder name:** Still literal placeholder `[INSERT CO-FOUNDER NAME]` (user forgot real name). Role: Co-Founder. Agent judgment for bio/quote OK when unblocked. **Task 5 BLOCKED** until real name supplied.
2. **About Us styling:** Agent judgment for light polish against current brand CSS (Phase 2 Task 4).
3. **Post-submit image surface:** BOTH My Listings **and** submission confirmation show thumbs.
4. **Detail Owner/Contact:** Public = Call/WhatsApp CTAs only (no owner PII); admin = full owner details.
5. **Seller Type:** Keep Developer + Owner + Broker.
6. **Listing Intent + Listing Type:** YES — dual-write both.

## Out of Scope

- Unrelated homepage redesign, chatbot, map, ML price predictor
- Changing admin credentials or documenting secrets
- Broad unlock of all frontend beyond the listed client items
- Migrating historical local-only upload files unless needed for Discover fix (call out as follow-up data repair if many rows still point at `/uploads/`)
