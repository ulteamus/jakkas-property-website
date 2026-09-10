-- Row Level Security
-- Public site reads active/available listings; CRM writes use service role
-- (bypasses RLS) from the Flask backend.
-- ---------------------------------------------------------------------------

ALTER TABLE properties ENABLE ROW LEVEL SECURITY;
ALTER TABLE property_images ENABLE ROW LEVEL SECURITY;
ALTER TABLE property_videos ENABLE ROW LEVEL SECURITY;
ALTER TABLE property_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE testimonials ENABLE ROW LEVEL SECURITY;
ALTER TABLE review_comments ENABLE ROW LEVEL SECURITY;
ALTER TABLE inquiries ENABLE ROW LEVEL SECURITY;
ALTER TABLE leads ENABLE ROW LEVEL SECURITY;
ALTER TABLE admins ENABLE ROW LEVEL SECURITY;
ALTER TABLE seller_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE customer_visits ENABLE ROW LEVEL SECURITY;
ALTER TABLE owner_submissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE activity_logs ENABLE ROW LEVEL SECURITY;

-- Drop-and-recreate policies for idempotent re-runs
DROP POLICY IF EXISTS properties_public_read ON properties;
CREATE POLICY properties_public_read ON properties
  FOR SELECT
  USING (status IN ('available', 'active', 'sold', 'rented') OR status IS NOT NULL);

DROP POLICY IF EXISTS property_images_public_read ON property_images;
CREATE POLICY property_images_public_read ON property_images
  FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM properties p
      WHERE p.id = property_images.property_id
    )
  );

DROP POLICY IF EXISTS property_videos_public_read ON property_videos;
CREATE POLICY property_videos_public_read ON property_videos
  FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM properties p
      WHERE p.id = property_videos.property_id
    )
  );

DROP POLICY IF EXISTS testimonials_public_read ON testimonials;
CREATE POLICY testimonials_public_read ON testimonials
  FOR SELECT
  USING (is_active IS TRUE);

DROP POLICY IF EXISTS review_comments_public_read ON review_comments;
CREATE POLICY review_comments_public_read ON review_comments
  FOR SELECT
  USING (is_active IS TRUE);

-- Authenticated role: full read for CRM-facing tables (PostgREST JWT).
-- Flask uses the service role key for writes (RLS bypass). Tighten further
-- if you expose PostgREST to browsers with anon/authenticated keys.

DROP POLICY IF EXISTS crm_auth_read_inquiries ON inquiries;
CREATE POLICY crm_auth_read_inquiries ON inquiries
  FOR SELECT TO authenticated
  USING (true);

DROP POLICY IF EXISTS crm_auth_read_leads ON leads;
CREATE POLICY crm_auth_read_leads ON leads
  FOR SELECT TO authenticated
  USING (true);

DROP POLICY IF EXISTS crm_auth_read_admins ON admins;
CREATE POLICY crm_auth_read_admins ON admins
  FOR SELECT TO authenticated
  USING (true);

DROP POLICY IF EXISTS crm_auth_read_sellers ON seller_profiles;
CREATE POLICY crm_auth_read_sellers ON seller_profiles
  FOR SELECT TO authenticated
  USING (true);

DROP POLICY IF EXISTS crm_auth_read_visits ON customer_visits;
CREATE POLICY crm_auth_read_visits ON customer_visits
  FOR SELECT TO authenticated
  USING (true);

DROP POLICY IF EXISTS crm_auth_read_submissions ON owner_submissions;
CREATE POLICY crm_auth_read_submissions ON owner_submissions
  FOR SELECT TO authenticated
  USING (true);

DROP POLICY IF EXISTS crm_auth_read_activity ON activity_logs;
CREATE POLICY crm_auth_read_activity ON activity_logs
  FOR SELECT TO authenticated
  USING (true);

-- Public insert for contact / sell forms via anon key (optional PostgREST path)
DROP POLICY IF EXISTS inquiries_anon_insert ON inquiries;
CREATE POLICY inquiries_anon_insert ON inquiries
  FOR INSERT TO anon, authenticated
  WITH CHECK (true);

DROP POLICY IF EXISTS submissions_anon_insert ON owner_submissions;
CREATE POLICY submissions_anon_insert ON owner_submissions
  FOR INSERT TO anon, authenticated
  WITH CHECK (true);


-- ---------------------------------------------------------------------------
