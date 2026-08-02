# RELEASE_RUNBOOK

This runbook covers the final 48-hour release hardening flow for the MySQL-backed app.

## 1) Startup Steps

1. Open PowerShell in repo root:
   - `cd C:\Users\Omen\property-broker-chatbot`
2. Activate Python environment:
   - `venv\Scripts\activate`
3. Start local MySQL (repo-local datadir):
   - `powershell -ExecutionPolicy Bypass -File .\scripts\start-local-mysql.ps1`
4. Start Flask app:
   - `$env:FLASK_DEBUG='0'`
   - `venv\Scripts\python.exe app.py`
5. Open:
   - Public: `http://127.0.0.1:5000/`
   - Admin login: `http://127.0.0.1:5000/admin/login`

## 2) MySQL Verification Steps

1. Verify MySQL listening port:
   - `Get-NetTCPConnection -LocalPort 3306 -State Listen`
2. Verify configured DB connectivity from app environment:
   - `mysql -h 127.0.0.1 -P 3306 -u root -p -e "SELECT DATABASE(), VERSION();" jakkash_property`
3. Verify critical tables exist:
   - `admins`
   - `properties`
   - `inquiries`
   - `owner_submissions`
   - `seller_profiles`
   - `customer_visits`
   - `activity_logs`

## 3) Required Env Vars (Google / Twilio)

Set these in `.env` before production cutover:

- Core auth/session:
  - `FLASK_SECRET_KEY` (strong random secret)
- Google OAuth (admin login):
  - `GOOGLE_OAUTH_CLIENT_ID`
  - `GOOGLE_OAUTH_CLIENT_SECRET`
  - `GOOGLE_OAUTH_REDIRECT_URI` (recommended explicit production callback)
- SMS / OTP delivery (Twilio):
  - `SMS_PROVIDER=twilio`
  - `TWILIO_ACCOUNT_SID`
  - `TWILIO_AUTH_TOKEN`
  - `TWILIO_FROM_NUMBER`
  - `ALLOW_DEV_OTP_FALLBACK=false` (production)

## 4) Smoke Test Checklist

Run after startup and after any last-minute config change.

### Public Routes

- `GET /` -> 200
- `GET /about` -> 200
- `GET /services` -> 200
- `GET /properties` -> 200
- `GET /contact` -> 200
- `GET /sell-property` -> 200
- `GET /ai-chatbot` -> 200
- `GET /price-ai` -> 200

### Auth / OTP / Forgot Password

- `GET /admin/login` -> 200
- Invalid login `POST /admin/login` -> stays on login with validation flash
- Valid login `POST /admin/login` -> OTP verify flow (`/admin/verify`) or admin dashboard
- `GET /admin/verify` without pending login -> redirects to login
- `GET /admin/forgot-password` -> 200
- Invalid identify `POST /admin/forgot-password` -> validation flash
- `POST /admin/forgot-password/verify` invalid OTP -> validation flash
- Valid OTP in forgot flow -> reaches `/admin/forgot-password/reset`

### Admin Routes (Authenticated + OTP verified)

- `GET /admin/` -> 200
- `GET /admin/sellers` -> 200
- `GET /admin/visits` -> 200
- `GET /admin/activity` -> 200 (super admin)

### Safe POST Validations

All `/api` write requests (`POST`/`PUT`/`PATCH`/`DELETE`) now require a valid CSRF token (`X-CSRFToken` header or form token) tied to the active session.

- `POST /api/inquiry` with missing name/mobile -> 400 JSON
- `POST /api/visit-request` with missing required fields -> 400 JSON
- `POST /api/predict-price` invalid `sq_ft` -> 400 JSON
- `POST /api/chat` missing message -> 400 JSON
- `POST /api/properties/smart-search` empty query -> 400 JSON
- `POST /admin/sellers` missing required fields -> returns with validation flash
- `POST /admin/visits` missing required fields -> returns with validation flash

## 5) Local MySQL Persistence Helper

### No-admin option (recommended): user logon scheduled task

1. Register autostart task:
   - `powershell -ExecutionPolicy Bypass -File .\scripts\register-local-mysql-autostart.ps1`
2. Register and run immediately:
   - `powershell -ExecutionPolicy Bypass -File .\scripts\register-local-mysql-autostart.ps1 -RunNow`
3. Remove autostart task:
   - `powershell -ExecutionPolicy Bypass -File .\scripts\unregister-local-mysql-autostart.ps1`

If task creation is blocked by policy, use an elevated shell and run the admin option below.

### Admin-required option: install as Windows service

Run these in **elevated PowerShell**:

1. Create service:
   - `sc.exe create PropertyBrokerMySQL binPath= "\"C:\Program Files\MySQL\MySQL Server 8.4\bin\mysqld.exe\" --basedir=\"C:\Program Files\MySQL\MySQL Server 8.4\" --datadir=\"C:\Users\Omen\property-broker-chatbot\.mysql84-alt2\" --innodb_undo_directory=\"C:\Users\Omen\property-broker-chatbot\.mysql84-undo\" --port=3306 --bind-address=127.0.0.1" start= auto`
2. Start service:
   - `sc.exe start PropertyBrokerMySQL`
3. Stop/Delete (rollback):
   - `sc.exe stop PropertyBrokerMySQL`
   - `sc.exe delete PropertyBrokerMySQL`

## 6) Rollback Basics

1. Stop app process.
2. Roll app code back to previous known-good commit/tag.
3. Restart app and re-run smoke checklist.
4. If DB rollback is needed:
   - Pre-release backup example:
     - `mysqldump -u root -p jakkash_property > .\backups\pre_release.sql`
   - Restore example:
     - `mysql -u root -p jakkash_property < .\backups\pre_release.sql`
5. If OAuth/Twilio outage occurs, keep login operational by reverting env vars to last known-good values and restarting app.
