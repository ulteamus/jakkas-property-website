# Implementation Plan: Client Feedback Round 2 (Storage + Sell UX + Admin Sync)

> **Supersedes:** prior plan *Client Feedback (Vercel Live)* / Phases 1–3 (Discover images, empty `/properties`, tab sliders, admin form parity, image delete). Those items are treated as **done or deferred**; this document is the **new scope** from Audio 1–4 feedback. Do not re-implement Phase 1–3 unless a regression is proven.

## Overview

Fix production **image persistence** (upload → remote store → DB link) as a fail-fast priority, then apply **client-authorized** public UX changes (sell step order, expected-price integrity, hide Owner/Contact on public detail, About/responsive polish), then fix **My Listings approval sync**, then admin **Sell Properties table scroll** plus **Property Inventory** area filter + print export.

**Design-lock note:** Standing Jakkash “frontend FINAL” rule is overridden **only** for surfaces listed in this plan. Do not redesign unrelated templates.

**Stack reminder:** Flask + Jinja; edit `templates/**` + `static/**` then `py -3 scripts/vercel_bundle.py`. Media: `services/storage_service.py` (Supabase → Cloudinary → local; local forbidden on Vercel). Public listings: `available|approved|active`; sell creates `reserved` + `owner_submissions`.

## Architecture Decisions

- **Storage first, fail loud:** Prior smoke noted silent upload fail on prod while delete works when an image exists. Treat missing remote URL / empty `property_images` as a hard defect; surface errors to submitter/admin; never swallow storage exceptions into “success with no photos” without a clear warning (already partially present on sell — extend and fix root cause).
- **Canonical media path:** Persist only HTTPS Supabase/Cloudinary URLs in DB on Vercel. Local `properties/...` paths are invalid in production.
- **Sell wizard UX:** Strict step order 1 Listing Intent → 2 Owner → 3 Contact (dynamic by Owner/Broker/Developer) → 4 Property Details → 5 Submit. Intermediate steps use **Next** (no Submit). Preserve existing POST field names.
- **Expected price:** User-entered INR is authoritative. No client/server script may predict, overwrite, or deduct from `price` / `#expectedPriceInput` on sell (or admin property form parity fields). Standalone `/price-predictor` / `/api/predict-price` remain separate tools — do not wire them into sell submit.
- **Public detail privacy:** Remove Owner and Contact **tabs** from public `detail.html`; show Property Details (+ listing intent/price as today) and a single clean brokerage CTA (WhatsApp/Call/Inquiry). No owner PII in public DOM.
- **My Listings status source of truth:** Display status must reflect **effective approval**, not only `owner_submissions.status`. Prefer coalesce: if linked `properties.status` ∈ `{available,approved,active}` → show Approved; if submission rejected → Rejected; else Pending. Also sync submission when admin sets property available via property form.
- **Admin inventory vs sell queue:** Area filter + Print View for **Property Inventory** (`/admin/properties`) — Sell Properties already has area + print; reuse that pattern. Table clip: `.admin-table-wrap { overflow: hidden }` fights horizontal scroll — fix CSS so Actions remain reachable.

## Dependency Graph

```
Prod storage env (bucket + service key + public policies)
    │
    └── save_media / sell + admin upload → property_images.file_path
            │
            └── Visual parity (public cards, My Listings thumbs, admin gallery)

Sell step model (intent → owner → contact → property → submit)
    │
    ├── Expected price lock (no auto-mutate)
    └── Detail privacy (drop Owner/Contact tabs)  [independent after sell UX]

Approval write paths (sell-properties approve OR property_form status)
    │
    └── My Listings display status (+ optional backfill)

Admin CSS overflow + Property Inventory filters/print
    │
    └── Independent of public UX (can follow sync)

About layout + mobile/tablet polish (authorized surfaces only)
```

## Root-cause hypotheses (to verify in Task 1)

| Area | Likely cause | Evidence in codebase |
|------|----------------|----------------------|
| Upload silent fail | Supabase upload fails; Cloudinary missing; local forbidden on Vercel; exception logged but listing still “success” | `storage_service.save_media`; sell catches per-file errors; admin `_upload_media` `except: pass` |
| Images not linked | `add_image` never called when `stored` is None; empty payload / bad MIME | `routes/public.py` sell loop |
| My Listings Pending | Template uses `s.status` only; ignores joined `property_current_status`; property_form can set `available` without `set_submission_status` | `my_listings.html`; `admin_portal.property_form` update path |
| Actions clipped | `.admin-table-wrap { overflow: hidden }` (desktop) | `static/css/admin.css` ~367–372 |
| Inventory no area/print | `properties.html` status chips only; sell_properties already has area+print | Compare templates/routes |

## Task List

### Phase 1: Storage fail-fast (PRIORITY)

- [x] Task 1: Diagnose production storage path (env, bucket, keys, policies, sample upload)
- [x] Task 2: Fix upload → remote store → DB link; fail loud when no remote URL
- [x] Task 3: Stop silent media swallow on admin property form; align warnings with sell

### Checkpoint: Storage
- [x] Prod sell with photos yields HTTPS URLs in `property_images` / submission JSON *(code path verified locally against live Supabase; deploy + human smoke still recommended)*
- [x] Failed upload shows clear user-visible error/warning (not empty gallery with “success” only)
- [ ] Delete still works for newly uploaded remote images *(unchanged delete path; spot-check after deploy)*
- [ ] Human review before UI/admin phases

### Phase 2: Sell flow, price integrity, public privacy

- [x] Task 4: Reorder sell wizard + Next/Submit-only-at-end
- [x] Task 5: Lock expected price (remove any predict/alter/deduct paths on sell + form parity)
- [x] Task 6: Hide Owner & Contact tabs on public property detail; clean brokerage CTA

### Checkpoint: Public sell + detail
- [x] Step order matches spec; Submit only on final step
- [x] Submitted price equals typed value
- [x] Public detail has no Owner/Contact tabs; no seller PII
- [x] `vercel_bundle.py` after template/static edits

### Phase 3: My Listings approval sync

- [x] Task 7: Sync / derive My Listings status from property + submission; backfill on property_form publish

### Checkpoint: Approval sync
- [x] Mobile search shows Approved after admin approval (either approve path) *(code path; human smoke after deploy)*
- [x] Rejected still shows Rejected

### Phase 4: Admin table, inventory filter, print

- [x] Task 8: Horizontal scroll for Sell Properties (and inventory) action columns
- [x] Task 9: Property Inventory location/area filter (e.g. Adajan, Vesu)
- [x] Task 10: Property Inventory Print View for filtered set

### Checkpoint: Admin inventory
- [x] Actions reachable on narrow + desktop widths *(CSS overflow-x:auto on `.admin-table-wrap`; human smoke after deploy)*
- [x] Filter + print match filtered rows

### Phase 5: About + responsive polish

- [x] Task 11: About Us layout improvements (authorized page only)
- [x] Task 12: Mobile + tablet pass on authorized surfaces (sell, detail, about, my-listings, admin tables)

### Checkpoint: Complete
- [x] All acceptance criteria met *(Phase 5 implemented; human deploy smoke still open)*
- [ ] Bundle + deploy smoke on storage + sell + my-listings + admin inventory
- [ ] Ready for human / client review

## Detailed Tasks

## Task 1: Diagnose production storage path

**Description:** Read-only-to-ops diagnosis of why prod uploads silent-fail while delete works when an image exists. Confirm Vercel env (`SUPABASE_URL`, service role key preference order, `SUPABASE_BUCKET`/`STORAGE_BACKEND`), bucket existence/public ACL, and a single controlled upload test (staging or prod admin) logging returned URL vs DB row.

**Acceptance criteria:**
- [x] Written diagnosis: which backend is selected on Vercel and why upload fails (or succeeds)
- [x] Confirmed whether failure is auth, bucket missing, MIME, payload empty, or URL not written to DB

**Verification:**
- [x] Manual: one admin or sell upload attempt with runtime logs inspected
- [x] Compare a known-good remote URL row vs a failed submission’s `images` JSON

**Diagnosis result (2026-09-16):**
- Backend preference on Vercel/local: `STORAGE_BACKEND=supabase`, bucket `property-media`.
- Failure mode: **auth key selection**. Code preferred `SUPABASE_SERVICE_KEY` (`sb_secret_*`) which supabase-py rejects as **Invalid API key**; JWT in `SUPABASE_KEY` uploads successfully (HTTP 200 + public GET 200 + `property_images` row).
- Not MIME/empty payload/missing bucket (bucket exists; upload works once JWT is used).
- Silent success path: sell already warned; admin `_upload_media` was wrapped in `except: pass` (Task 3).

**Dependencies:** None

**Files likely touched:**
- (investigation notes only; may add temporary logging later in Task 2)
- `services/storage_service.py` (read)
- Vercel env / Supabase dashboard (ops)

**Estimated scope:** Small–Medium (investigation; no feature code until Task 2)

---

## Task 2: Fix upload → store → DB link (fail loud)

**Description:** Fix root cause from Task 1 so `save_media` / `save_upload` returns a durable HTTPS URL and sell/admin paths call `add_image` with that URL. On Vercel, never persist local relative paths. When all uploads fail, prefer hard fail or unavoidable clear warning that cannot be missed (JSON + flash + confirm UI).

**Acceptance criteria:**
- [x] Successful upload stores `https://…` in `property_images.file_path` and submission `images`
- [x] Failure raises or returns explicit error; no silent empty gallery on “happy path” success without warning
- [x] Public/admin thumbs resolve for new uploads

**Verification:**
- [ ] Sell with 2 images → My Listings thumbs + admin gallery
- [ ] Force-fail storage (bad bucket name in preview) → user sees error/warning

**Dependencies:** Task 1

**Files likely touched:**
- `services/storage_service.py`
- `routes/public.py` (sell upload loop / response)
- `models/property.py` (`add_image` if needed)
- Possibly `routes/admin_portal.py` `_upload_media`

**Estimated scope:** Medium

---

## Task 3: Admin upload errors not swallowed

**Description:** Property form currently `except: pass` around `_upload_media`, which hides the same storage bug. Flash/log media failures after successful property save; keep property update durable but make media failure visible.

**Acceptance criteria:**
- [x] Admin save with failed images shows flash warning listing failure
- [x] Successful admin images still attach as remote URLs

**Verification:**
- [ ] Admin edit attach photo on prod/preview
- [ ] Logs contain storage exception when forced fail

**Dependencies:** Task 2

**Files likely touched:**
- `routes/admin_portal.py`
- `templates/admin/property_form.html` (optional message display)

**Estimated scope:** Small

---

## Task 4: Sell wizard reorder + Next / Submit-at-end

**Description:** Reorder tabs/panels to: Listing Intent → Owner → Contact (labels/fields already dynamic via seller type) → Property Details. Add Next/Back controls; keep Submit only on final step (or only enabled on final step). Update `sell_property.js` tab activation and validation to validate per-step before Next.

**Acceptance criteria:**
- [x] Strict order matches client audio (1→5)
- [x] Intermediate steps: Next (and Back), not Submit
- [x] Final step: Submit For Selling; POST contract unchanged
- [x] Owner/Broker/Developer still retitle contact fields

**Verification:**
- [ ] Manual walkthrough mobile + desktop
- [ ] Successful submit still creates reserved property + submission

**Dependencies:** Checkpoint Storage preferred (can implement in parallel after Task 2 if needed)

**Files likely touched:**
- `templates/public/sell_property.html`
- `static/js/sell_property.js`
- `static/css/jakkash.css` (step nav only if needed)
- Then `scripts/vercel_bundle.py`

**Estimated scope:** Medium

---

## Task 5: Expected price integrity

**Description:** Audit sell (+ admin property form price field) for any script that predicts, autofills, or deducts expected price. Remove/disable wiring to `/api/predict-price` or ML helpers on these forms. Ensure submitted `price` equals `#expectedPriceInput` value with no client mutation before POST.

**Acceptance criteria:**
- [x] No automatic change to expected price on sell form
- [x] Typed value equals DB `properties.price` / submission `price` after submit

**Verification:**
- [ ] Enter known price → submit → admin/My Listings show same number *(manual)*
- [x] Grep confirm no predict hooks on sell/admin property form JS

**Dependencies:** None (∥ Task 4)

**Files likely touched:**
- `static/js/sell_property.js`
- `static/js/admin_property_form.js` (if any)
- `templates/public/sell_property.html` / `templates/admin/property_form.html` (remove predictor UI if present)

**Estimated scope:** Small

---

## Task 6: Public detail privacy (hide Owner/Contact tabs)

**Description:** On `templates/public/detail.html`, remove Owner and Contact tab buttons/panels. Keep Property Details (and listing intent/price presentation). Provide one clean CTA group to contact the brokerage team (existing WhatsApp/Call/Inquiry — consolidate so it doesn’t feel like seller contact).

**Acceptance criteria:**
- [x] No Owner or Contact tabs in public detail UI
- [x] No owner name/phone/email in public detail markup
- [x] Clear CTA to contact Jakkash team remains

**Verification:**
- [ ] `/property/<slug>` desktop + mobile
- [ ] View-source / a11y tree: no seller PII tabs

**Dependencies:** None (∥ Phase 2)

**Files likely touched:**
- `templates/public/detail.html`
- `static/js/detail.js` (if tab init assumes four tabs)
- CSS as needed
- Bundle

**Estimated scope:** Small

---

## Task 7: My Listings approval state sync

**Description:** Fix out-of-sync Pending when property is live. (1) Template/API: derive badge from `property_current_status` + submission status. (2) When admin `property_form` sets status to available/approved/active for a linked submission, call `set_submission_status(..., "approved")` (and reverse to pending/reserved carefully if demoted). Optional one-shot SQL/script to backfill mismatched rows.

**Acceptance criteria:**
- [x] After admin approval (Sell Properties **or** property status → available), mobile lookup shows Approved
- [x] View link appears when approved + slug present
- [x] Rejected remains Rejected

**Verification:**
- [ ] Approve via sell-properties → My Listings by mobile
- [ ] Set available via property edit on a reserved user submission → My Listings updates
- [ ] Pending reserved still Pending

**Implementation (2026-09-17):**
- `effective_listing_status` / `display_status` on parsed submissions; My Listings badge uses property Status.
- `sync_submission_from_property_status` on admin `property_form` when status changes.

**Dependencies:** None (∥ after Phase 1; independent of sell UX)

**Files likely touched:**
- `templates/public/my_listings.html`
- `routes/public.py` (`my_listings` — attach `display_status`)
- `routes/admin_portal.py` (`property_form` status sync)
- `models/submission.py` if helper needed

**Estimated scope:** Medium

---

## Task 8: Admin table horizontal scroll (actions visible)

**Description:** Fix CSS so Sell Properties (and Property Inventory) action columns are not clipped. Replace/narrow `.admin-table-wrap { overflow: hidden }` so `table-responsive` / `overflow-x: auto` works on desktop as well as the existing mobile media-query rules.

**Acceptance criteria:**
- [x] All action buttons reachable via horizontal scroll without being cut off
- [x] Card border-radius still acceptable (clip content only where intentional)

**Verification:**
- [ ] `/admin/sell-properties` at ~1024px and mobile widths
- [ ] `/admin/properties` same check

**Implementation (2026-09-17):** `.admin-table-wrap` uses `overflow-x: auto` (desktop + mobile); table `min-width: 720px`.

**Dependencies:** None

**Files likely touched:**
- `static/css/admin.css`
- Possibly `templates/admin/sell_properties.html` / `properties.html` wrapper classes
- Bundle

**Estimated scope:** Small

---

## Task 9: Property Inventory area filter

**Description:** Add location/area filter (e.g. Adajan, Vesu) to `/admin/properties`, mirroring Sell Properties area select. Extend `prop_model.search` / route query args; area options from distinct `area_name` (not only `status=available` if inventory needs reserved too — prefer all statuses in admin scope).

**Acceptance criteria:**
- [x] Selecting an area filters inventory list
- [x] “All areas” clears filter
- [x] Works with existing status chips + pagination

**Verification:**
- [ ] Filter Adajan → only matching rows
- [ ] Status=reserved + area combo works

**Implementation (2026-09-17):** `?area=` on `/admin/properties`; options = known Surat list ∪ `areas_list(all_statuses=True)`.

**Dependencies:** None (∥ Task 8)

**Files likely touched:**
- `routes/admin_portal.py` (`properties`)
- `models/property.py` (`search`, `areas_list` variant)
- `templates/admin/properties.html`

**Estimated scope:** Small–Medium

---

## Task 10: Property Inventory print export

**Description:** Add Print View button on Property Inventory that opens a print-friendly template of the **current filtered** set (status + area + page or “all matching” — prefer all matching filtered rows up to a sane cap, document cap in UI). Reuse patterns from `sell_properties_print.html` / `print_sell_properties`.

**Acceptance criteria:**
- [x] Print View respects active filters
- [x] Browser print stylesheet usable for inventory report
- [x] Does not expose needless PII beyond inventory fields already on admin list

**Verification:**
- [ ] Filter area → Print View → rows match
- [ ] Print preview readable

**Implementation (2026-09-17):** `/admin/properties/print` + `properties_print.html`; cap 1000 matching rows.

**Dependencies:** Task 9 (filter query args)

**Files likely touched:**
- `routes/admin_portal.py` (new print route)
- `templates/admin/properties_print.html` (new)
- `templates/admin/properties.html` (button)
- Bundle

**Estimated scope:** Medium

---

## Task 11: About Us layout improvements

**Description:** Client-authorized polish on `templates/public/about.html` (+ related CSS). Improve layout rhythm/alignment without redesigning the whole site. Scope: About page (and homepage `#about` only if the same issue is visible there — prefer About page first).

**Acceptance criteria:**
- [x] About layout improved per client feedback (clearer hierarchy, less cramped sections)
- [x] Desktop + tablet + mobile acceptable

**Verification:**
- [ ] `/about` screenshots at 375 / 768 / 1280

**Implementation (2026-09-17):** Shared `about-page-shell` width across hero/leadership/values/stats; clamp spacing; equal leadership cards with consistent photo crop (`object-position: center 18%`); vision/mission under same shell.

**Dependencies:** Open question on exact visual prefs (else judgment within existing brand)

**Files likely touched:**
- `templates/public/about.html`
- `static/css/jakkash.css` and/or page-scoped styles
- Bundle

**Estimated scope:** Small

---

## Task 12: Mobile + tablet responsiveness pass

**Description:** Rigorous pass across **authorized** surfaces only: sell wizard, public detail, about, my-listings, admin sell-properties + properties tables. Fix overflow, tap targets, tab/step nav, and table scroll regressions introduced by earlier phases.

**Acceptance criteria:**
- [x] No critical horizontal page overflow on 375 / 768
- [x] Sell Next/Submit usable on mobile
- [x] Admin actions reachable (ties to Task 8)

**Verification:**
- [ ] Checklist pass on listed routes
- [ ] Spot-check after bundle

**Implementation (2026-09-17):** Sticky sell step nav + 48px tap targets; `w-sm-auto`; detail CTA 2-col tablet grid; my-listings table horizontal scroll; admin filter/action min-heights on phone/tablet. Bundle via `vercel_bundle.py`.

**Dependencies:** Tasks 4, 6, 8, 11

**Files likely touched:**
- `static/css/jakkash.css`, `static/css/admin.css`
- Possibly small HTML/JS tweaks on authorized templates only

**Estimated scope:** Medium

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Prod Supabase key is anon-only / RLS blocks upload | High | Task 1 verifies service role; document required Vercel secrets before coding workarounds |
| “Silent success” hides incomplete fix | High | Task 2–3 force visible warnings + log correlation IDs |
| Syncing submission on property_form causes false Approvals | Med | Only sync when linked `owner_submissions` exists; map status carefully |
| Inventory print loads too many rows | Med | Cap + message; reuse sell print period patterns |
| Frontend FINAL conflict / scope creep | Med | Touch only authorized surfaces listed above |
| Bundle drift (`api/template_store` stale) | Med | Always run `vercel_bundle.py` after template/static edits |
| Price “AI” was client perception of another page | Low | Task 5 audit; clarify in Open Questions |

## Open Questions — Resolved (Round 2 kickoff)

1. **Storage ops:** Assume Vercel has secrets set; implement **fail-fast logging**. If upload still fails, document exact `vercel env ls` / `vercel env add` commands for the user to verify (no invented secret values). **Diagnosis (Task 1):** Prod has `SUPABASE_SERVICE_KEY`, `SUPABASE_KEY`, `SUPABASE_ANON_KEY`, `SUPABASE_URL`, `SUPABASE_BUCKET`/`SUPABASE_STORAGE_BUCKET`, `STORAGE_BACKEND`. Local/prod prefer `SUPABASE_SERVICE_KEY` (`sb_secret_*`) first — supabase-py Storage rejects it as **Invalid API key**; classic JWT in `SUPABASE_KEY` uploads successfully. Bucket: `property-media`.
2. **Approval path:** Sync from **property Status only** (for Phase 3 / Task 7). Note now; implement later.
3. **Expected price:** Sell form field — **disable scripts altering input** (Phase 2 / Task 5). Note now; implement later.
4. **Inventory print:** **HTML print** (Phase 4 / Task 10). Note now; implement later.
5. **About / responsive:** **Agent judgment** under existing brand (Phase 5). Note now; implement later.
6. **areas_list:** Inventory area filter includes **all statuses** (Phase 4 / Task 9). Note now; implement later.

## Implementation Order (agents)

1. Tasks 1 → 2 → 3 (storage) — **stop for human checkpoint**
2. Tasks 4 ∥ 5 ∥ 6 (sell UX / price / privacy)
3. Task 7 (My Listings sync)
4. Tasks 8 ∥ 9 → 10 (admin scroll / filter / print)
5. Tasks 11 → 12 (About + responsive)

## Parallelization

| Parallel-safe | Sequential |
|---------------|------------|
| Task 5 ∥ Task 6 ∥ Task 4 (after storage checkpoint) | 1 → 2 → 3 |
| Task 8 ∥ Task 9 | 9 → 10 |
| Task 7 ∥ Phase 4 | Bundle before deploy smoke |

## Verification commands (repo)

- Bundle: `py -3 scripts/vercel_bundle.py`
- Prefer existing smoke / e2e scripts if present (`scripts/test_e2e_pipeline.py`) for sell + listings after storage fix
- Manual prod/preview checklist per checkpoint above
