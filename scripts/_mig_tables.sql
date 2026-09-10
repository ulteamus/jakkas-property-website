-- Jakkash Property Broker — Supabase PostgreSQL schema
-- Apply in Supabase SQL Editor (Dashboard → SQL → New query), or:
--   psql "$SUPABASE_DB_URL" -f database/supabase_schema.sql
--
-- Maps to models under models/*.py (table names match SQLite/MySQL app code).
-- "seller_info" in product language = seller_profiles table.
-- "reviews" = testimonials + review_comments.


CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ---------------------------------------------------------------------------
-- Core tables
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS admins (
  id BIGSERIAL PRIMARY KEY,
  username TEXT NOT NULL UNIQUE,
  email TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  full_name TEXT DEFAULT 'Sam',
  role TEXT DEFAULT 'main_admin',
  permissions_json JSONB,
  phone TEXT,
  phone_verified BOOLEAN DEFAULT FALSE,
  require_otp BOOLEAN DEFAULT TRUE,
  mobile_otp_enabled BOOLEAN DEFAULT TRUE,
  mobile_otp_hash TEXT,
  mobile_otp_expires_at TIMESTAMPTZ,
  mobile_otp_sent_at TIMESTAMPTZ,
  totp_enabled BOOLEAN DEFAULT FALSE,
  totp_secret TEXT,
  last_otp_verified_at TIMESTAMPTZ,
  created_by_admin_id BIGINT REFERENCES admins(id) ON DELETE SET NULL,
  password_reset_failed_attempts INTEGER DEFAULT 0,
  password_reset_locked_until TIMESTAMPTZ,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS properties (
  id BIGSERIAL PRIMARY KEY,
  property_name TEXT NOT NULL,
  slug TEXT UNIQUE,
  property_type TEXT NOT NULL,
  area_name TEXT NOT NULL,
  address TEXT,
  price DOUBLE PRECISION NOT NULL,
  bhk INTEGER DEFAULT 0,
  sq_ft DOUBLE PRECISION NOT NULL,
  description TEXT,
  amenities JSONB,
  latitude DOUBLE PRECISION DEFAULT 21.1702,
  longitude DOUBLE PRECISION DEFAULT 72.8311,
  status TEXT DEFAULT 'available',
  is_featured BOOLEAN DEFAULT FALSE,
  listing_type TEXT DEFAULT 'sale',
  view_count INTEGER DEFAULT 0,
  primary_image TEXT,
  owner_admin_id BIGINT REFERENCES admins(id) ON DELETE SET NULL,
  creation_source TEXT DEFAULT 'admin',
  block_wing TEXT,
  unit_number TEXT,
  listing_intent TEXT DEFAULT 'sell',
  seller_type TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_properties_status ON properties(status);
CREATE INDEX IF NOT EXISTS idx_properties_area ON properties(area_name);
CREATE INDEX IF NOT EXISTS idx_properties_type ON properties(property_type);

CREATE TABLE IF NOT EXISTS property_images (
  id BIGSERIAL PRIMARY KEY,
  property_id BIGINT NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
  file_path TEXT NOT NULL,
  sort_order INTEGER DEFAULT 0,
  is_primary BOOLEAN DEFAULT FALSE,
  uploaded_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS property_videos (
  id BIGSERIAL PRIMARY KEY,
  property_id BIGINT NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
  file_path TEXT NOT NULL,
  title TEXT,
  sort_order INTEGER DEFAULT 0,
  uploaded_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS property_documents (
  id BIGSERIAL PRIMARY KEY,
  property_id BIGINT NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
  file_path TEXT NOT NULL,
  doc_name TEXT,
  uploaded_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS inquiries (
  id BIGSERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  mobile TEXT NOT NULL,
  email TEXT,
  message TEXT,
  property_id BIGINT REFERENCES properties(id) ON DELETE SET NULL,
  source TEXT DEFAULT 'contact_form',
  status TEXT DEFAULT 'new',
  notes TEXT,
  budget TEXT,
  preferred_location TEXT,
  inquiry_type TEXT DEFAULT 'general',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS owner_submissions (
  id BIGSERIAL PRIMARY KEY,
  property_id BIGINT REFERENCES properties(id) ON DELETE SET NULL,
  owner_name TEXT NOT NULL,
  owner_mobile TEXT NOT NULL,
  owner_alt_mobile TEXT,
  owner_email TEXT,
  owner_address TEXT NOT NULL,
  property_title TEXT NOT NULL,
  property_type TEXT NOT NULL,
  property_status TEXT DEFAULT 'buy',
  bhk INTEGER DEFAULT 0,
  bungalow_number TEXT,
  apartment_number TEXT,
  area_sq_ft DOUBLE PRECISION,
  price DOUBLE PRECISION,
  property_address TEXT NOT NULL,
  city TEXT DEFAULT 'Surat',
  location_area TEXT,
  description TEXT,
  amenities_json JSONB,
  listing_intent TEXT DEFAULT 'buy',
  images_json JSONB,
  videos_json JSONB,
  status TEXT DEFAULT 'pending',
  owner_admin_id BIGINT REFERENCES admins(id) ON DELETE SET NULL,
  reviewed_by BIGINT REFERENCES admins(id) ON DELETE SET NULL,
  reviewed_at TIMESTAMPTZ,
  review_note TEXT,
  submitter_type TEXT DEFAULT 'owner',
  area_unit TEXT,
  area_value DOUBLE PRECISION,
  block_wing TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS leads (
  id BIGSERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  mobile TEXT NOT NULL,
  email TEXT,
  budget DOUBLE PRECISION,
  preferred_area TEXT,
  property_id BIGINT REFERENCES properties(id) ON DELETE SET NULL,
  inquiry_id BIGINT REFERENCES inquiries(id) ON DELETE SET NULL,
  status TEXT DEFAULT 'new',
  lead_score INTEGER DEFAULT 0,
  lead_tier TEXT DEFAULT 'cold',
  follow_up_date TIMESTAMPTZ,
  is_urgent BOOLEAN DEFAULT FALSE,
  whatsapp_clicks INTEGER DEFAULT 0,
  call_clicks INTEGER DEFAULT 0,
  properties_viewed INTEGER DEFAULT 0,
  time_on_site_sec INTEGER DEFAULT 0,
  saved_count INTEGER DEFAULT 0,
  inquiry_date TIMESTAMPTZ DEFAULT NOW(),
  last_contacted_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS lead_notes (
  id BIGSERIAL PRIMARY KEY,
  lead_id BIGINT NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
  admin_id BIGINT REFERENCES admins(id) ON DELETE SET NULL,
  note TEXT NOT NULL,
  follow_up_date TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS saved_properties (
  id BIGSERIAL PRIMARY KEY,
  session_id TEXT NOT NULL,
  property_id BIGINT NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (session_id, property_id)
);

CREATE TABLE IF NOT EXISTS property_views (
  id BIGSERIAL PRIMARY KEY,
  property_id BIGINT NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
  visitor_id TEXT,
  session_id TEXT,
  viewed_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS visitors (
  id BIGSERIAL PRIMARY KEY,
  visitor_id TEXT NOT NULL UNIQUE,
  session_id TEXT,
  ip_hash TEXT,
  user_agent TEXT,
  first_visit TIMESTAMPTZ DEFAULT NOW(),
  last_visit TIMESTAMPTZ DEFAULT NOW(),
  visit_count INTEGER DEFAULT 1,
  total_time_sec INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS visitor_events (
  id BIGSERIAL PRIMARY KEY,
  visitor_id TEXT NOT NULL,
  event_type TEXT NOT NULL,
  property_id BIGINT REFERENCES properties(id) ON DELETE SET NULL,
  meta JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS search_analytics (
  id BIGSERIAL PRIMARY KEY,
  area_name TEXT,
  property_type TEXT,
  min_budget DOUBLE PRECISION,
  max_budget DOUBLE PRECISION,
  bhk INTEGER,
  session_id TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS area_demand (
  id BIGSERIAL PRIMARY KEY,
  area_name TEXT NOT NULL UNIQUE,
  view_count INTEGER DEFAULT 0,
  search_count INTEGER DEFAULT 0,
  inquiry_count INTEGER DEFAULT 0,
  demand_score DOUBLE PRECISION DEFAULT 0,
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Product "reviews"
CREATE TABLE IF NOT EXISTS testimonials (
  id BIGSERIAL PRIMARY KEY,
  client_name TEXT NOT NULL,
  client_location TEXT DEFAULT 'Surat',
  review_text TEXT NOT NULL,
  rating INTEGER DEFAULT 5,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS review_comments (
  id BIGSERIAL PRIMARY KEY,
  testimonial_id BIGINT NOT NULL REFERENCES testimonials(id) ON DELETE CASCADE,
  commenter_name TEXT NOT NULL,
  commenter_email TEXT,
  comment_text TEXT NOT NULL,
  is_active BOOLEAN DEFAULT TRUE,
  admin_id BIGINT REFERENCES admins(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Product "seller_info"
CREATE TABLE IF NOT EXISTS seller_profiles (
  id BIGSERIAL PRIMARY KEY,
  full_name TEXT NOT NULL,
  mobile TEXT NOT NULL,
  email TEXT,
  address TEXT,
  tags_text TEXT,
  notes TEXT,
  created_by_admin_id BIGINT REFERENCES admins(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_seller_profiles_mobile ON seller_profiles(mobile);

CREATE TABLE IF NOT EXISTS customer_visits (
  id BIGSERIAL PRIMARY KEY,
  visit_date DATE NOT NULL,
  client_name TEXT NOT NULL,
  client_address TEXT,
  client_contact TEXT NOT NULL,
  client_requirement TEXT,
  property_id BIGINT REFERENCES properties(id) ON DELETE SET NULL,
  property_ids JSONB,
  executive_admin_id BIGINT REFERENCES admins(id) ON DELETE SET NULL,
  executive_name TEXT,
  executive_address TEXT,
  executive_contact TEXT,
  customer_signature_label TEXT,
  executive_signature_label TEXT,
  customer_signature_data TEXT,
  executive_signature_data TEXT,
  created_by_admin_id BIGINT REFERENCES admins(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS activity_logs (
  id BIGSERIAL PRIMARY KEY,
  admin_id BIGINT REFERENCES admins(id) ON DELETE SET NULL,
  action_key TEXT NOT NULL,
  action_label TEXT NOT NULL,
  entity_type TEXT,
  entity_id BIGINT,
  meta_json JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ---------------------------------------------------------------------------
