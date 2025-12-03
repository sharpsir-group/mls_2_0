#!/bin/bash
# ============================================================
# RESO Web API Integrity Test
# Two-way verification: Qobrix API ↔ RESO API
# ============================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MLS2_ROOT="$(dirname "$SCRIPT_DIR")"

# Load environment
if [ -f "$MLS2_ROOT/.env" ]; then
    export $(grep -v '^#' "$MLS2_ROOT/.env" | xargs)
fi

RESO_API="${RESO_API_URL:-https://humaticai.com/reso}"

echo "=============================================="
echo "  Qobrix → RESO API Two-Way Integrity Test"
echo "=============================================="
echo ""
echo "Qobrix API: $QOBRIX_API_BASE_URL"
echo "RESO API:   $RESO_API"
echo ""

# Python script for comprehensive testing
python3 << 'PYTHON_SCRIPT'
import os
import sys
import json
import httpx

QOBRIX_API = os.environ['QOBRIX_API_BASE_URL']
QOBRIX_USER = os.environ['QOBRIX_API_USER']
QOBRIX_KEY = os.environ['QOBRIX_API_KEY']
RESO_API = os.environ.get('RESO_API_URL', 'https://humaticai.com/reso')

def qobrix_get(endpoint, params=None):
    """GET from Qobrix API"""
    headers = {
        'X-Api-User': QOBRIX_USER,
        'X-Api-Key': QOBRIX_KEY
    }
    resp = httpx.get(f"{QOBRIX_API}{endpoint}", headers=headers, params=params, timeout=60)
    return resp.json()

def reso_get(endpoint):
    """GET from RESO API"""
    resp = httpx.get(f"{RESO_API}{endpoint}", timeout=60)
    return resp.json()

print("=" * 60)
print("TEST 1: Property Count Verification")
print("=" * 60)

# Qobrix property count
qobrix_props = qobrix_get('/properties', {'limit': 1, 'page': 1})
qobrix_count = qobrix_props.get('pagination', {}).get('count', 0)

# RESO property count
reso_props = reso_get('/odata/Property?$count=true&$top=1')
reso_count = reso_props.get('@odata.count', 0)

# Allow small tolerance for recently added/deleted records
diff = abs(qobrix_count - reso_count)
tolerance = max(10, qobrix_count * 0.001)  # 0.1% or 10, whichever is larger
match = "✅" if diff <= tolerance else "❌"
if diff > 0 and diff <= tolerance:
    match = "⚠️"  # Warning for small difference
print(f"  {match} Properties: Qobrix={qobrix_count:,}  RESO={reso_count:,}  (diff={diff})")

count_issues = []
if diff > tolerance:
    count_issues.append(f"Property count: Qobrix={qobrix_count}, RESO={reso_count}, diff={diff}")

print("")
print("=" * 60)
print("TEST 2: Sample Property Data Verification")
print("=" * 60)

# Get 5 sample properties from Qobrix
qobrix_sample = qobrix_get('/properties', {'limit': 5, 'page': 1})
data_issues = []

for qprop in qobrix_sample.get('data', []):
    qid = qprop.get('id')
    listing_key = f"QOBRIX_{qid}"
    
    # Get from RESO API
    reso_data = reso_get(f"/odata/Property?$filter=ListingKey eq '{listing_key}'")
    
    if not reso_data.get('value'):
        print(f"  ❌ {listing_key[:40]}... NOT FOUND in RESO API")
        data_issues.append(f"{listing_key}: Not found in RESO")
        continue
    
    rprop = reso_data['value'][0]
    
    # Compare key fields
    issues = []
    
    # Price
    q_price = qprop.get('sale_price_amount') or qprop.get('rent_price_amount')
    r_price = rprop.get('ListPrice')
    if q_price and r_price:
        q_price_f = float(q_price) if q_price else None
        r_price_f = float(r_price) if r_price else None
        if q_price_f != r_price_f:
            issues.append(f"Price: Q={q_price_f}, R={r_price_f}")
    
    # City
    q_city = qprop.get('city')
    r_city = rprop.get('City')
    if q_city != r_city:
        issues.append(f"City: Q={q_city}, R={r_city}")
    
    # Bedrooms
    q_beds = qprop.get('bedrooms')
    r_beds = rprop.get('BedroomsTotal')
    if q_beds and r_beds:
        try:
            q_beds_i = int(float(q_beds)) if q_beds else None
            r_beds_i = int(r_beds) if r_beds else None
            if q_beds_i != r_beds_i:
                issues.append(f"Beds: Q={q_beds_i}, R={r_beds_i}")
        except:
            pass
    
    if issues:
        print(f"  ❌ {listing_key[:40]}...")
        for i in issues:
            print(f"     {i}")
            data_issues.append(f"{listing_key}: {i}")
    else:
        print(f"  ✅ {listing_key[:40]}... Price={r_price}, City={r_city}")

print("")
print("=" * 60)
print("TEST 3: Media/Photos Verification")
print("=" * 60)

# Get 5 sample properties and check their media counts
qobrix_props = qobrix_get('/properties', {'limit': 5, 'page': 1})
media_issues = []

for qprop in qobrix_props.get('data', []):
    qid = qprop.get('id')
    listing_key = f"QOBRIX_{qid}"
    
    # Get photos from Qobrix via media endpoint
    try:
        qobrix_photos = qobrix_get(f'/media/by-category/photos/Properties/{qid}')
        qobrix_media_count = len(qobrix_photos.get('data', []))
    except:
        qobrix_media_count = 0
    
    # Get media from RESO API
    reso_media = reso_get(f"/odata/Media?$filter=ResourceRecordKey eq '{listing_key}'&$count=true")
    reso_media_count = reso_media.get('@odata.count', 0)
    
    match = "✅" if qobrix_media_count == reso_media_count else "❌"
    if qobrix_media_count != reso_media_count:
        media_issues.append(f"{listing_key}: Q={qobrix_media_count}, R={reso_media_count}")
    
    print(f"  {match} {listing_key[:40]}... Q={qobrix_media_count}, R={reso_media_count}")

print("")
print("=" * 60)
print("TEST 4: Agent/Member Verification")
print("=" * 60)

# RESO Member = Qobrix /agents + /users (combined in Silver ETL)
qobrix_agents = qobrix_get('/agents', {'limit': 1, 'page': 1})
q_agent_count = qobrix_agents.get('pagination', {}).get('count', 0)

qobrix_users = qobrix_get('/users', {'limit': 1, 'page': 1})
q_user_count = qobrix_users.get('pagination', {}).get('count', 0)

q_combined = q_agent_count + q_user_count

# Get members from RESO
reso_members = reso_get('/odata/Member?$count=true&$top=1')
r_member_count = reso_members.get('@odata.count', 0)

match = "✅" if q_combined == r_member_count else "⚠️"
print(f"  {match} Qobrix /agents: {q_agent_count} + /users: {q_user_count} = {q_combined}")
print(f"  {match} RESO Member: {r_member_count}")

member_issues = []
if q_combined != r_member_count:
    member_issues.append(f"Count mismatch: Q={q_combined}, R={r_member_count}")

print("")
print("=" * 60)
print("TEST 5: Contact Verification")
print("=" * 60)

# Get contacts from Qobrix
qobrix_contacts = qobrix_get('/contacts', {'limit': 1, 'page': 1})
q_contact_count = qobrix_contacts.get('pagination', {}).get('count', 0)

# Get contacts from RESO
reso_contacts = reso_get('/odata/Contacts?$count=true&$top=1')
r_contact_count = reso_contacts.get('@odata.count', 0)

# Allow small tolerance for recently added/deleted records
c_diff = abs(q_contact_count - r_contact_count)
c_tolerance = max(20, q_contact_count * 0.001)  # 0.1% or 20
match = "✅" if c_diff <= c_tolerance else "❌"
if c_diff > 0 and c_diff <= c_tolerance:
    match = "⚠️"
print(f"  {match} Contacts: Qobrix={q_contact_count:,}, RESO={r_contact_count:,}  (diff={c_diff})")

contact_issues = []
if c_diff > c_tolerance:
    contact_issues.append(f"Count mismatch: Q={q_contact_count}, R={r_contact_count}, diff={c_diff}")

print("")
print("=" * 60)
print("TEST 6: Field Transformation Verification")
print("=" * 60)

# Get one property and check transformations
q_sample = qobrix_get('/properties', {'limit': 1, 'page': 1})['data'][0]
qid = q_sample['id']
r_sample = reso_get(f"/odata/Property?$filter=ListingKey eq 'QOBRIX_{qid}'")['value'][0]

transform_checks = []

# ListingKey transformation
transform_checks.append(('ListingKey', f"QOBRIX_{qid}", r_sample.get('ListingKey')))

# PropertyType mapping (Qobrix property_type -> RESO PropertyType, title case)
q_type = q_sample.get('property_type')
r_type = r_sample.get('PropertyType')
expected_type = q_type.title() if q_type else None
transform_checks.append(('PropertyType', expected_type, r_type))

# StandardStatus mapping  
q_status = q_sample.get('status')
r_status = r_sample.get('StandardStatus')
status_map = {'available': 'Active', 'sold': 'Closed', 'let': 'Leased', 'pending': 'Pending'}
expected_status = status_map.get(q_status, q_status)
transform_checks.append(('StandardStatus', expected_status, r_status))

# Currency Code
r_currency = r_sample.get('ListPriceCurrencyCode')
transform_checks.append(('ListPriceCurrencyCode', 'EUR', r_currency))  # Assuming EUR

transform_issues = []
for field, expected, actual in transform_checks:
    match = "✅" if expected == actual else "❌"
    if expected != actual:
        transform_issues.append(f"{field}: expected={expected}, got={actual}")
    print(f"  {match} {field}: {expected} → {actual}")

print("")
print("=" * 60)
print("TEST 7: RESO Type Compliance")
print("=" * 60)

# Check that RESO API returns correct types
type_checks = [
    ('ListPrice', (int, float), r_sample.get('ListPrice')),
    ('BedroomsTotal', (int, type(None)), r_sample.get('BedroomsTotal')),
    ('BathroomsTotalInteger', (int, type(None)), r_sample.get('BathroomsTotalInteger')),
    ('Latitude', (int, float, type(None)), r_sample.get('Latitude')),
    ('Longitude', (int, float, type(None)), r_sample.get('Longitude')),
    ('LivingArea', (int, float, type(None)), r_sample.get('LivingArea')),
    ('City', (str, type(None)), r_sample.get('City')),
    ('ListingKey', (str,), r_sample.get('ListingKey')),
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
print("TEST 8: Media URL Full Path")
print("=" * 60)

# Check that media URLs are full paths
media_data = reso_get("/odata/Media?$top=3&$select=MediaKey,MediaURL")
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
print("SUMMARY")
print("=" * 60)

total_issues = len(count_issues) + len(data_issues) + len(media_issues) + len(contact_issues) + len(transform_issues) + len(type_issues) + len(url_issues)

print(f"  Property Count:         {'✅ PASS' if not count_issues else '❌ FAIL (' + str(len(count_issues)) + ')'}")
print(f"  Property Data:          {'✅ PASS' if not data_issues else '❌ FAIL (' + str(len(data_issues)) + ')'}")
print(f"  Media Count:            {'✅ PASS' if not media_issues else '❌ FAIL (' + str(len(media_issues)) + ')'}")
print(f"  Contact Count:          {'✅ PASS' if not contact_issues else '❌ FAIL (' + str(len(contact_issues)) + ')'}")
print(f"  Field Transformations:  {'✅ PASS' if not transform_issues else '❌ FAIL (' + str(len(transform_issues)) + ')'}")
print(f"  RESO Type Compliance:   {'✅ PASS' if not type_issues else '❌ FAIL (' + str(len(type_issues)) + ')'}")
print(f"  Media URL Full Path:    {'✅ PASS' if not url_issues else '❌ FAIL (' + str(len(url_issues)) + ')'}")
print("")

if total_issues == 0:
    print("🎉 ALL INTEGRITY TESTS PASSED!")
    print("   Qobrix API data matches RESO API data")
    sys.exit(0)
else:
    print(f"⚠️  {total_issues} issues found")
    sys.exit(1)

PYTHON_SCRIPT
