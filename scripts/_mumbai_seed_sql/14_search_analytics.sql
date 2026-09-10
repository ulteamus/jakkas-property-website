-- search_analytics: 3 rows
DELETE FROM search_analytics;
INSERT INTO search_analytics (id, area_name, property_type, min_budget, max_budget, bhk, session_id, created_at) VALUES (1, NULL, NULL, NULL, NULL, NULL, 'ccc24316-d38a-4aa0-b013-f9c568c38707', '2026-08-30T18:40:30.925499+00:00');
INSERT INTO search_analytics (id, area_name, property_type, min_budget, max_budget, bhk, session_id, created_at) VALUES (2, NULL, NULL, NULL, NULL, NULL, 'fcc7e9e6-db51-46a1-ac29-50dfad59ccf0', '2026-08-30T18:46:47.878229+00:00');
INSERT INTO search_analytics (id, area_name, property_type, min_budget, max_budget, bhk, session_id, created_at) VALUES (3, NULL, NULL, NULL, NULL, NULL, '27a23be5-17a7-4a96-801a-e97b096626bc', '2026-08-30T18:51:22.870993+00:00');
SELECT setval(pg_get_serial_sequence('search_analytics', 'id'), COALESCE((SELECT MAX(id) FROM search_analytics), 1));
