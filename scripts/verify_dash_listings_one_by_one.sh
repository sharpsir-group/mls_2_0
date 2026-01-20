#!/bin/bash
# Copyright 2025 SharpSir Group
# Licensed under the Apache License, Version 2.0
# See LICENSE file for details.
# ============================================================
# Dash → RESO Web API One-by-One Verification
# Tests each listing individually: JSON Source ↔ RESO API
# ============================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MLS2_ROOT="$(dirname "$SCRIPT_DIR")"

# Load environment
if [ -f "$MLS2_ROOT/.env" ]; then
    export $(grep -v '^#' "$MLS2_ROOT/.env" | xargs)
fi

RESO_API="${RESO_API_URL:-http://localhost:3900}"
# Use new SRC_2 format (Hungary = DASH_FILE)
DASH_SOURCE_DIR="${SRC_2_DIR:-${DASH_SOURCE_DIR:-$MLS2_ROOT/dash_hsir_source}}"
DASH_OFFICE_KEY="${SRC_2_OFFICE_KEY:-SHARPSIR-HU-001}"

echo "=============================================="
echo "  Dash → RESO API One-by-One Verification"
echo "=============================================="
echo ""
echo "Dash Source: $DASH_SOURCE_DIR"
echo "RESO API:    $RESO_API"
echo "Office Key:  $DASH_OFFICE_KEY (Hungary)"
echo ""

# Python script for one-by-one testing
python3 << 'PYTHON_SCRIPT'
import os
import sys
import json
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
    
    if resp.status_code != 200:
        return None
    return resp.json()

def load_dash_source():
    """Load listing JSON file from source directory"""
    # Try HSIR_Listings_readable.json first, then any .json file
    json_file = os.path.join(DASH_SOURCE_DIR, 'HSIR_Listings_readable.json')
    if not os.path.exists(json_file):
        # Find any JSON file
        import glob
        json_files = glob.glob(os.path.join(DASH_SOURCE_DIR, '*.json'))
        json_file = json_files[0] if json_files else json_file
    
    if not os.path.exists(json_file):
        print(f"  ❌ File not found: {json_file}")
        return []
    
    with open(json_file, 'r') as f:
        data = json.load(f)
        if isinstance(data, list):
            listings = data
        else:
            listings = data.get('listings', [])
    
    return listings

print("Loading Dash source file...")
dash_listings = load_dash_source()
print(f"  ✅ Loaded {len(dash_listings)} listings\n")

if not dash_listings:
    print("❌ No listings found")
    sys.exit(1)

print("=" * 80)
print("Testing each listing one by one...")
print("=" * 80)
print()

total = len(dash_listings)
passed = 0
failed = 0
warnings = 0
issues = []

for idx, listing in enumerate(dash_listings, 1):
    listing_guid = listing.get('listingGuid', 'UNKNOWN')
    listing_key = f"DASH_{listing_guid}"
    
    print(f"[{idx}/{total}] Testing: {listing_key[:50]}...")
    
    # Get from RESO API
    reso_prop = reso_get(f'/odata/Property?$filter=ListingKey eq \'{listing_key}\'&$top=1')
    
    if not reso_prop or not reso_prop.get('value'):
        print(f"  ❌ NOT FOUND in RESO API")
        failed += 1
        issues.append(f"{listing_key}: Not found in RESO API")
        print()
        continue
    
    rprop = reso_prop['value'][0]
    listing_issues = []
    
    # Check 1: Price
    s_price = listing.get('listPrice')
    r_price = rprop.get('ListPrice')
    if s_price and r_price:
        try:
            s_price_f = float(s_price) if s_price else None
            r_price_f = float(r_price) if r_price else None
            if abs(s_price_f - r_price_f) > 0.01:  # Allow small floating point differences
                listing_issues.append(f"Price mismatch: {s_price_f} vs {r_price_f}")
        except:
            pass
    
    # Check 2: City
    location = listing.get('propertyDetails', {}).get('location', {})
    s_city = location.get('city', '')
    r_city = rprop.get('City')
    if s_city and r_city and s_city != r_city:
        listing_issues.append(f"City mismatch: '{s_city}' vs '{r_city}'")
    
    # Check 3: Bedrooms
    prop_details = listing.get('propertyDetails', {})
    s_beds = prop_details.get('noOfBedrooms')
    r_beds = rprop.get('BedroomsTotal')
    if s_beds is not None and r_beds is not None:
        try:
            s_beds_i = int(float(s_beds)) if s_beds else None
            r_beds_i = int(r_beds) if r_beds else None
            if s_beds_i != r_beds_i:
                listing_issues.append(f"Bedrooms mismatch: {s_beds_i} vs {r_beds_i}")
        except:
            pass
    
    # Check 4: Country
    s_country = location.get('countryCode', '')
    r_country = rprop.get('Country')
    if s_country and r_country and s_country != r_country:
        listing_issues.append(f"Country mismatch: '{s_country}' vs '{r_country}'")
    
    # Check 5: Agent
    primary_agent = listing.get('primaryAgent', {})
    s_agent_id = primary_agent.get('personGuid')
    r_agent_key = rprop.get('ListAgentKey', '')
    if s_agent_id:
        expected_key = f"DASH_AGENT_{s_agent_id}"
        if r_agent_key != expected_key:
            listing_issues.append(f"AgentKey mismatch: expected '{expected_key[:30]}...', got '{r_agent_key[:30] if r_agent_key else 'NONE'}...'")
    
    # Check 6: Geolocation
    s_lat = location.get('latitude')
    s_lon = location.get('longitude')
    r_lat = rprop.get('Latitude')
    r_lon = rprop.get('Longitude')
    
    if s_lat is not None and s_lon is not None:
        try:
            s_lat_f = float(s_lat)
            s_lon_f = float(s_lon)
            if r_lat is not None and r_lon is not None:
                r_lat_f = float(r_lat)
                r_lon_f = float(r_lon)
                # Allow small differences (GPS precision)
                if abs(s_lat_f - r_lat_f) > 0.0001 or abs(s_lon_f - r_lon_f) > 0.0001:
                    listing_issues.append(f"Geolocation mismatch: ({s_lat_f}, {s_lon_f}) vs ({r_lat_f}, {r_lon_f})")
            else:
                listing_issues.append("Geolocation missing in RESO")
        except:
            pass
    elif r_lat is not None and r_lon is not None:
        listing_issues.append("Geolocation missing in source but present in RESO")
    
    # Check 7: Media count
    source_media = listing.get('media', [])
    source_media_count = len(source_media)
    reso_media = reso_get(f"/odata/Media?$filter=ResourceRecordKey eq '{listing_key}'&$count=true")
    reso_media_count = reso_media.get('@odata.count', len(reso_media.get('value', []))) if reso_media else 0
    
    if abs(source_media_count - reso_media_count) > 0:
        listing_issues.append(f"Media count mismatch: {source_media_count} vs {reso_media_count}")
    
    # Check 8: Status
    s_status = listing.get('statusCode', '')
    r_status = rprop.get('StandardStatus', '')
    if s_status and r_status:
        # Map Dash status to RESO status
        status_map = {
            'AC': 'Active',
            'AV': 'Active',  # Available -> Active (correct mapping)
            'SLD': 'Closed',
            'EXP': 'Expired',
            'WD': 'Withdrawn',
            'PS': 'Pending',
            'CL': 'Closed'
        }
        expected_reso = status_map.get(s_status, 'Active')  # Default to Active for unknown statuses
        if r_status != expected_reso:
            listing_issues.append(f"Status mapping issue: '{s_status}' -> '{r_status}' (expected '{expected_reso}')")
    
    # Print result
    if listing_issues:
        print(f"  ⚠️  {len(listing_issues)} issue(s):")
        for issue in listing_issues:
            print(f"     - {issue}")
        warnings += 1
        issues.append(f"{listing_key}: {'; '.join(listing_issues)}")
    else:
        print(f"  ✅ All checks passed")
        passed += 1
    
    print()

print("=" * 80)
print("SUMMARY")
print("=" * 80)
print(f"  Total listings tested: {total}")
print(f"  ✅ Passed: {passed} ({passed*100/total:.1f}%)")
print(f"  ⚠️  Warnings: {warnings} ({warnings*100/total:.1f}%)")
print(f"  ❌ Failed: {failed} ({failed*100/total:.1f}%)")
print()

if issues:
    print("Issues found:")
    for issue in issues[:10]:
        print(f"  - {issue}")
    if len(issues) > 10:
        print(f"  ... and {len(issues) - 10} more issues")
    print()

if failed == 0 and warnings == 0:
    print("🎉 ALL LISTINGS VERIFIED SUCCESSFULLY!")
    print("   All listings match between JSON source and RESO API")
    sys.exit(0)
elif failed == 0:
    print("⚠️  VERIFICATION COMPLETE WITH WARNINGS")
    print("   All listings found, but some have minor data differences")
    sys.exit(0)
else:
    print("❌ VERIFICATION FAILED")
    print("   Some listings are missing or have critical issues")
    sys.exit(1)

PYTHON_SCRIPT

