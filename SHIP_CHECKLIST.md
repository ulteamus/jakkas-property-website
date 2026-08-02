# SHIP CHECKLIST

Repository: `C:\Users\Omen\property-broker-chatbot`  
Date: 2026-06-20

## Final Preflight Checks

- Confirm Python venv exists and dependencies are installed:
  - `venv\Scripts\python.exe -m pip install -r requirements.txt`
- Confirm app is locked to MySQL mode:
  - `.env` has `USE_SQLITE=0`
  - No startup log line contains `falling back to SQLite`
- Confirm local MySQL is reachable on configured port:
  - `Get-NetTCPConnection -LocalPort 3306 -State Listen`
- Confirm schema/tables exist in target DB (`jakkash_property`):
  - `admins`, `properties`, `inquiries`, `owner_submissions`, `seller_profiles`, `customer_visits`, `activity_logs`
- Confirm Flask is started with production-safe flags:
  - `FLASK_DEBUG=0`
  - `FLASK_SECRET_KEY` set to a strong non-default value

## Required Production Env Vars

- Core:
  - `FLASK_SECRET_KEY`
  - `FLASK_ENV=production`
  - `FLASK_DEBUG=0`
  - `USE_SQLITE=0`
  - `MYSQL_HOST`
  - `MYSQL_PORT`
  - `MYSQL_USER`
  - `MYSQL_PASSWORD`
  - `MYSQL_DATABASE`
  - `DEFAULT_ADMIN_PASSWORD`
- Admin OAuth (Google):
  - `GOOGLE_OAUTH_CLIENT_ID`
  - `GOOGLE_OAUTH_CLIENT_SECRET`
  - `GOOGLE_OAUTH_REDIRECT_URI`
- OTP/SMS (Twilio):
  - `SMS_PROVIDER=twilio`
  - `TWILIO_ACCOUNT_SID`
  - `TWILIO_AUTH_TOKEN`
  - `TWILIO_FROM_NUMBER`
  - `ALLOW_DEV_OTP_FALLBACK=false`
- Branding/contact (required for rendered templates):
  - `COMPANY_EMAIL`
  - `COMPANY_ADDRESS`
  - `COMPANY_WHATSAPP`

## One-Command Startup / Check Commands

- Start local MySQL:
  - `powershell -ExecutionPolicy Bypass -File .\scripts\start-local-mysql.ps1`
- Start Flask app (PowerShell one-liner):
  - `powershell -NoProfile -Command "$env:FLASK_DEBUG='0'; $env:USE_SQLITE='0'; venv\Scripts\python.exe app.py"`
- Quick smoke/status probe (PowerShell one-liner):
  - `powershell -NoProfile -Command "$urls=@('/','/price-ai','/admin/login','/admin/forgot-password','/admin/','/admin/properties','/admin/inquiries','/admin/activity','/admin/sellers','/admin/visits','/admin/employees'); foreach($u in $urls){try{$r=Invoke-WebRequest -Uri ('http://127.0.0.1:5000'+$u) -MaximumRedirection 0 -TimeoutSec 10 -ErrorAction Stop; Write-Output ($u+' -> '+[int]$r.StatusCode)}catch{if($_.Exception.Response){Write-Output ($u+' -> '+[int]$_.Exception.Response.StatusCode)}else{Write-Output ($u+' -> ERROR '+$_.Exception.Message)}}}"`

## Post-Deploy Smoke Checks

- Public + auth routes:
  - `GET /` -> `200`
  - `GET /price-ai` -> `200`
  - `GET /admin/login` -> `200` (or `302` to `/admin/` when already authenticated)
  - `GET /admin/forgot-password` -> `200`
- Admin auth behavior (unauthenticated session):
  - `GET /admin/` -> `302` to login
  - `GET /admin/properties` -> `302` to login
  - `GET /admin/inquiries` -> `302` to login
  - `GET /admin/activity` -> `302` to login
  - `GET /admin/sellers` -> `302` to login
  - `GET /admin/visits` -> `302` to login
  - `GET /admin/employees` -> `302` to login
- Admin authorized behavior (authenticated + OTP verified):
  - `GET /admin/` -> `200`
  - `GET /admin/properties` -> `200` with `manage_properties`
  - `GET /admin/inquiries` -> `200` with `manage_inquiries`
  - `GET /admin/sellers` -> `200` with `manage_sellers`
  - `GET /admin/visits` -> `200` with `manage_customer_visits`
  - `GET /admin/activity` -> `200` for super admin (else `403`)
  - `GET /admin/employees` -> `200` for super admin (else `403`)
