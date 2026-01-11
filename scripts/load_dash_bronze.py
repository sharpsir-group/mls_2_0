#!/usr/bin/env python3
"""
Dash Bronze Data Loader

Loads Dash/Sotheby's JSON files from local filesystem into Databricks Bronze tables.
Usage:
    python3 scripts/load_dash_bronze.py tmp/dash_listings_hungary.json
    python3 scripts/load_dash_bronze.py tmp/dash_listings_hungary.json --country HU
"""
import json
import sys
import argparse
from pathlib import Path
import asyncio
import httpx
from typing import Any, Optional

# Add api directory to path for config
sys.path.insert(0, str(Path(__file__).parent.parent / "api"))
from config import get_settings


class DashBronzeLoader:
    """Load Dash JSON data into Databricks Bronze tables."""
    
    def __init__(self):
        self.settings = get_settings()
        host = self.settings.databricks_host
        if host.startswith("https://"):
            self.base_url = host.rstrip("/")
        else:
            self.base_url = f"https://{host}"
        self.headers = {
            "Authorization": f"Bearer {self.settings.databricks_token}",
            "Content-Type": "application/json"
        }
        self.catalog = "mls2"
        self.schema = "dash_bronze"
    
    async def execute_query(self, sql: str) -> dict[str, Any]:
        """Execute SQL query against Databricks."""
        payload = {
            "warehouse_id": self.settings.databricks_warehouse_id,
            "statement": sql,
            "wait_timeout": "30s",
            "on_wait_timeout": "CANCEL"
        }
        
        async with httpx.AsyncClient(timeout=60) as client:
            url = f"{self.base_url}/api/2.0/sql/statements"
            response = await client.post(url, headers=self.headers, json=payload)
            
            if response.status_code >= 400:
                raise Exception(f"HTTP {response.status_code}: {response.text[:500]}")
            
            response.raise_for_status()
            result = response.json()
            status = result.get("status", {}).get("state")
            statement_id = result.get("statement_id")
            
            # Poll for completion
            while status in ("PENDING", "RUNNING"):
                await asyncio.sleep(0.5)
                poll_response = await client.get(
                    f"{self.base_url}/api/2.0/sql/statements/{statement_id}",
                    headers=self.headers
                )
                poll_response.raise_for_status()
                result = poll_response.json()
                status = result.get("status", {}).get("state")
            
            if status == "FAILED":
                error = result.get("status", {}).get("error", {})
                raise Exception(f"Query failed: {error.get('message', 'Unknown error')}")
            
            if status == "CANCELED":
                raise Exception("Query was canceled (timeout)")
            
            return result
    
    async def ensure_schema_exists(self):
        """Create dash_bronze schema if it doesn't exist."""
        sql = f"""
            CREATE SCHEMA IF NOT EXISTS {self.catalog}.{self.schema}
        """
        await self.execute_query(sql)
        print(f"✅ Schema {self.catalog}.{self.schema} ready")
    
    def transform_dash_to_bronze_properties(self, listings: list, country_code: str) -> list[dict]:
        """Transform Dash listings to bronze properties format."""
        properties = []
        
        for listing in listings:
            prop = {}
            prop_details = listing.get("propertyDetails", {})
            location = prop_details.get("location", {})
            
            # Identifiers
            prop["id"] = listing.get("listingGuid", "")
            prop["ref"] = listing.get("listingId", "")
            
            # Status
            prop["status"] = listing.get("statusCode", "")
            prop["status_description"] = listing.get("statusDescription", "")
            
            # Pricing
            prop["list_selling_price_amount"] = str(listing.get("listPrice", ""))
            prop["list_price_usd"] = str(listing.get("listPriceInUSD", ""))
            prop["currency_code"] = listing.get("currencyCode", "")
            prop["currency_name"] = listing.get("currencyName", "")
            
            # Property details
            prop["property_type"] = prop_details.get("typeDescription", "")
            prop["property_type_code"] = prop_details.get("typeCode", "")
            prop["property_subtype"] = prop_details.get("subtypeDescription", "")
            prop["property_subtype_code"] = prop_details.get("subtypeCode", "")
            prop["property_name"] = prop_details.get("propertyName", "")
            prop["style_code"] = prop_details.get("styleCode", "")
            prop["style_description"] = prop_details.get("styleDescription", "")
            
            # Bedrooms/bathrooms
            prop["bedrooms"] = str(prop_details.get("noOfBedrooms", ""))
            prop["bathrooms"] = str(prop_details.get("fullBath", ""))
            prop["half_bath"] = str(prop_details.get("halfBath", ""))
            
            # Areas
            prop["living_area"] = str(prop_details.get("livingArea", ""))
            prop["living_area_unit"] = prop_details.get("livingAreaUnitCode", "")
            prop["building_area"] = str(prop_details.get("buildingArea", ""))
            prop["building_area_unit"] = prop_details.get("buildingAreaUnitCode", "")
            prop["lot_size"] = str(prop_details.get("lotSize", ""))
            prop["lot_size_unit"] = prop_details.get("lotSizeUnitCode", "")
            
            # Location
            prop["country"] = location.get("countryCode", country_code)
            prop["country_name"] = location.get("countryName", "")
            prop["state"] = location.get("stateProvinceCode", "")
            prop["state_name"] = location.get("stateProvinceName", "")
            prop["city"] = location.get("city", "")
            prop["district"] = location.get("district", "")
            prop["post_code"] = location.get("postalCode", "")
            prop["street"] = location.get("addressLine1", "")
            prop["latitude"] = str(location.get("latitude", ""))
            prop["longitude"] = str(location.get("longitude", ""))
            
            # Dates
            prop["listed_date"] = listing.get("listedDate", "")
            prop["last_update_on"] = listing.get("lastUpdateOn", "")
            prop["last_updated_by"] = listing.get("lastUpdatedBy", "")
            
            # Flags
            prop["is_off_market"] = str(listing.get("isOffTheMarket", False))
            prop["is_for_auction"] = str(listing.get("isForAuction", False))
            prop["is_new_construction"] = str(listing.get("isNewConstruction", False))
            prop["is_call_to_show"] = str(listing.get("isCallToShow", False))
            prop["is_price_upon_request"] = str(listing.get("isPriceUponRequest", False))
            prop["is_foreclosure"] = str(listing.get("isForeclosure", False))
            
            # URLs
            prop["listing_url"] = listing.get("listingUrl", "")
            
            # Days on market
            prop["days_on_market"] = str(listing.get("daysOnMarket", ""))
            
            # Remarks (store as JSON string)
            remarks = listing.get("remarks", [])
            if remarks:
                prop["remarks"] = json.dumps(remarks)
            else:
                prop["remarks"] = ""
            
            # Features (store as JSON string)
            features = prop_details.get("features", [])
            if features:
                prop["features"] = json.dumps(features)
            else:
                prop["features"] = ""
            
            # Additional details
            additional = listing.get("additionalDetails", {})
            if additional:
                prop["additional_details"] = json.dumps(additional)
            else:
                prop["additional_details"] = ""
            
            # Source identifier
            prop["source"] = "dash_sothebys"
            
            # Convert all values to strings (bronze layer requirement)
            for key, value in prop.items():
                if value is None:
                    prop[key] = ""
                elif isinstance(value, (dict, list)):
                    prop[key] = json.dumps(value)
                else:
                    prop[key] = str(value)
            
            properties.append(prop)
        
        return properties
    
    def transform_dash_to_bronze_media(self, listings: list) -> list[dict]:
        """Transform Dash media to bronze media format."""
        media_items = []
        
        for listing in listings:
            listing_guid = listing.get("listingGuid", "")
            media_list = listing.get("media", [])
            
            for media_item in media_list:
                media = {}
                media["id"] = media_item.get("mediaGuid", "")
                media["property_id"] = listing_guid
                media["sequence_number"] = str(media_item.get("sequenceNumber", ""))
                media["category"] = media_item.get("category", "")
                media["is_default"] = str(media_item.get("isDefault", False))
                media["url"] = media_item.get("url", "")
                media["caption"] = media_item.get("caption", "")
                media["format_code"] = media_item.get("formatCode", "")
                media["format_description"] = media_item.get("formatDescription", "")
                media["height"] = str(media_item.get("height", ""))
                media["width"] = str(media_item.get("width", ""))
                media["is_landscape"] = str(media_item.get("isLandscape", False))
                media["is_distributable"] = str(media_item.get("isDistributable", False))
                
                # Resolution URLs (store as JSON)
                resolution_urls = media_item.get("resolutionUrls", [])
                if resolution_urls:
                    media["resolution_urls"] = json.dumps(resolution_urls)
                else:
                    media["resolution_urls"] = ""
                
                # Additional annotations (store as JSON)
                annotations = media_item.get("additionalAnnotations", [])
                if annotations:
                    media["additional_annotations"] = json.dumps(annotations)
                else:
                    media["additional_annotations"] = ""
                
                # Media tags (store as JSON)
                tags = media_item.get("mediaTags", [])
                if tags:
                    media["media_tags"] = json.dumps(tags)
                else:
                    media["media_tags"] = ""
                
                # Source identifier
                media["source"] = "dash_sothebys"
                
                # Convert all values to strings
                for key, value in media.items():
                    if value is None:
                        media[key] = ""
                    elif isinstance(value, (dict, list)):
                        media[key] = json.dumps(value)
                    else:
                        media[key] = str(value)
                
                media_items.append(media)
        
        return media_items
    
    async def load_properties(self, properties: list):
        """Load properties into dash_bronze.properties table."""
        if not properties:
            print("⚠️  No properties to load")
            return
        
        # Build INSERT statements (batch insert)
        # Since Databricks SQL API doesn't support bulk INSERT easily, we'll use CREATE TABLE AS SELECT
        # First, create a temporary JSON structure and insert via SQL
        
        # For now, we'll use a simpler approach: create table with all columns as STRING
        # and insert row by row (or use INSERT INTO with VALUES)
        
        # Get column names from first property
        columns = list(properties[0].keys())
        columns_str = ", ".join([f"`{col}`" for col in columns])
        
        # Build VALUES clause
        values_clauses = []
        for prop in properties:
            values = []
            for col in columns:
                val = prop.get(col, "")
                # Escape single quotes and wrap in quotes
                val_escaped = val.replace("'", "''").replace("\\", "\\\\")
                values.append(f"'{val_escaped}'")
            values_clauses.append(f"({', '.join(values)})")
        
        # Create table if not exists
        create_table_sql = f"""
            CREATE TABLE IF NOT EXISTS {self.catalog}.{self.schema}.properties (
                {', '.join([f"`{col}` STRING" for col in columns])}
            ) USING DELTA
        """
        await self.execute_query(create_table_sql)
        
        # Drop and recreate (bronze layer = overwrite)
        drop_table_sql = f"DROP TABLE IF EXISTS {self.catalog}.{self.schema}.properties"
        await self.execute_query(drop_table_sql)
        
        # Recreate table
        await self.execute_query(create_table_sql)
        
        # Insert in batches (Databricks SQL API has limits)
        batch_size = 50
        for i in range(0, len(values_clauses), batch_size):
            batch = values_clauses[i:i+batch_size]
            insert_sql = f"""
                INSERT INTO {self.catalog}.{self.schema}.properties ({columns_str})
                VALUES {', '.join(batch)}
            """
            await self.execute_query(insert_sql)
            print(f"  Inserted batch {i//batch_size + 1} ({len(batch)} properties)")
        
        print(f"✅ Loaded {len(properties)} properties into {self.catalog}.{self.schema}.properties")
    
    async def load_media(self, media_items: list):
        """Load media into dash_bronze.media table."""
        if not media_items:
            print("⚠️  No media items to load")
            return
        
        columns = list(media_items[0].keys())
        columns_str = ", ".join([f"`{col}`" for col in columns])
        
        values_clauses = []
        for media in media_items:
            values = []
            for col in columns:
                val = media.get(col, "")
                val_escaped = val.replace("'", "''").replace("\\", "\\\\")
                values.append(f"'{val_escaped}'")
            values_clauses.append(f"({', '.join(values)})")
        
        create_table_sql = f"""
            CREATE TABLE IF NOT EXISTS {self.catalog}.{self.schema}.media (
                {', '.join([f"`{col}` STRING" for col in columns])}
            ) USING DELTA
        """
        await self.execute_query(create_table_sql)
        
        drop_table_sql = f"DROP TABLE IF EXISTS {self.catalog}.{self.schema}.media"
        await self.execute_query(drop_table_sql)
        await self.execute_query(create_table_sql)
        
        batch_size = 50
        for i in range(0, len(values_clauses), batch_size):
            batch = values_clauses[i:i+batch_size]
            insert_sql = f"""
                INSERT INTO {self.catalog}.{self.schema}.media ({columns_str})
                VALUES {', '.join(batch)}
            """
            await self.execute_query(insert_sql)
            print(f"  Inserted batch {i//batch_size + 1} ({len(batch)} media items)")
        
        print(f"✅ Loaded {len(media_items)} media items into {self.catalog}.{self.schema}.media")
    
    async def load_file(self, json_file: Path, country_code: Optional[str] = None):
        """Load Dash JSON file into Databricks Bronze."""
        print(f"📥 Loading Dash data from: {json_file}")
        
        if not json_file.exists():
            raise FileNotFoundError(f"File not found: {json_file}")
        
        with open(json_file, 'r', encoding='utf-8') as f:
            listings = json.load(f)
        
        print(f"📊 Found {len(listings)} listings")
        
        # Determine country code
        if not country_code and listings:
            first_listing = listings[0]
            country_code = first_listing.get("propertyDetails", {}).get("location", {}).get("countryCode", "HU")
        
        print(f"🌍 Country code: {country_code}")
        
        # Ensure schema exists
        await self.ensure_schema_exists()
        
        # Transform data
        print("\n🔄 Transforming properties...")
        properties = self.transform_dash_to_bronze_properties(listings, country_code or "HU")
        
        print("🔄 Transforming media...")
        media_items = self.transform_dash_to_bronze_media(listings)
        
        # Load into Databricks
        print("\n💾 Loading properties into Databricks...")
        await self.load_properties(properties)
        
        print("\n💾 Loading media into Databricks...")
        await self.load_media(media_items)
        
        print("\n✅ Dash Bronze load complete!")


async def main():
    parser = argparse.ArgumentParser(description="Load Dash JSON data into Databricks Bronze")
    parser.add_argument("json_file", type=str, help="Path to Dash JSON file")
    parser.add_argument("--country", type=str, help="Country code (e.g., HU, CY)")
    
    args = parser.parse_args()
    
    json_path = Path(args.json_file)
    if not json_path.is_absolute():
        json_path = Path(__file__).parent.parent / json_path
    
    loader = DashBronzeLoader()
    await loader.load_file(json_path, args.country)


if __name__ == "__main__":
    asyncio.run(main())

