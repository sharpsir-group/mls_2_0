#!/usr/bin/env python
# Databricks notebook source
# MLS 2.0 - Create empty gold tables for contact audit and segments (app-managed; no Qobrix source).
# common_contact_profile_changelog, common_contact_segments, common_contact_profile_segments

# COMMAND ----------

spark.sql("USE CATALOG sharp")
spark.sql("CREATE SCHEMA IF NOT EXISTS common")

# common_contact_profile_changelog: audit trail per contact profile (app or future API)
spark.sql(
    """
CREATE TABLE IF NOT EXISTS common.common_contact_profile_changelog (
    id STRING,
    changed_at TIMESTAMP NOT NULL,
    changed_by_user_id STRING,
    event_type STRING,
    field_name STRING,
    old_value STRING,
    new_value STRING,
    source_system STRING
)
"""
)
print("✅ common.common_contact_profile_changelog: created (empty; app-managed)")

# common_contact_segments: segment definitions (e.g. Newsletter, VIP)
spark.sql(
    """
CREATE TABLE IF NOT EXISTS common.common_contact_segments (
    id STRING,
    name STRING NOT NULL,
    description STRING,
    created_at TIMESTAMP NOT NULL
)
"""
)
print("✅ common.common_contact_segments: created (empty; app-managed)")

# common_contact_profile_segments: junction contact_profile <-> segment
spark.sql(
    """
CREATE TABLE IF NOT EXISTS common.common_contact_profile_segments (
    contact_profile_id STRING NOT NULL,
    segment_id STRING NOT NULL,
    added_at TIMESTAMP NOT NULL
)
"""
)
print("✅ common.common_contact_profile_segments: created (empty; app-managed)")
