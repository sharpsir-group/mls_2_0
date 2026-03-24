WITH table_counts AS (
SELECT 'properties' as table_name, COUNT(*) as total_rows FROM __CATALOG__.qobrix_bronze.properties UNION ALL
SELECT 'agents', COUNT(*) FROM __CATALOG__.qobrix_bronze.agents UNION ALL
SELECT 'contacts', COUNT(*) FROM __CATALOG__.qobrix_bronze.contacts UNION ALL
SELECT 'property_viewings', COUNT(*) FROM __CATALOG__.qobrix_bronze.property_viewings UNION ALL
SELECT 'property_media', COUNT(*) FROM __CATALOG__.qobrix_bronze.property_media UNION ALL
SELECT 'opportunities', COUNT(*) FROM __CATALOG__.qobrix_bronze.opportunities UNION ALL
SELECT 'users', COUNT(*) FROM __CATALOG__.qobrix_bronze.users UNION ALL
SELECT 'projects', COUNT(*) FROM __CATALOG__.qobrix_bronze.projects UNION ALL
SELECT 'project_features', COUNT(*) FROM __CATALOG__.qobrix_bronze.project_features UNION ALL
SELECT 'property_types', COUNT(*) FROM __CATALOG__.qobrix_bronze.property_types UNION ALL
SELECT 'property_subtypes', COUNT(*) FROM __CATALOG__.qobrix_bronze.property_subtypes UNION ALL
SELECT 'locations', COUNT(*) FROM __CATALOG__.qobrix_bronze.locations UNION ALL
SELECT 'media_categories', COUNT(*) FROM __CATALOG__.qobrix_bronze.media_categories UNION ALL
SELECT 'bayut_locations', COUNT(*) FROM __CATALOG__.qobrix_bronze.bayut_locations UNION ALL
SELECT 'bazaraki_locations', COUNT(*) FROM __CATALOG__.qobrix_bronze.bazaraki_locations UNION ALL
SELECT 'spitogatos_locations', COUNT(*) FROM __CATALOG__.qobrix_bronze.spitogatos_locations UNION ALL
SELECT 'property_finder_ae_locations', COUNT(*) FROM __CATALOG__.qobrix_bronze.property_finder_ae_locations
),
cdc_changes AS (
SELECT entity_name, records_processed as cdc_changed
FROM __CATALOG__.qobrix_bronze.cdc_metadata m
WHERE sync_completed_at = (
  SELECT MAX(sync_completed_at) FROM __CATALOG__.qobrix_bronze.cdc_metadata WHERE entity_name = m.entity_name
)
)
SELECT t.table_name, t.total_rows, COALESCE(c.cdc_changed, 0) as cdc_changed
FROM table_counts t
LEFT JOIN cdc_changes c ON t.table_name = c.entity_name
ORDER BY CASE t.table_name
  WHEN 'properties' THEN 1 WHEN 'agents' THEN 2 WHEN 'contacts' THEN 3
  WHEN 'property_viewings' THEN 4 WHEN 'property_media' THEN 5 WHEN 'opportunities' THEN 6
  WHEN 'users' THEN 7 WHEN 'projects' THEN 8 ELSE 99 END
