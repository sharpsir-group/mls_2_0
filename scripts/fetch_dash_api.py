#!/usr/bin/env python3
"""
DASH API Fetcher

Fetches listing data from DASH/Sotheby's API using Okta OAuth authentication.
Supports fetching by office, by delta, or all available listings.

Usage:
    # Fetch listings for a specific source (by office key)
    python3 scripts/fetch_dash_api.py --source SHARPSIR-KZ-001
    
    # Fetch and immediately load to Databricks bronze
    python3 scripts/fetch_dash_api.py --source SHARPSIR-KZ-001 --load
    
    # Output to specific file
    python3 scripts/fetch_dash_api.py --source SHARPSIR-KZ-001 --output /path/to/output.json
    
    # List available DASH_API sources
    python3 scripts/fetch_dash_api.py --list-sources
"""
import httpx
import json
import asyncio
import argparse
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# Load .env from project root
from dotenv import load_dotenv
MLS2_ROOT = Path(__file__).parent.parent
load_dotenv(MLS2_ROOT / ".env")

# Add api directory to path for config
sys.path.insert(0, str(MLS2_ROOT / "api"))
from config import get_settings, DataSource


class DashAPIFetcher:
    """Fetches listings from DASH API using Okta OAuth."""
    
    def __init__(self, source: DataSource):
        """
        Initialize fetcher with a DataSource configuration.
        
        Args:
            source: DataSource object with DASH_API credentials
        """
        if source.source_type != "DASH_API":
            raise ValueError(f"Source {source.office_key} is not DASH_API type (got {source.source_type})")
        
        self.source = source
        self.office_key = source.office_key
        self.system_name = source.system_name
        self.system_id = source.system_id
        self.country = source.country
        
        # DASH API credentials from source
        self.api_key = source.dash_api_key
        self.okta_client_id = source.dash_okta_client_id
        self.okta_client_secret = source.dash_okta_client_secret
        self.okta_token_url = source.dash_okta_token_url
        self.okta_scope = source.dash_okta_scope
        self.api_base_url = source.dash_api_url
        self.office_guid = source.dash_office_guid
        
        self.version_params = {"x-rlgy-version": "v4.1"}
        self.access_token: Optional[str] = None
        self.token_expires_at: Optional[datetime] = None
    
    async def get_access_token(self) -> str:
        """Get OAuth2 access token from Okta (with caching)."""
        # Return cached token if still valid
        if self.access_token and self.token_expires_at:
            if datetime.now() < self.token_expires_at - timedelta(minutes=5):
                return self.access_token
        
        print("🔐 Getting Okta access token...")
        
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                self.okta_token_url,
                auth=(self.okta_client_id, self.okta_client_secret),
                data={"grant_type": "client_credentials", "scope": self.okta_scope},
                headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"}
            )
            
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data.get("access_token")
                expires_in = token_data.get("expires_in", 3600)
                self.token_expires_at = datetime.now() + timedelta(seconds=expires_in)
                print(f"  ✅ Token obtained (expires in {expires_in}s)")
                return self.access_token
            else:
                raise Exception(f"Failed to get token: {response.status_code} - {response.text}")
    
    def get_headers(self) -> dict:
        """Get headers for API requests."""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "apikey": self.api_key,
            "Accept": "application/json"
        }
    
    async def fetch_listings_by_office(self, office_guid: Optional[str] = None) -> list:
        """Fetch all listings for a specific office."""
        office_guid = office_guid or self.office_guid
        print(f"\n🏢 Fetching listings by office: {office_guid}")
        
        await self.get_access_token()
        
        async with httpx.AsyncClient(timeout=60) as client:
            params = {**self.version_params, "officeGuid": office_guid}
            response = await client.get(
                f"{self.api_base_url}/listings/byoffice",
                headers=self.get_headers(),
                params=params
            )
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    print(f"  ✅ Found {len(data)} listing summaries")
                    return data
            else:
                print(f"  ❌ Error {response.status_code}: {response.text[:200]}")
        
        return []
    
    async def fetch_listings_delta(self, from_date: Optional[str] = None) -> list:
        """Fetch all listings changed since a date."""
        if not from_date:
            from_date = (datetime.now() - timedelta(days=365*5)).strftime("%Y-%m-%d")
        
        print(f"\n📋 Fetching listings delta since {from_date}...")
        
        await self.get_access_token()
        
        all_listings = []
        listing_types = ["residentialsale", "residentialrental", "commercialsale", "commerciallease"]
        
        async with httpx.AsyncClient(timeout=60) as client:
            for listing_type in listing_types:
                params = {
                    **self.version_params,
                    "fromDate": from_date,
                    "listingType": listing_type
                }
                
                response = await client.get(
                    f"{self.api_base_url}/listings/delta",
                    headers=self.get_headers(),
                    params=params
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if isinstance(data, list):
                        print(f"  {listing_type}: {len(data)} listings")
                        all_listings.extend(data)
                else:
                    print(f"  {listing_type}: Error {response.status_code}")
        
        print(f"  Total: {len(all_listings)} listings")
        return all_listings
    
    async def fetch_full_listing(
        self,
        client: httpx.AsyncClient,
        listing_guid: str,
        listing_type: str
    ) -> Optional[dict]:
        """Fetch full listing details by GUID."""
        # Map listing type to endpoint
        type_to_endpoint = {
            "Residential Sale": "residentialsales",
            "residentialsale": "residentialsales",
            "Residential Rental": "residentialrentals",
            "residentialrental": "residentialrentals",
            "Commercial Sale": "commercialsales",
            "commercialsale": "commercialsales",
            "Commercial Lease": "commercialleases",
            "commerciallease": "commercialleases"
        }
        
        endpoint_type = type_to_endpoint.get(listing_type)
        if not endpoint_type:
            return None
        
        url = f"{self.api_base_url}/consumer/listings/{endpoint_type}/{listing_guid}"
        
        response = await client.get(url, headers=self.get_headers(), params=self.version_params)
        
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            # Try alternate endpoint
            url = f"{self.api_base_url}/listings/{endpoint_type}/{listing_guid}"
            response = await client.get(
                url,
                headers=self.get_headers(),
                params={**self.version_params, "idType": "id"}
            )
            if response.status_code == 200:
                return response.json()
        
        return None
    
    async def fetch_all_listings(self) -> list:
        """
        Fetch all listings with full details.
        
        1. Get delta listings to find all listing GUIDs and types
        2. Fetch full details for each listing
        3. De-duplicate and return
        """
        print("=" * 60)
        print(f"  DASH API Full Listings Fetch")
        print(f"  Source: {self.office_key} ({self.system_name})")
        print(f"  Time: {datetime.now().isoformat()}")
        print(f"  API: {self.api_base_url}")
        print("=" * 60)
        
        # Get listing summaries from delta
        delta_listings = await self.fetch_listings_delta()
        
        if not delta_listings:
            print("❌ No listings found in delta")
            return []
        
        await self.get_access_token()
        
        print(f"\n🔄 Fetching full details for {len(delta_listings)} listing entries...")
        
        full_listings = {}
        errors = []
        
        async with httpx.AsyncClient(timeout=120) as client:
            for i, listing in enumerate(delta_listings):
                listing_guid = listing.get("entityGuid")
                listing_type = listing.get("type")
                
                if not listing_guid or not listing_type:
                    continue
                
                # Skip if already fetched
                if listing_guid in full_listings:
                    continue
                
                print(f"  [{i+1}/{len(delta_listings)}] {listing_type}: {listing_guid[:8]}...", end=" ")
                
                try:
                    full_data = await self.fetch_full_listing(client, listing_guid, listing_type)
                    
                    if full_data:
                        full_listings[listing_guid] = full_data
                        print("✅")
                    else:
                        errors.append({"guid": listing_guid, "type": listing_type, "error": "Not found"})
                        print("❌")
                except Exception as e:
                    errors.append({"guid": listing_guid, "type": listing_type, "error": str(e)})
                    print(f"❌ {e}")
                
                # Avoid rate limiting
                await asyncio.sleep(0.1)
        
        unique_listings = list(full_listings.values())
        
        print(f"\n📊 Summary:")
        print(f"   Unique listings fetched: {len(unique_listings)}")
        print(f"   Errors: {len(errors)}")
        
        if errors:
            print(f"   First few errors: {errors[:3]}")
        
        return unique_listings


def list_dash_api_sources():
    """List all configured DASH_API sources."""
    settings = get_settings()
    sources = settings.get_sources_by_type("DASH_API")
    
    if not sources:
        print("No DASH_API sources configured in .env")
        return
    
    print("Available DASH_API sources:")
    for src in sources:
        print(f"  {src.office_key}")
        print(f"    Name: {src.system_name}")
        print(f"    System ID: {src.system_id}")
        print(f"    Country: {src.country}")
        print(f"    API URL: {src.dash_api_url}")
        print()


async def main():
    parser = argparse.ArgumentParser(description="Fetch listings from DASH API")
    parser.add_argument("--source", "-s", type=str, help="Source office key (e.g., SHARPSIR-KZ-001)")
    parser.add_argument("--output", "-o", type=str, help="Output JSON file path")
    parser.add_argument("--load", action="store_true", help="Load fetched data into Databricks bronze")
    parser.add_argument("--list-sources", action="store_true", help="List available DASH_API sources")
    
    args = parser.parse_args()
    
    if args.list_sources:
        list_dash_api_sources()
        return 0
    
    if not args.source:
        print("Error: --source is required. Use --list-sources to see available sources.")
        return 1
    
    # Get source configuration
    settings = get_settings()
    source = settings.get_source_by_office_key(args.source)
    
    if not source:
        print(f"Error: Source '{args.source}' not found in configuration.")
        print("Available sources:")
        for src in settings.get_data_sources():
            print(f"  {src.office_key} ({src.source_type})")
        return 1
    
    if source.source_type != "DASH_API":
        print(f"Error: Source '{args.source}' is type '{source.source_type}', not DASH_API")
        return 1
    
    fetcher = DashAPIFetcher(source)
    
    # Fetch all listings
    listings = await fetcher.fetch_all_listings()
    
    if not listings:
        print("❌ No listings fetched")
        return 1
    
    # Determine output path
    if args.output:
        output_path = Path(args.output)
    else:
        # Default to source-specific directory
        output_path = MLS2_ROOT / "dash_hsir_source" / f"dash_{source.country.lower()}_listings_{datetime.now().strftime('%Y%m%d')}.json"
    
    # Save to file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(listings, f, indent=2)
    
    print(f"\n💾 Saved {len(listings)} listings to: {output_path}")
    
    # Optionally load to Databricks
    if args.load:
        print(f"\n📤 Loading to Databricks bronze (office_key={source.office_key})...")
        
        from load_dash_bronze import DashBronzeLoader
        
        loader = DashBronzeLoader(source)
        await loader.load_file(output_path)
    
    print("\n✅ Done!")
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
