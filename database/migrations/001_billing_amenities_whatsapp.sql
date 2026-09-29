-- 001: dynamic amenities, billing receipts/payments, WhatsApp promo (Tier A) tables.
-- Idempotent: safe to re-run. Apply with:
--   python scripts/migrate_cloud_supabase.py --migration database/migrations/001_billing_amenities_whatsapp.sql
-- RLS is enabled with no policies: anon/authenticated PostgREST roles get no access;
-- the Flask backend connects as the table owner / service role.

BEGIN;

CREATE TABLE IF NOT EXISTS amenities (
  id BIGSERIAL PRIMARY KEY,
  slug TEXT NOT NULL UNIQUE,
  label TEXT NOT NULL,
  is_active BOOLEAN DEFAULT TRUE,
  sort_order INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS billing_receipts (
  id BIGSERIAL PRIMARY KEY,
  receipt_no TEXT UNIQUE,
  property_id BIGINT REFERENCES properties(id) ON DELETE SET NULL,
  property_name TEXT,
  property_address TEXT,
  deal_type TEXT NOT NULL DEFAULT 'sale',
  client_name TEXT NOT NULL,
  client_mobile TEXT,
  client_email TEXT,
  client_address TEXT,
  deal_amount NUMERIC(14,2) DEFAULT 0,
  brokerage_amount NUMERIC(14,2) NOT NULL DEFAULT 0,
  gst_enabled BOOLEAN DEFAULT FALSE,
  gst_rate NUMERIC(5,2) DEFAULT 18,
  gst_amount NUMERIC(14,2) DEFAULT 0,
  total_amount NUMERIC(14,2) NOT NULL DEFAULT 0,
  status TEXT DEFAULT 'unpaid',
  notes TEXT,
  void_reason TEXT,
  voided_at TIMESTAMPTZ,
  created_by_admin_id BIGINT REFERENCES admins(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS billing_payments (
  id BIGSERIAL PRIMARY KEY,
  receipt_id BIGINT NOT NULL REFERENCES billing_receipts(id) ON DELETE CASCADE,
  amount NUMERIC(14,2) NOT NULL CHECK (amount > 0),
  payment_date DATE,
  method TEXT,
  reference TEXT,
  note TEXT,
  recorded_by_admin_id BIGINT REFERENCES admins(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS whatsapp_opt_ins (
  id BIGSERIAL PRIMARY KEY,
  phone TEXT NOT NULL UNIQUE,
  status TEXT NOT NULL DEFAULT 'opted_in',
  source TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS whatsapp_promo_log (
  id BIGSERIAL PRIMARY KEY,
  phone TEXT NOT NULL,
  contact_name TEXT,
  source_type TEXT,
  source_id BIGINT,
  property_id BIGINT REFERENCES properties(id) ON DELETE SET NULL,
  channel TEXT DEFAULT 'wa_link',
  message TEXT,
  sent_by_admin_id BIGINT REFERENCES admins(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_billing_receipts_property ON billing_receipts(property_id);
CREATE INDEX IF NOT EXISTS idx_billing_receipts_created ON billing_receipts(created_at);
CREATE INDEX IF NOT EXISTS idx_billing_payments_receipt ON billing_payments(receipt_id);
CREATE INDEX IF NOT EXISTS idx_whatsapp_promo_log_phone ON whatsapp_promo_log(phone, created_at);

ALTER TABLE amenities ENABLE ROW LEVEL SECURITY;
ALTER TABLE billing_receipts ENABLE ROW LEVEL SECURITY;
ALTER TABLE billing_payments ENABLE ROW LEVEL SECURITY;
ALTER TABLE whatsapp_opt_ins ENABLE ROW LEVEL SECURITY;
ALTER TABLE whatsapp_promo_log ENABLE ROW LEVEL SECURITY;

INSERT INTO amenities (slug, label, sort_order) VALUES
  ('parking', 'Parking', 10),
  ('lift', 'Lift', 20),
  ('security', 'Security', 30),
  ('power_backup', 'Power Backup', 40),
  ('garden', 'Garden', 50),
  ('gym', 'Gym', 60),
  ('swimming_pool', 'Swimming Pool', 70),
  ('club_house', 'Club House', 80),
  ('cctv', 'CCTV', 90),
  ('water_supply', 'Water Supply', 100)
ON CONFLICT (slug) DO NOTHING;

COMMIT;
