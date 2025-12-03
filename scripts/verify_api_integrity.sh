#!/bin/bash
# ============================================================
# RESO Web API Integrity Test
# Two-way verification: Databricks ↔ API
# ============================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MLS2_ROOT="$(dirname "$SCRIPT_DIR")"

# Load environment
if [ -f "$MLS2_ROOT/.env" ]; then
    export $(grep -v '^#' "$MLS2_ROOT/.env" | xargs)
fi

API_BASE="${API_BASE_URL:-https://humaticai.com/reso}"

echo "=============================================="
echo "  RESO Web API Two-Way Integrity Test"
echo "=============================================="
echo ""
echo "API: $API_BASE"
echo "Databricks: $DATABRICKS_HOST"
echo ""

# Python script for comprehensive testing
python3 << 'PYTHON_SCRIPT'
import os
import sys
import json
import httpx

API_BASE = os.environ.get('API_BASE_URL', 'https://humaticai.com/reso')
DB_HOST = os.environ['DATABRICKS_HOST']
DB_TOKEN = os.environ['DATABRICKS_TOKEN']
DB_WAREHOUSE = os.environ['DATABRICKS_WAREHOUSE_ID']
DB_CATALOG = os.environ.get('DATABRICKS_CATALOG', 'mls2')
DB_SCHEMA = os.environ.get('DATABRICKS_SCHEMA', 'reso_gold')

def db_query(sql):
    """Execute query against Databricks"""
    resp = httpx.post(
        f"{DB_HOST}/api/2.0/sql/statements",
        headers={"Authorization": f"Bearer {DB_TOKEN}"},
        json={"warehouse_id": DB_WAREHOUSE, "statement": sql, "wait_timeout": "30s"},
        timeout=60
    )
    data = resp.json()
    if 'result' in data and data['result'].get('data_array'):
        return data['result']['data_array']
    return []

def api_get(endpoint):
    """GET from RESO API"""
    resp = httpx.get(f"{API_BASE}{endpoint}", timeout=60)
    return resp.json()

print("=" * 60)
print("TEST 1: Record Count Verification")
print("=" * 60)

resources = [
    ('Property', 'property'),
    ('Member', 'member'),
    ('Office', 'office'),
    ('Media', 'media'),
    ('Contacts', 'contacts'),
    ('ShowingAppointment', 'showing_appointment'),
]

count_issues = []
for api_name, table_name in resources:
    # Get count from Databricks
    db_result = db_query(f"SELECT COUNT(*) FROM {DB_CATALOG}.{DB_SCHEMA}.{table_name}")
    db_count = int(db_result[0][0]) if db_result else 0
    
    # Get count from API
    api_data = api_get(f"/odata/{api_name}?$count=true&$top=1")
    api_count = api_data.get('@odata.count', 0)
    
    match = "✅" if db_count == api_count else "❌"
    if db_count != api_count:
        count_issues.append(f"{api_name}: DB={db_count}, API={api_count}")
    
    print(f"  {match} {api_name:<20} DB: {db_count:>8,}  API: {api_count:>8,}")

print("")
print("=" * 60)
print("TEST 2: Sample Data Verification (Property)")
print("=" * 60)

# Get sample from DB
db_sample = db_query(f"""
    SELECT ListingKey, ListPrice, City, BedroomsTotal, BathroomsTotalInteger
    FROM {DB_CATALOG}.{DB_SCHEMA}.property
    ORDER BY ListingKey
    LIMIT 5
""")

# Get same records from API
data_issues = []
for row in db_sample:
    listing_key = row[0]
    db_price = float(row[1]) if row[1] else None
    db_city = row[2]
    db_beds = int(row[3]) if row[3] else None
    db_baths = int(row[4]) if row[4] else None
    
    # Fetch from API
    api_data = api_get(f"/odata/Property?$filter=ListingKey eq '{listing_key}'&$select=ListingKey,ListPrice,City,BedroomsTotal,BathroomsTotalInteger")
    
    if not api_data.get('value'):
        print(f"  ❌ {listing_key[:30]}... NOT FOUND in API")
        data_issues.append(f"{listing_key}: Not found in API")
        continue
    
    api_prop = api_data['value'][0]
    api_price = api_prop.get('ListPrice')
    api_city = api_prop.get('City')
    api_beds = api_prop.get('BedroomsTotal')
    api_baths = api_prop.get('BathroomsTotalInteger')
    
    # Compare
    issues = []
    if db_price != api_price: issues.append(f"Price: DB={db_price}, API={api_price}")
    if db_city != api_city: issues.append(f"City: DB={db_city}, API={api_city}")
    if db_beds != api_beds: issues.append(f"Beds: DB={db_beds}, API={api_beds}")
    if db_baths != api_baths: issues.append(f"Baths: DB={db_baths}, API={api_baths}")
    
    if issues:
        print(f"  ❌ {listing_key[:30]}...")
        for i in issues:
            print(f"     {i}")
            data_issues.append(f"{listing_key}: {i}")
    else:
        print(f"  ✅ {listing_key[:30]}... Price={api_price}, City={api_city}, Beds={api_beds}")

print("")
print("=" * 60)
print("TEST 3: Type Verification (Sample Fields)")
print("=" * 60)

api_prop = api_get("/odata/Property?$top=1")['value'][0]

type_checks = [
    ('ListPrice', (int, float), api_prop.get('ListPrice')),
    ('BedroomsTotal', (int, type(None)), api_prop.get('BedroomsTotal')),
    ('BathroomsTotalInteger', (int, type(None)), api_prop.get('BathroomsTotalInteger')),
    ('Latitude', (int, float, type(None)), api_prop.get('Latitude')),
    ('Longitude', (int, float, type(None)), api_prop.get('Longitude')),
    ('LivingArea', (int, float, type(None)), api_prop.get('LivingArea')),
    ('City', (str, type(None)), api_prop.get('City')),
    ('ListingKey', (str,), api_prop.get('ListingKey')),
    ('ListPriceCurrencyCode', (str, type(None)), api_prop.get('ListPriceCurrencyCode')),
]

type_issues = []
for field, expected_types, value in type_checks:
    actual_type = type(value)
    ok = actual_type in expected_types
    if not ok:
        type_issues.append(f"{field}: expected {expected_types}, got {actual_type}")
    status = "✅" if ok else "❌"
    print(f"  {status} {field:<25} {actual_type.__name__:<10} = {str(value)[:25]}")

print("")
print("=" * 60)
print("TEST 4: Media URL Verification")
print("=" * 60)

# Check that media URLs are full paths
media_data = api_get("/odata/Media?$top=3&$select=MediaKey,MediaURL")
url_issues = []
for media in media_data.get('value', []):
    url = media.get('MediaURL', '')
    if url and not url.startswith('http'):
        url_issues.append(f"{media['MediaKey']}: URL not absolute")
        print(f"  ❌ {media['MediaKey'][:30]}... URL={url[:40]}")
    else:
        print(f"  ✅ {media['MediaKey'][:30]}... URL is absolute")

print("")
print("=" * 60)
print("TEST 5: API Response Format")
print("=" * 60)

# Check OData response format
prop_resp = api_get("/odata/Property?$top=1&$count=true")
format_checks = [
    ('@odata.context' in prop_resp, '@odata.context present'),
    ('@odata.count' in prop_resp, '@odata.count present'),
    ('value' in prop_resp, 'value array present'),
    (isinstance(prop_resp.get('value'), list), 'value is array'),
]

format_issues = []
for passed, desc in format_checks:
    status = "✅" if passed else "❌"
    if not passed:
        format_issues.append(desc)
    print(f"  {status} {desc}")

print("")
print("=" * 60)
print("SUMMARY")
print("=" * 60)

total_issues = len(count_issues) + len(data_issues) + len(type_issues) + len(url_issues) + len(format_issues)

print(f"  Count Verification:    {'✅ PASS' if not count_issues else '❌ FAIL (' + str(len(count_issues)) + ')'}")
print(f"  Data Verification:     {'✅ PASS' if not data_issues else '❌ FAIL (' + str(len(data_issues)) + ')'}")
print(f"  Type Verification:     {'✅ PASS' if not type_issues else '❌ FAIL (' + str(len(type_issues)) + ')'}")
print(f"  Media URL Verification:{'✅ PASS' if not url_issues else '❌ FAIL (' + str(len(url_issues)) + ')'}")
print(f"  Response Format:       {'✅ PASS' if not format_issues else '❌ FAIL (' + str(len(format_issues)) + ')'}")
print("")

if total_issues == 0:
    print("🎉 ALL INTEGRITY TESTS PASSED!")
    sys.exit(0)
else:
    print(f"⚠️  {total_issues} issues found")
    sys.exit(1)

PYTHON_SCRIPT

