-- MLS 2.0 — bootstrap Unity Catalog namespace (isolated from legacy `mls2`).
-- Run in Databricks SQL Warehouse or notebook as Metastore Admin / account admin.
-- Some workspaces require creating the catalog in the Account Console first; if
-- `CREATE CATALOG` fails here, create `mls_2_0` there, then run the SCHEMA section.

CREATE CATALOG IF NOT EXISTS mls_2_0
COMMENT 'MLS 2.0 datamart: Qobrix/Dash → bronze/silver → RESO gold';

CREATE SCHEMA IF NOT EXISTS mls_2_0.qobrix_bronze
COMMENT 'Raw Qobrix API (Delta)';
CREATE SCHEMA IF NOT EXISTS mls_2_0.qobrix_silver
COMMENT 'Normalized Qobrix';
CREATE SCHEMA IF NOT EXISTS mls_2_0.reso_gold
COMMENT 'RESO Data Dictionary gold';
CREATE SCHEMA IF NOT EXISTS mls_2_0.exports
COMMENT 'Portal exports (e.g. HomeOverseas)';
CREATE SCHEMA IF NOT EXISTS mls_2_0.dash_bronze
COMMENT 'Dash/HU (and related) bronze — optional';
CREATE SCHEMA IF NOT EXISTS mls_2_0.dash_silver
COMMENT 'Dash silver — optional';

-- Grants (uncomment and substitute your group or service principal):
-- GRANT USE CATALOG ON CATALOG mls_2_0 TO `data-engineering`;
-- GRANT USE SCHEMA ON SCHEMA mls_2_0.qobrix_bronze TO `data-engineering`;
-- GRANT ALL PRIVILEGES ON SCHEMA mls_2_0.qobrix_bronze TO `data-engineering`;
-- Repeat for qobrix_silver, reso_gold, exports, dash_bronze, dash_silver as needed.
