# JAKKASH PROPERTY CONSULTANCY

Production-ready real estate platform for **Surat, Gujarat, India**.

**Team:** JAKKASH Property Team  
**Office:** 40,Ganesh Krupa Soc,Opp Gail Tower ,Anand Mahal Road ,Surat 395009  
**Phone:** +91 85117-51119

## Platform Modules

| Module | Description |
|--------|-------------|
| Public Website | Home, listings, detail, map, about, services, testimonials, contact, AI chatbot, sell-property |
| Admin Portal | Dashboard, properties, leads, inquiries, analytics |
| Lead Management | Scoring, tiers (cold/warm/hot), notes, follow-ups |
| AI / ML | Lead scoring, recommendations, price prediction, demand analytics |
| Surat Map | Leaflet + OpenStreetMap with category markers |
| Media | Images, videos, PDF documents per property |

## Tech Stack

- **Frontend:** HTML5, CSS3, Bootstrap 5, JavaScript, AJAX
- **Backend:** Python Flask, Flask-Login, Flask-WTF (CSRF)
- **Database:** MySQL
- **Maps:** Leaflet.js + OpenStreetMap
- **ML:** scikit-learn, pandas, numpy (optional XGBoost on Python 3.11–3.12)

## Quick Start

### 1. MySQL

```bash
mysql -u root -p < database/schema.sql
```

### 2. Environment

```bash
copy .env.example .env
```

Set `MYSQL_PASSWORD` and `FLASK_SECRET_KEY`.

### 3. Python

```bash
py -3 -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
py -3 ml\train_models.py
```

### 4. Run

```bash
py -3 app.py
```

- **Website:** http://127.0.0.1:5000  
- **Admin:** http://127.0.0.1:5000/admin/login  
- **Bootstrap admin username:** `sam`
- **Bootstrap admin password:** defaults to `jodika` (override with `DEFAULT_ADMIN_PASSWORD`)

## Folder Structure

```
property-broker-chatbot/
├── app.py
├── config.py
├── database/schema.sql
├── models/          # admin, property, lead, inquiry, analytics
├── routes/          # public, admin_portal, api, auth
├── services/        # ML, WhatsApp, follow-up
├── ml/train_models.py
├── templates/public/
├── templates/admin/
├── static/css|js|img/
└── uploads/properties/{id}/images|videos|documents/
```

## API (JSON)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/properties` | GET | Search/filter |
| `/api/properties/map` | GET | Map markers |
| `/api/inquiry` | POST | Submit inquiry + create lead |
| `/api/whatsapp/interest` | POST | WhatsApp deep link |
| `/api/saved` | GET/POST/DELETE | Saved properties |
| `/api/predict-price` | POST | Price prediction |

## Security

- Password hashing (Werkzeug)
- CSRF on admin forms
- Parameterized SQL queries
- File type validation on uploads
- Session cookies (HttpOnly)

## Branding

Theme colors: **Orange** `#F58220`, **Black** `#1a1a1a`, **White**

Logo: `static/img/logo.png`

## License

Proprietary — Jakkash Property Consultancy
