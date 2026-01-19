#!/bin/bash
# Copyright 2025 SharpSir Group
# Licensed under the Apache License, Version 2.0
# See LICENSE file for details.
# ============================================================
# Dash → RESO Web API Integrity Test
# Two-way verification: Dash JSON Source ↔ RESO API
# Only processes HSIR_Listings_readable.json (ignores old files)
# ============================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MLS2_ROOT="$(dirname "$SCRIPT_DIR")"

# Load environment
if [ -f "$MLS2_ROOT/.env" ]; then
    export $(grep -v '^#' "$MLS2_ROOT/.env" | xargs)
fi

RESO_API="${RESO_API_URL:-http://localhost:3900}"
# Use new SRC_2 format (Hungary = DASH_JSON)
DASH_SOURCE_DIR="${SRC_2_DIR:-${DASH_SOURCE_DIR:-$MLS2_ROOT/dash_hsir_source}}"
DASH_OFFICE_KEY="${SRC_2_OFFICE_KEY:-SHARPSIR-HU-001}"

echo "=============================================="
echo "  Dash → RESO API Two-Way Integrity Test"
echo "=============================================="
echo ""
echo "Dash Source: $DASH_SOURCE_DIR"
echo "RESO API:    $RESO_API"
echo "Office Key:  $DASH_OFFICE_KEY (Hungary)"
echo ""

# Python script for comprehensive testing
python3 << 'PYTHON_SCRIPT'
import os
import sys
import json
import glob
from pathlib import Path

# Try httpx first, fall back to requests
try:
    import httpx
    HTTP_CLIENT = 'httpx'
except ImportError:
    import requests as httpx
    HTTP_CLIENT = 'requests'

RESO_API = os.environ.get('RESO_API_URL', 'http://localhost:3900')
DASH_SOURCE_DIR = os.environ.get('SRC_2_DIR', os.environ.get('DASH_SOURCE_DIR', ''))
DASH_OFFICE_KEY = os.environ.get('SRC_2_OFFICE_KEY', 'SHARPSIR-HU-001')
# Use Hungary client credentials for Dash data
OAUTH_CLIENT_ID = os.environ.get('OAUTH_CLIENT_2_ID', '')
OAUTH_CLIENT_SECRET = os.environ.get('OAUTH_CLIENT_2_SECRET', '')

# OAuth token cache
_oauth_token = None

def get_oauth_token():
    """Get OAuth token for RESO API (Hungary client)"""
    global _oauth_token
    if _oauth_token:
        return _oauth_token
    
    if not OAUTH_CLIENT_ID or not OAUTH_CLIENT_SECRET:
        print("⚠️  Warning: No OAUTH_CLIENT_2 credentials found")
        return None
    
    if HTTP_CLIENT == 'httpx':
        resp = httpx.post(
            f"{RESO_API}/oauth/token",
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            data=f'grant_type=client_credentials&client_id={OAUTH_CLIENT_ID}&client_secret={OAUTH_CLIENT_SECRET}',
            timeout=30
        )
    else:
        resp = httpx.post(
            f"{RESO_API}/oauth/token",
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            data=f'grant_type=client_credentials&client_id={OAUTH_CLIENT_ID}&client_secret={OAUTH_CLIENT_SECRET}',
            timeout=30
        )
    
    if resp.status_code == 200:
        _oauth_token = resp.json().get('access_token')
    else:
        print(f"⚠️  OAuth failed: {resp.status_code} {resp.text[:100]}")
    return _oauth_token

def reso_get(endpoint):
    """GET from RESO API with OAuth"""
    headers = {}
    token = get_oauth_token()
    if token:
        headers['Authorization'] = f'Bearer {token}'
    
    if HTTP_CLIENT == 'httpx':
        resp = httpx.get(f"{RESO_API}{endpoint}", headers=headers, timeout=60)
    else:
        resp = httpx.get(f"{RESO_API}{endpoint}", headers=headers, timeout=60)
    return resp.json()

def load_dash_source():
    """Load only HSIR_Listings_readable.json (ignore old files)"""
    all_listings = []
    json_file = os.path.join(DASH_SOURCE_DIR, 'HSIR_Listings_readable.json')
    
    if not os.path.exists(json_file):
        print(f"  ❌ File not found: {json_file}")
        return all_listings
    
    with open(json_file, 'r') as f:
        data = json.load(f)
        # Handle both formats: direct list or dict with 'listings' key
        if isinstance(data, list):
            listings = data
        else:
            listings = data.get('listings', [])
        all_listings.extend(listings)
        print(f"  📁 {os.path.basename(json_file)}: {len(listings)} listings")
    
    return all_listings

print("Loading Dash source file...")
dash_listings = load_dash_source()
print(f"  Total: {len(dash_listings)} listings from source\n")

# Build lookup by listingGuid (takes last occurrence)
dash_by_guid = {l['listingGuid']: l for l in dash_listings}

# Build unique media count per listing (aggregates across all source files)
def get_unique_media_count(guid):
    """Get unique media count for a listing across all source files"""
    unique_media = set()
    for l in dash_listings:
        if l.get('listingGuid') == guid:
            for m in l.get('media', []):
                unique_media.add(m.get('mediaGuid'))
    return len(unique_media)

print("=" * 60)
print("TEST 1: Property Count Verification")
print("=" * 60)

# Source count (unique listings - same listing may appear in multiple files)
unique_listing_guids = set(l['listingGuid'] for l in dash_listings)
source_count = len(unique_listing_guids)

# RESO property count (filtered by office key)
reso_props = reso_get(f"/odata/Property?$count=true&$top=1&$filter=OriginatingSystemOfficeKey eq '{DASH_OFFICE_KEY}'")
reso_count = reso_props.get('@odata.count', len(reso_props.get('value', [])))

diff = abs(source_count - reso_count)
match = "✅" if diff == 0 else "⚠️" if diff <= 5 else "❌"
print(f"  {match} Properties: Source={source_count}  RESO={reso_count}  (diff={diff})")

count_issues = []
if diff > 5:
    count_issues.append(f"Property count: Source={source_count}, RESO={reso_count}, diff={diff}")

print("")
print("=" * 60)
print("TEST 2: Sample Property Data Verification")
print("=" * 60)

# Get 5 sample properties from RESO API
reso_sample = reso_get(f"/odata/Property?$top=5&$filter=OriginatingSystemOfficeKey eq '{DASH_OFFICE_KEY}'')
data_issues = []

for rprop in reso_sample.get('value', []):
    listing_key = rprop.get('ListingKey', '')
    
    # Extract GUID from ListingKey (format: DASH_<guid>)
    if not listing_key.startswith('DASH_'):
        print(f"  ⚠️  {listing_key[:40]}... Unexpected key format")
        continue
    
    guid = listing_key.replace('DASH_', '')
    
    # Find in source
    source_listing = dash_by_guid.get(guid)
    if not source_listing:
        print(f"  ❌ {listing_key[:40]}... NOT FOUND in source JSON")
        data_issues.append(f"{listing_key}: Not found in source")
        continue
    
    issues = []
    
    # Price comparison (source uses 'listPrice')
    s_price = source_listing.get('listPrice')
    r_price = rprop.get('ListPrice')
    if s_price and r_price:
        try:
            s_price_f = float(s_price) if s_price else None
            r_price_f = float(r_price) if r_price else None
            if s_price_f != r_price_f:
                issues.append(f"Price: S={s_price_f}, R={r_price_f}")
        except:
            pass
    
    # City comparison (source uses propertyDetails.location.city)
    location = source_listing.get('propertyDetails', {}).get('location', {})
    s_city = location.get('city', '')
    r_city = rprop.get('City')
    if s_city and r_city and s_city != r_city:
        issues.append(f"City: S={s_city}, R={r_city}")
    
    # Bedrooms comparison (source uses propertyDetails.noOfBedrooms)
    prop_details = source_listing.get('propertyDetails', {})
    s_beds = prop_details.get('noOfBedrooms')
    r_beds = rprop.get('BedroomsTotal')
    if s_beds and r_beds:
        try:
            s_beds_i = int(float(s_beds)) if s_beds else None
            r_beds_i = int(r_beds) if r_beds else None
            if s_beds_i != r_beds_i:
                issues.append(f"Beds: S={s_beds_i}, R={r_beds_i}")
        except:
            pass
    
    # Country comparison (source uses propertyDetails.location.countryCode)
    s_country = location.get('countryCode', '')
    r_country = rprop.get('Country')
    if s_country and r_country and s_country != r_country:
        issues.append(f"Country: S={s_country}, R={r_country}")
    
    if issues:
        print(f"  ❌ {listing_key[:40]}...")
        for i in issues:
            print(f"     {i}")
            data_issues.append(f"{listing_key}: {i}")
    else:
        print(f"  ✅ {listing_key[:40]}... Price={r_price}, City={r_city}")

print("")
print("=" * 60)
print("TEST 3: Media Count Verification")
print("=" * 60)

media_issues = []

for rprop in reso_sample.get('value', [])[:5]:
    listing_key = rprop.get('ListingKey', '')
    guid = listing_key.replace('DASH_', '')
    
    source_listing = dash_by_guid.get(guid)
    if not source_listing:
        continue
    
    # Count UNIQUE media in source (across all files for this listing)
    source_media_count = get_unique_media_count(guid)
    
    # Count media in RESO API
    reso_media = reso_get(f"/odata/Media?$filter=ResourceRecordKey eq '{listing_key}'&$count=true")
    reso_media_count = reso_media.get('@odata.count', len(reso_media.get('value', [])))
    
    diff = abs(source_media_count - reso_media_count)
    match = "✅" if diff == 0 else "⚠️" if diff <= 2 else "❌"
    
    if diff > 2:
        media_issues.append(f"{listing_key}: Source={source_media_count}, RESO={reso_media_count}")
    
    print(f"  {match} {listing_key[:40]}... Source={source_media_count}, RESO={reso_media_count}")

print("")
print("=" * 60)
print("TEST 4: Features Mapping Verification")
print("=" * 60)

# Get a property with features from RESO
reso_with_features = reso_get(f"/odata/Property?$top=3&$filter=OriginatingSystemOfficeKey eq '{DASH_OFFICE_KEY}' and View ne null&$select=ListingKey,View,Flooring,Cooling,Heating,PoolFeatures,ParkingFeatures')
feature_issues = []

for rprop in reso_with_features.get('value', []):
    listing_key = rprop.get('ListingKey', '')
    guid = listing_key.replace('DASH_', '')
    
    source_listing = dash_by_guid.get(guid)
    if not source_listing:
        continue
    
    # Get source features
    source_features = source_listing.get('features', [])
    source_feature_groups = {}
    for f in source_features:
        group = f.get('featureGroupDescription', '')
        desc = f.get('featureDescription', '')
        if group not in source_feature_groups:
            source_feature_groups[group] = []
        source_feature_groups[group].append(desc)
    
    # Check RESO feature fields
    issues = []
    
    # View
    r_view = rprop.get('View')
    s_views = source_feature_groups.get('Views', [])
    if r_view and s_views:
        for sv in s_views:
            if sv not in r_view:
                issues.append(f"View missing: {sv}")
                break
    
    # Flooring
    r_flooring = rprop.get('Flooring')
    s_flooring = source_feature_groups.get('Flooring', [])
    if r_flooring and s_flooring:
        for sf in s_flooring:
            if sf not in r_flooring:
                issues.append(f"Flooring missing: {sf}")
                break
    
    if issues:
        print(f"  ⚠️  {listing_key[:40]}...")
        for i in issues[:2]:
            print(f"     {i}")
            feature_issues.append(f"{listing_key}: {i}")
    else:
        print(f"  ✅ {listing_key[:40]}... View={r_view[:30] if r_view else 'N/A'}...")

print("")
print("=" * 60)
print("TEST 5: Agent/Office Data Verification")
print("=" * 60)

agent_issues = []

# Get properties with agent data
reso_with_agent = reso_get(f"/odata/Property?$top=3&$filter=OriginatingSystemOfficeKey eq '{DASH_OFFICE_KEY}' and ListAgentKey ne null&$select=ListingKey,ListAgentKey,ListOfficeKey,PublicRemarks')

for rprop in reso_with_agent.get('value', []):
    listing_key = rprop.get('ListingKey', '')
    guid = listing_key.replace('DASH_', '')
    
    source_listing = dash_by_guid.get(guid)
    if not source_listing:
        continue
    
    # Check agent mapping
    primary_agent = source_listing.get('primaryAgent', {})
    s_agent_id = primary_agent.get('personGuid')
    r_agent_key = rprop.get('ListAgentKey', '')
    
    issues = []
    
    if s_agent_id and r_agent_key:
        expected_key = f"DASH_AGENT_{s_agent_id}"
        if r_agent_key != expected_key:
            issues.append(f"AgentKey: expected {expected_key[:30]}..., got {r_agent_key[:30]}...")
    
    if issues:
        print(f"  ⚠️  {listing_key[:40]}...")
        for i in issues:
            print(f"     {i}")
            agent_issues.append(f"{listing_key}: {i}")
    else:
        print(f"  ✅ {listing_key[:40]}... Agent={r_agent_key[:30] if r_agent_key else 'N/A'}...")

print("")
print("=" * 60)
print("TEST 6: Data Source & Office Key Verification")
print("=" * 60)

# Verify all properties have correct X_DataSource
reso_check = reso_get(f"/odata/Property?$top=100&$filter=OriginatingSystemOfficeKey eq '{DASH_OFFICE_KEY}'&$select=ListingKey,OriginatingSystemOfficeKey,X_DataSource')
source_issues = []

correct_source = 0
wrong_source = 0

for rprop in reso_check.get('value', []):
    office_key = rprop.get('OriginatingSystemOfficeKey')
    data_source = rprop.get('X_DataSource')
    
    if office_key == DASH_OFFICE_KEY and data_source == 'dash_sothebys':
        correct_source += 1
    else:
        wrong_source += 1
        source_issues.append(f"{rprop.get('ListingKey')}: OfficeKey={office_key}, DataSource={data_source}")

match = "✅" if wrong_source == 0 else "❌"
print(f"  {match} Correct ({DASH_OFFICE_KEY} + DASH_JSON): {correct_source}")
if wrong_source > 0:
    print(f"  ❌ Incorrect: {wrong_source}")
    for i in source_issues[:3]:
        print(f"     {i}")

print("")
print("=" * 60)
print("TEST 7: RESO Type Compliance")
print("=" * 60)

# Get one property and check types
r_sample = reso_get(f"/odata/Property?$top=1&$filter=OriginatingSystemOfficeKey eq '{DASH_OFFICE_KEY}'')
if r_sample.get('value'):
    rprop = r_sample['value'][0]
    
    type_checks = [
        ('ListPrice', (int, float, type(None)), rprop.get('ListPrice')),
        ('BedroomsTotal', (int, type(None)), rprop.get('BedroomsTotal')),
        ('BathroomsTotalInteger', (int, type(None)), rprop.get('BathroomsTotalInteger')),
        ('YearBuilt', (int, type(None)), rprop.get('YearBuilt')),
        ('Latitude', (int, float, type(None)), rprop.get('Latitude')),
        ('Longitude', (int, float, type(None)), rprop.get('Longitude')),
        ('LivingArea', (int, float, type(None)), rprop.get('LivingArea')),
        ('City', (str, type(None)), rprop.get('City')),
        ('ListingKey', (str,), rprop.get('ListingKey')),
        ('View', (str, type(None)), rprop.get('View')),
    ]
    
    type_issues = []
    for field, expected_types, value in type_checks:
        actual_type = type(value)
        ok = actual_type in expected_types
        if not ok:
            type_issues.append(f"{field}: expected {expected_types}, got {actual_type}")
        status = "✅" if ok else "❌"
        print(f"  {status} {field:<25} {actual_type.__name__:<10} = {str(value)[:25]}")
else:
    type_issues = ['No properties found']
    print("  ⚠️  No properties found to test")

print("")
print("=" * 60)
print("TEST 8: Media URL & Dimensions")
print("=" * 60)

# Check media URLs and dimensions
media_data = reso_get("/odata/Media?$top=5&$filter=OriginatingSystemOfficeKey eq '{DASH_OFFICE_KEY}'&$select=MediaKey,MediaURL,ImageWidth,ImageHeight")
url_issues = []

for media in media_data.get('value', []):
    url = media.get('MediaURL', '')
    width = media.get('ImageWidth')
    height = media.get('ImageHeight')
    
    issues = []
    if url and not url.startswith('http'):
        issues.append("URL not absolute")
        url_issues.append(f"{media['MediaKey']}: URL not absolute")
    
    # Check dimensions exist
    has_dims = width is not None and height is not None
    
    if issues:
        print(f"  ❌ {media['MediaKey'][:35]}... {', '.join(issues)}")
    else:
        dims = f"{width}x{height}" if has_dims else "no dims"
        print(f"  ✅ {media['MediaKey'][:35]}... {dims}")

print("")
print("=" * 60)
print("TEST 9: Agent & Geolocation Completeness")
print("=" * 60)

agent_geo_issues = []

total_listings = len(dash_listings)
with_agent_guid = 0
with_agent_name = 0
with_agent_email = 0
with_geolocation = 0
with_both = 0

for listing in dash_listings:
    # Check agent completeness
    agent = listing.get('primaryAgent', {})
    has_agent_guid = bool(agent.get('personGuid'))
    has_agent_name = bool(agent.get('firstName') or agent.get('lastName'))
    has_agent_email = bool(agent.get('primaryEmailAddress') or agent.get('vanityEmailAddress'))
    
    # Check geolocation
    location = listing.get('propertyDetails', {}).get('location', {})
    lat = location.get('latitude')
    lon = location.get('longitude')
    has_geolocation = False
    
    if lat is not None and lon is not None:
        try:
            lat_f = float(lat)
            lon_f = float(lon)
            if -90 <= lat_f <= 90 and -180 <= lon_f <= 180 and (lat_f != 0 or lon_f != 0):
                has_geolocation = True
        except (ValueError, TypeError):
            pass
    
    # Count completions
    if has_agent_guid:
        with_agent_guid += 1
    if has_agent_name:
        with_agent_name += 1
    if has_agent_email:
        with_agent_email += 1
    if has_geolocation:
        with_geolocation += 1
    if has_agent_guid and has_agent_name and has_agent_email and has_geolocation:
        with_both += 1
    
    # Track issues
    listing_guid = listing.get('listingGuid', 'UNKNOWN')
    issues = []
    if not has_agent_guid:
        issues.append("missing agent GUID")
    if not has_agent_name:
        issues.append("missing agent name")
    if not has_agent_email:
        issues.append("missing agent email")
    if not has_geolocation:
        issues.append("missing/invalid geolocation")
    
    if issues:
        agent_geo_issues.append(f"{listing_guid}: {', '.join(issues)}")

# Print summary
print(f"  Total listings: {total_listings}")
print(f"  With agent GUID: {with_agent_guid} ({with_agent_guid*100/total_listings:.1f}%)")
print(f"  With agent name: {with_agent_name} ({with_agent_name*100/total_listings:.1f}%)")
print(f"  With agent email: {with_agent_email} ({with_agent_email*100/total_listings:.1f}%)")
print(f"  With geolocation: {with_geolocation} ({with_geolocation*100/total_listings:.1f}%)")
print(f"  Complete (agent + geo): {with_both} ({with_both*100/total_listings:.1f}%)")

if agent_geo_issues:
    print(f"  ⚠️  {len(agent_geo_issues)} listings with issues:")
    for issue in agent_geo_issues[:5]:
        print(f"     {issue}")
    if len(agent_geo_issues) > 5:
        print(f"     ... and {len(agent_geo_issues) - 5} more")
else:
    print(f"  ✅ All listings have complete agent and geolocation data")

print("")
print("  Checking RESO API data...")
# Verify in RESO API
reso_all_props = reso_get(f"/odata/Property?$filter=OriginatingSystemOfficeKey eq '{DASH_OFFICE_KEY}'&$select=ListingKey,ListAgentKey,Latitude,Longitude')
reso_props_list = reso_all_props.get('value', [])

reso_with_agent = 0
reso_with_geo = 0
reso_complete = 0
reso_issues = []

for rprop in reso_props_list:
    listing_key = rprop.get('ListingKey', '')
    has_agent = bool(rprop.get('ListAgentKey'))
    lat = rprop.get('Latitude')
    lon = rprop.get('Longitude')
    has_geo = False
    
    if lat is not None and lon is not None:
        try:
            lat_f = float(lat)
            lon_f = float(lon)
            if -90 <= lat_f <= 90 and -180 <= lon_f <= 180 and (lat_f != 0 or lon_f != 0):
                has_geo = True
        except (ValueError, TypeError):
            pass
    
    if has_agent:
        reso_with_agent += 1
    if has_geo:
        reso_with_geo += 1
    if has_agent and has_geo:
        reso_complete += 1
    
    if not has_agent or not has_geo:
        issues = []
        if not has_agent:
            issues.append("missing agent")
        if not has_geo:
            issues.append("missing geolocation")
        reso_issues.append(f"{listing_key[:40]}...: {', '.join(issues)}")

reso_total = len(reso_props_list)
print(f"  RESO API - Total listings: {reso_total}")
print(f"  RESO API - With agent: {reso_with_agent} ({reso_with_agent*100/reso_total:.1f}%)" if reso_total > 0 else "  RESO API - With agent: 0")
print(f"  RESO API - With geolocation: {reso_with_geo} ({reso_with_geo*100/reso_total:.1f}%)" if reso_total > 0 else "  RESO API - With geolocation: 0")
print(f"  RESO API - Complete (agent + geo): {reso_complete} ({reso_complete*100/reso_total:.1f}%)" if reso_total > 0 else "  RESO API - Complete: 0")

if reso_issues:
    print(f"  ⚠️  {len(reso_issues)} RESO listings with issues:")
    for issue in reso_issues[:5]:
        print(f"     {issue}")
    if len(reso_issues) > 5:
        print(f"     ... and {len(reso_issues) - 5} more")
    agent_geo_issues.extend([f"RESO: {i}" for i in reso_issues])
else:
    print(f"  ✅ All RESO API listings have complete agent and geolocation data")

print("")
print("=" * 60)
print("SUMMARY")
print("=" * 60)

total_issues = len(count_issues) + len(data_issues) + len(media_issues) + len(feature_issues) + len(agent_issues) + len(source_issues) + len(type_issues) + len(url_issues) + len(agent_geo_issues)

print(f"  Property Count:         {'✅ PASS' if not count_issues else '❌ FAIL (' + str(len(count_issues)) + ')'}")
print(f"  Property Data:          {'✅ PASS' if not data_issues else '❌ FAIL (' + str(len(data_issues)) + ')'}")
print(f"  Media Count:            {'✅ PASS' if not media_issues else '❌ FAIL (' + str(len(media_issues)) + ')'}")
print(f"  Features Mapping:       {'✅ PASS' if not feature_issues else '⚠️  WARN (' + str(len(feature_issues)) + ')'}")
print(f"  Agent/Office Data:      {'✅ PASS' if not agent_issues else '⚠️  WARN (' + str(len(agent_issues)) + ')'}")
print(f"  Data Source Tags:       {'✅ PASS' if not source_issues else '❌ FAIL (' + str(len(source_issues)) + ')'}")
print(f"  RESO Type Compliance:   {'✅ PASS' if not type_issues else '❌ FAIL (' + str(len(type_issues)) + ')'}")
print(f"  Media URL/Dimensions:   {'✅ PASS' if not url_issues else '❌ FAIL (' + str(len(url_issues)) + ')'}")
print(f"  Agent/Geo Completeness: {'✅ PASS' if not agent_geo_issues else '❌ FAIL (' + str(len(agent_geo_issues)) + ')'}")
print("")

if total_issues == 0:
    print("🎉 ALL DASH INTEGRITY TESTS PASSED!")
    print("   Dash JSON source data matches RESO API data")
    sys.exit(0)
else:
    print(f"⚠️  {total_issues} issues found")
    sys.exit(1)

PYTHON_SCRIPT

