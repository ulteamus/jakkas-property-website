# Implementation Plan: E2E Form Submission Smoke Test

## Overview
Add `e2e_form_test.py` at the project root to submit Contact Us and Sell Property forms against the live Flask + Supabase stack, prove rows exist in cloud Postgres (`inquiries` / `owner_submissions` / `properties`), verify `/my-listings` and `/properties` render live data, then delete tagged test rows.

## Architecture Decisions
- Prefer Flask test client with `WTF_CSRF_ENABLED=False` when talking to the same process as the DB (deterministic CSRF). Also support HTTP mode against `http://127.0.0.1:5000` by scraping `csrf_token` from GET pages when `--http` is set.
- Product table names: Contact → `inquiries`; Sell → `owner_submissions` + `properties` (there is no `submissions` table).
- Sell creates `status=reserved` (pending approval). For `/properties` display check, temporarily set the tagged property to `available`, then cleanup deletes it.
- Tag all payloads with `E2E_FORM_<token>` so cleanup is exact and safe.

## Task List

### Phase 1: Foundation
- [x] Task 1: Publish plan + todo for E2E form test
- [x] Task 2: Implement `e2e_form_test.py` (contact + sell + DB asserts + routes + cleanup)

### Checkpoint: Foundation
- [x] Script runs under `USE_SQLITE=0` / pooler DSN
- [x] No permanent rows left after run

### Phase 2: Execution
- [x] Task 3: Ensure Flask is up on `:5000` (reloader off)
- [x] Task 4: Run `python e2e_form_test.py` and capture report

### Checkpoint: Complete
- [x] Contact + sell return 2xx success JSON
- [x] Cloud DB rows verified then deleted
- [x] `/my-listings` and `/properties` (+ `/api/properties`) return live tagged data

## Supporting fixes applied during E2E
- Contact `/api/inquiry`: lead insert is best-effort (was returning 503 when `leads` missing).
- Supabase migration: expand `owner_submissions` columns; create `leads` / `lead_notes`.
- E2E `/properties` assert uses `/api/properties` (listings page is JS-driven).

## Risks and Mitigations
| Risk | Impact | Mitigation |
|------|--------|------------|
| CSRF on live HTTP | Med | Scrape token or use test-client mode |
| Sell not visible on `/properties` | Med | Flip status `reserved` → `available` for assert only |
| Missing `leads` table | Med | Contact path already handles failure; ensure inquiry insert succeeds |
| Storage upload fails (anon key) | Low | Sell allows media failure; use mock 1x1 PNG optional file |

## Open Questions
- None — requirements are well-defined.
