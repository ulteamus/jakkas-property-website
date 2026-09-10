-- testimonials: 4 rows
DELETE FROM testimonials;
INSERT INTO testimonials (id, client_name, client_location, review_text, rating, is_active, created_at) VALUES (1, 'Rajesh Patel', 'Adajan, Surat', 'Jakkash Property helped us find our dream 3BHK. Professional and transparent service.', 5, TRUE, '2026-08-29T06:06:05+00:00');
INSERT INTO testimonials (id, client_name, client_location, review_text, rating, is_active, created_at) VALUES (2, 'Priya Shah', 'Vesu, Surat', 'Tirth bhai gave honest advice on pricing. Highly recommend for Surat properties.', 5, TRUE, '2026-08-29T06:06:05+00:00');
INSERT INTO testimonials (id, client_name, client_location, review_text, rating, is_active, created_at) VALUES (3, 'Amit Desai', 'Piplod, Surat', 'Quick site visits and excellent follow-up. Our shop deal closed smoothly.', 5, TRUE, '2026-08-29T06:06:05+00:00');
INSERT INTO testimonials (id, client_name, client_location, review_text, rating, is_active, created_at) VALUES (4, 'Cloud Reviewer', 'Surat', 'Cloud review persistence 907492123c', 5, TRUE, '2026-08-30T18:51:30.176179+00:00');
SELECT setval(pg_get_serial_sequence('testimonials', 'id'), COALESCE((SELECT MAX(id) FROM testimonials), 1));
