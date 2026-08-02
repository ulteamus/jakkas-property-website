-- Jakkash Property Consultancy - Complete MySQL Schema
-- Surat, Gujarat, India

CREATE DATABASE IF NOT EXISTS jakkash_property
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE jakkash_property;

-- Admins (Flask-Login)
CREATE TABLE IF NOT EXISTS admins (
  id INT AUTO_INCREMENT PRIMARY KEY,
  username VARCHAR(80) NOT NULL UNIQUE,
  email VARCHAR(120) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  full_name VARCHAR(120) DEFAULT 'Sam',
  role VARCHAR(32) DEFAULT 'main_admin',
  permissions_json TEXT,
  phone VARCHAR(30),
  phone_verified TINYINT(1) DEFAULT 0,
  require_otp TINYINT(1) DEFAULT 1,
  mobile_otp_enabled TINYINT(1) DEFAULT 1,
  mobile_otp_hash VARCHAR(255),
  mobile_otp_expires_at DATETIME NULL,
  mobile_otp_sent_at DATETIME NULL,
  totp_enabled TINYINT(1) DEFAULT 0,
  totp_secret VARCHAR(64),
  last_otp_verified_at DATETIME NULL,
  created_by_admin_id INT NULL,
  password_reset_failed_attempts INT DEFAULT 0,
  password_reset_locked_until DATETIME NULL,
  is_active TINYINT(1) DEFAULT 1,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS properties (
  id INT AUTO_INCREMENT PRIMARY KEY,
  property_name VARCHAR(200) NOT NULL,
  slug VARCHAR(220) UNIQUE,
  property_type ENUM('flat','shop','office','bungalow','plot') NOT NULL,
  area_name VARCHAR(120) NOT NULL COMMENT 'Surat locality',
  address TEXT,
  price DECIMAL(15,2) NOT NULL,
  bhk INT DEFAULT 0,
  sq_ft DECIMAL(10,2) NOT NULL,
  description TEXT,
  amenities JSON,
  latitude DECIMAL(10,7) DEFAULT 21.1702000,
  longitude DECIMAL(10,7) DEFAULT 72.8311000,
  status ENUM('available','sold','rented','reserved') DEFAULT 'available',
  is_featured TINYINT(1) DEFAULT 0,
  listing_type ENUM('sale','rent') DEFAULT 'sale',
  view_count INT DEFAULT 0,
  primary_image VARCHAR(500),
  owner_admin_id INT NULL,
  creation_source VARCHAR(40) DEFAULT 'admin',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_area (area_name),
  INDEX idx_type (property_type),
  INDEX idx_status (status),
  INDEX idx_price (price),
  INDEX idx_featured (is_featured)
);

CREATE TABLE IF NOT EXISTS property_images (
  id INT AUTO_INCREMENT PRIMARY KEY,
  property_id INT NOT NULL,
  file_path VARCHAR(500) NOT NULL,
  sort_order INT DEFAULT 0,
  is_primary TINYINT(1) DEFAULT 0,
  uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (property_id) REFERENCES properties(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS property_videos (
  id INT AUTO_INCREMENT PRIMARY KEY,
  property_id INT NOT NULL,
  file_path VARCHAR(500) NOT NULL,
  title VARCHAR(200),
  sort_order INT DEFAULT 0,
  uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (property_id) REFERENCES properties(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS property_documents (
  id INT AUTO_INCREMENT PRIMARY KEY,
  property_id INT NOT NULL,
  file_path VARCHAR(500) NOT NULL,
  doc_name VARCHAR(200),
  uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (property_id) REFERENCES properties(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS inquiries (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(120) NOT NULL,
  mobile VARCHAR(20) NOT NULL,
  email VARCHAR(120),
  message TEXT,
  property_id INT,
  source VARCHAR(50) DEFAULT 'contact_form',
  status VARCHAR(30) DEFAULT 'new',
  notes TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_inquiries_status (status),
  INDEX idx_inquiries_created_at (created_at),
  FOREIGN KEY (property_id) REFERENCES properties(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS owner_submissions (
  id INT AUTO_INCREMENT PRIMARY KEY,
  property_id INT,
  owner_name VARCHAR(160) NOT NULL,
  owner_mobile VARCHAR(30) NOT NULL,
  owner_alt_mobile VARCHAR(30),
  owner_email VARCHAR(180),
  owner_address TEXT NOT NULL,
  property_title VARCHAR(220) NOT NULL,
  property_type VARCHAR(80) NOT NULL,
  property_status ENUM('buy', 'sell', 'rent') DEFAULT 'buy',
  bhk INT DEFAULT 0,
  bungalow_number VARCHAR(80),
  area_sq_ft DECIMAL(12,2),
  price DECIMAL(15,2),
  property_address TEXT NOT NULL,
  city VARCHAR(100) DEFAULT 'Surat',
  location_area VARCHAR(150),
  description TEXT,
  amenities_json JSON,
  listing_intent ENUM('buy', 'sell', 'rent') DEFAULT 'buy',
  images_json JSON,
  videos_json JSON,
  status ENUM('pending', 'approved', 'rejected') DEFAULT 'pending',
  owner_admin_id INT NULL,
  reviewed_by INT NULL,
  reviewed_at TIMESTAMP NULL,
  review_note TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_owner_submission_property (property_id),
  INDEX idx_owner_submission_status (status),
  INDEX idx_owner_submission_owner_admin (owner_admin_id),
  FOREIGN KEY (property_id) REFERENCES properties(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS leads (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(120) NOT NULL,
  mobile VARCHAR(20) NOT NULL,
  email VARCHAR(120),
  budget DECIMAL(15,2),
  preferred_area VARCHAR(120),
  property_id INT,
  inquiry_id INT,
  status ENUM('new','contacted','interested','site_visit_scheduled','closed') DEFAULT 'new',
  lead_score INT DEFAULT 0,
  lead_tier ENUM('cold','warm','hot') DEFAULT 'cold',
  follow_up_date DATE,
  is_urgent TINYINT(1) DEFAULT 0,
  whatsapp_clicks INT DEFAULT 0,
  call_clicks INT DEFAULT 0,
  properties_viewed INT DEFAULT 0,
  time_on_site_sec INT DEFAULT 0,
  saved_count INT DEFAULT 0,
  inquiry_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  last_contacted_at TIMESTAMP NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (property_id) REFERENCES properties(id) ON DELETE SET NULL,
  FOREIGN KEY (inquiry_id) REFERENCES inquiries(id) ON DELETE SET NULL,
  INDEX idx_status (status),
  INDEX idx_tier (lead_tier),
  INDEX idx_score (lead_score)
);

CREATE TABLE IF NOT EXISTS lead_notes (
  id INT AUTO_INCREMENT PRIMARY KEY,
  lead_id INT NOT NULL,
  admin_id INT,
  note TEXT NOT NULL,
  follow_up_date DATE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (lead_id) REFERENCES leads(id) ON DELETE CASCADE,
  FOREIGN KEY (admin_id) REFERENCES admins(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS saved_properties (
  id INT AUTO_INCREMENT PRIMARY KEY,
  session_id VARCHAR(64) NOT NULL,
  property_id INT NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_session_property (session_id, property_id),
  FOREIGN KEY (property_id) REFERENCES properties(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS property_views (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  property_id INT NOT NULL,
  visitor_id VARCHAR(64),
  session_id VARCHAR(64),
  viewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (property_id) REFERENCES properties(id) ON DELETE CASCADE,
  INDEX idx_property (property_id),
  INDEX idx_viewed (viewed_at)
);

CREATE TABLE IF NOT EXISTS visitors (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  visitor_id VARCHAR(64) NOT NULL UNIQUE,
  session_id VARCHAR(64),
  ip_hash VARCHAR(64),
  user_agent VARCHAR(300),
  first_visit TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  last_visit TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  visit_count INT DEFAULT 1,
  total_time_sec INT DEFAULT 0,
  INDEX idx_visitor (visitor_id)
);

CREATE TABLE IF NOT EXISTS visitor_events (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  visitor_id VARCHAR(64) NOT NULL,
  event_type ENUM('page_view','property_view','whatsapp_click','call_click','inquiry','save_property','search') NOT NULL,
  property_id INT,
  meta JSON,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_event_type (event_type),
  INDEX idx_created (created_at)
);

CREATE TABLE IF NOT EXISTS search_analytics (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  area_name VARCHAR(120),
  property_type VARCHAR(50),
  min_budget DECIMAL(15,2),
  max_budget DECIMAL(15,2),
  bhk INT,
  session_id VARCHAR(64),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_area (area_name)
);

CREATE TABLE IF NOT EXISTS area_demand (
  id INT AUTO_INCREMENT PRIMARY KEY,
  area_name VARCHAR(120) NOT NULL UNIQUE,
  view_count INT DEFAULT 0,
  search_count INT DEFAULT 0,
  inquiry_count INT DEFAULT 0,
  demand_score DECIMAL(8,2) DEFAULT 0,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS testimonials (
  id INT AUTO_INCREMENT PRIMARY KEY,
  client_name VARCHAR(120) NOT NULL,
  client_location VARCHAR(120) DEFAULT 'Surat',
  review_text TEXT NOT NULL,
  rating TINYINT DEFAULT 5,
  is_active TINYINT(1) DEFAULT 1,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS review_comments (
  id INT AUTO_INCREMENT PRIMARY KEY,
  testimonial_id INT NOT NULL,
  commenter_name VARCHAR(140) NOT NULL,
  commenter_email VARCHAR(180),
  comment_text TEXT NOT NULL,
  is_active TINYINT(1) DEFAULT 1,
  admin_id INT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_review_comments_testimonial (testimonial_id),
  FOREIGN KEY (testimonial_id) REFERENCES testimonials(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS seller_profiles (
  id INT AUTO_INCREMENT PRIMARY KEY,
  full_name VARCHAR(180) NOT NULL,
  mobile VARCHAR(40) NOT NULL,
  email VARCHAR(180),
  address TEXT,
  tags_text VARCHAR(600),
  notes TEXT,
  created_by_admin_id INT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_seller_profiles_mobile (mobile),
  INDEX idx_seller_profiles_created_at (created_at)
);

CREATE TABLE IF NOT EXISTS customer_visits (
  id INT AUTO_INCREMENT PRIMARY KEY,
  visit_date DATE NOT NULL,
  client_name VARCHAR(180) NOT NULL,
  client_address TEXT,
  client_contact VARCHAR(60) NOT NULL,
  client_requirement TEXT,
  property_id INT NULL,
  executive_admin_id INT NULL,
  executive_name VARCHAR(180),
  executive_address TEXT,
  executive_contact VARCHAR(60),
  customer_signature_label VARCHAR(180),
  executive_signature_label VARCHAR(180),
  customer_signature_data LONGTEXT,
  executive_signature_data LONGTEXT,
  created_by_admin_id INT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_customer_visits_visit_date (visit_date),
  INDEX idx_customer_visits_property_id (property_id),
  INDEX idx_customer_visits_executive_admin_id (executive_admin_id),
  FOREIGN KEY (property_id) REFERENCES properties(id) ON DELETE SET NULL,
  FOREIGN KEY (executive_admin_id) REFERENCES admins(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS activity_logs (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  admin_id INT NULL,
  action_key VARCHAR(120) NOT NULL,
  action_label VARCHAR(220) NOT NULL,
  entity_type VARCHAR(120) NULL,
  entity_id INT NULL,
  meta_json LONGTEXT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_activity_logs_created_at (created_at),
  INDEX idx_activity_logs_action_key (action_key),
  INDEX idx_activity_logs_admin_id (admin_id),
  FOREIGN KEY (admin_id) REFERENCES admins(id) ON DELETE SET NULL
);

-- Sample Surat areas
INSERT INTO area_demand (area_name, demand_score) VALUES
('Adajan', 85), ('Vesu', 90), ('Pal', 75), ('Piplod', 88),
('Varachha', 70), ('Katargam', 65), ('City Light', 82), ('Althan', 78),
('Dumas', 80), ('Hazira', 60), ('Nanachhipwad', 72), ('Ambaji Road', 74)
ON DUPLICATE KEY UPDATE area_name=area_name;

INSERT INTO testimonials (client_name, client_location, review_text, rating) VALUES
('Rajesh Patel', 'Adajan, Surat', 'Jakkash Property helped us find our dream 3BHK. Professional and transparent service.', 5),
('Priya Shah', 'Vesu, Surat', 'Tirth bhai gave honest advice on pricing. Highly recommend for Surat properties.', 5),
('Amit Desai', 'Piplod, Surat', 'Quick site visits and excellent follow-up. Our shop deal closed smoothly.', 5);

-- Sample properties (Surat coordinates)
INSERT INTO properties (property_name, slug, property_type, area_name, address, price, bhk, sq_ft, description, amenities, latitude, longitude, status, is_featured, listing_type) VALUES
('Premium 3BHK Flat - Vesu', 'premium-3bhk-flat-vesu', 'flat', 'Vesu', 'Vesu Main Road, Surat', 8500000, 3, 1450, 'Spacious 3BHK with modular kitchen and covered parking near VR Mall.', '["parking","lift","security","gym"]', 21.1415000, 72.7758000, 'available', 1, 'sale'),
('Commercial Shop - Adajan', 'commercial-shop-adajan', 'shop', 'Adajan', 'Adajan Patiya, Surat', 4500000, 0, 450, 'Prime commercial shop on main road with high footfall.', '["parking","power_backup"]', 21.1956000, 72.7934000, 'available', 1, 'sale'),
('Office Space - Piplod', 'office-space-piplod', 'office', 'Piplod', 'Piplod, Surat', 120000, 0, 1200, 'Furnished office in commercial complex. Ideal for IT/consultancy.', '["lift","security","cafeteria"]', 21.1608000, 72.7712000, 'available', 0, 'rent'),
('Luxury Bungalow - Dumas', 'luxury-bungalow-dumas', 'bungalow', 'Dumas', 'Dumas Road, Surat', 25000000, 4, 3500, '4BHK bungalow with garden and private terrace near beach road.', '["garden","parking","security","swimming_pool"]', 21.0892000, 72.8145000, 'available', 1, 'sale'),
('Residential Plot - Pal', 'residential-plot-pal', 'plot', 'Pal', 'Pal Area, Surat', 3200000, 0, 1800, 'Clear title plot in developing area. Ready for construction.', '["gated","water","electricity"]', 21.2053000, 72.8987000, 'available', 0, 'sale'),
('2BHK Flat - Varachha', '2bhk-flat-varachha', 'flat', 'Varachha', 'Varachha Road, Surat', 4200000, 2, 980, 'Affordable 2BHK near ring road. Great for first-time buyers.', '["lift","security"]', 21.2315000, 72.8543000, 'available', 0, 'sale')
ON DUPLICATE KEY UPDATE property_name=property_name;
