-- Client feedback: RLS + storage + reviews public access
-- Run in Supabase SQL Editor (project jakkas-property-india / Mumbai)

BEGIN;

-- ---------------------------------------------------------------------------
-- Reviews: product table alias over testimonials
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS testimonials (
  id BIGSERIAL PRIMARY KEY,
  client_name TEXT NOT NULL,
  client_location TEXT DEFAULT 'Surat',
  review_text TEXT NOT NULL,
  rating INTEGER DEFAULT 5,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE OR REPLACE VIEW reviews AS
SELECT
  id,
  client_name,
  client_location,
  review_text,
  rating,
  is_active,
  created_at
FROM testimonials;

ALTER TABLE testimonials ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS testimonials_public_read ON testimonials;
CREATE POLICY testimonials_public_read ON testimonials
  FOR SELECT
  USING (is_active IS TRUE);

DROP POLICY IF EXISTS testimonials_public_insert ON testimonials;
CREATE POLICY testimonials_public_insert ON testimonials
  FOR INSERT TO anon, authenticated
  WITH CHECK (true);

DROP POLICY IF EXISTS reviews_public_read ON testimonials;
-- (view uses underlying table policies)

-- ---------------------------------------------------------------------------
-- Properties: public read for approved / available / active
-- ---------------------------------------------------------------------------
ALTER TABLE properties ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS properties_public_read ON properties;
CREATE POLICY properties_public_read ON properties
  FOR SELECT
  USING (
    LOWER(COALESCE(status, '')) IN ('available', 'approved', 'active', 'sold', 'rented')
  );

-- Optional owner tracking for Supabase Auth dashboards
ALTER TABLE properties ADD COLUMN IF NOT EXISTS user_id UUID;
ALTER TABLE owner_submissions ADD COLUMN IF NOT EXISTS user_id UUID;

CREATE INDEX IF NOT EXISTS idx_properties_user_id ON properties(user_id);
CREATE INDEX IF NOT EXISTS idx_owner_submissions_user_id ON owner_submissions(user_id);

DROP POLICY IF EXISTS properties_owner_select ON properties;
CREATE POLICY properties_owner_select ON properties
  FOR SELECT TO authenticated
  USING (user_id = auth.uid() OR LOWER(COALESCE(status, '')) IN ('available', 'approved', 'active', 'sold', 'rented'));

DROP POLICY IF EXISTS submissions_owner_select ON owner_submissions;
CREATE POLICY submissions_owner_select ON owner_submissions
  FOR SELECT TO authenticated
  USING (user_id = auth.uid());

DROP POLICY IF EXISTS submissions_anon_insert ON owner_submissions;
CREATE POLICY submissions_anon_insert ON owner_submissions
  FOR INSERT TO anon, authenticated
  WITH CHECK (true);

-- ---------------------------------------------------------------------------
-- Storage bucket: property-media (public read)
-- ---------------------------------------------------------------------------
INSERT INTO storage.buckets (id, name, public)
VALUES ('property-media', 'property-media', true)
ON CONFLICT (id) DO UPDATE SET public = EXCLUDED.public;

DROP POLICY IF EXISTS property_media_public_read ON storage.objects;
CREATE POLICY property_media_public_read ON storage.objects
  FOR SELECT
  USING (bucket_id = 'property-media');

DROP POLICY IF EXISTS property_media_auth_insert ON storage.objects;
CREATE POLICY property_media_auth_insert ON storage.objects
  FOR INSERT TO authenticated, anon, service_role
  WITH CHECK (bucket_id = 'property-media');

DROP POLICY IF EXISTS property_media_auth_update ON storage.objects;
CREATE POLICY property_media_auth_update ON storage.objects
  FOR UPDATE TO authenticated, service_role
  USING (bucket_id = 'property-media');

COMMIT;
