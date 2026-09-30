-- Migration 002: client GSTIN on receipts, admin bell notifications, consented lead captures.
-- Idempotent: safe to re-run. New tables get RLS enabled with no policies (server uses service role),
-- matching migration 001.
-- Apply with: python scripts/migrate_cloud_supabase.py --migration database/migrations/002_gstin_notifications_leadcapture.sql

BEGIN;

ALTER TABLE billing_receipts ADD COLUMN IF NOT EXISTS client_gstin TEXT;

CREATE TABLE IF NOT EXISTS admin_notifications (
  id BIGSERIAL PRIMARY KEY,
  kind TEXT NOT NULL,
  title TEXT NOT NULL,
  body TEXT,
  link TEXT,
  ref_id BIGINT,
  dedupe_key TEXT UNIQUE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS admin_notification_state (
  admin_id BIGINT PRIMARY KEY REFERENCES admins(id) ON DELETE CASCADE,
  last_seen_id BIGINT NOT NULL DEFAULT 0,
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS lead_captures (
  id BIGSERIAL PRIMARY KEY,
  phone TEXT NOT NULL,
  name TEXT,
  source TEXT NOT NULL DEFAULT 'sell_page',
  consent BOOLEAN NOT NULL DEFAULT FALSE,
  consent_text TEXT,
  visitor_id TEXT,
  session_id TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_admin_notifications_created ON admin_notifications(created_at);
CREATE INDEX IF NOT EXISTS idx_lead_captures_created ON lead_captures(created_at);
CREATE INDEX IF NOT EXISTS idx_visitor_events_type_created ON visitor_events(event_type, created_at);

ALTER TABLE admin_notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE admin_notification_state ENABLE ROW LEVEL SECURITY;
ALTER TABLE lead_captures ENABLE ROW LEVEL SECURITY;

UPDATE owner_submissions SET listing_intent = 'sell' WHERE listing_intent IN ('buy', 'sale');

COMMIT;
