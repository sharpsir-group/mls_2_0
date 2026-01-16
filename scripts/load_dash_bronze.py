#!/usr/bin/env python3
"""
Dash Bronze Data Loader

Loads Dash/Sotheby's JSON files from local filesystem into Databricks Bronze tables.
Supports auto-scanning source directory for new/unprocessed files.

Usage:
    # Auto-process all new files from DASH_SOURCE_DIR
    python3 scripts/load_dash_bronze.py
    
    # Process specific file
    python3 scripts/load_dash_bronze.py --file dash_listings_hungary.json
    
    # Process specific file with country override
    python3 scripts/load_dash_bronze.py --file dash_listings_hungary.json --country HU
    
    # Force reprocess all files (ignore tracking)
    python3 scripts/load_dash_bronze.py --force
"""
import json
import sys
import argparse
from pathlib import Path
import asyncio
import hashlib
from datetime import datetime
import httpx
from typing import Any, Optional

# Add api directory to path for config
sys.path.insert(0, str(Path(__file__).parent.parent / "api"))
from config import get_settings


class DashBronzeLoader:
    """Load Dash JSON data into Databricks Bronze tables with file tracking."""
    
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
        
        # Get source directory from settings
        self.source_dir = Path(self.settings.dash_source_dir) if self.settings.dash_source_dir else None
        self.office_key = self.settings.dash_office_key or "HSIR"
    
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
    
    async def ensure_tracking_table_exists(self):
        """Create file tracking table if it doesn't exist."""
        sql = f"""
            CREATE TABLE IF NOT EXISTS {self.catalog}.{self.schema}.processed_files (
                filename STRING,
                file_hash STRING,
                processed_at TIMESTAMP,
                record_count INT,
                office_key STRING
            ) USING DELTA
        """
        await self.execute_query(sql)
    
    async def get_processed_files(self) -> dict[str, str]:
        """Get set of already processed files with their hashes."""
        try:
            result = await self.execute_query(f"""
                SELECT filename, file_hash FROM {self.catalog}.{self.schema}.processed_files
            """)
            
            processed = {}
            manifest = result.get("manifest", {})
            data = result.get("result", {}).get("data_array", [])
            
            for row in data:
                if len(row) >= 2:
                    processed[row[0]] = row[1]
            
            return processed
        except Exception as e:
            # Table might not exist yet
            if "TABLE_OR_VIEW_NOT_FOUND" in str(e) or "does not exist" in str(e).lower():
                return {}
            raise
    
    async def mark_file_processed(self, filename: str, file_hash: str, record_count: int):
        """Mark a file as processed in the tracking table."""
        now = datetime.utcnow().isoformat()
        sql = f"""
            INSERT INTO {self.catalog}.{self.schema}.processed_files 
            (filename, file_hash, processed_at, record_count, office_key)
            VALUES ('{filename}', '{file_hash}', '{now}', {record_count}, '{self.office_key}')
        """
        await self.execute_query(sql)
    
    def compute_file_hash(self, file_path: Path) -> str:
        """Compute MD5 hash of file for change detection."""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def find_new_files(self, processed: dict[str, str]) -> list[Path]:
        """Find JSON files in source directory that haven't been processed or have changed."""
        if not self.source_dir or not self.source_dir.exists():
            return []
        
        new_files = []
        for json_file in self.source_dir.glob("*.json"):
            file_hash = self.compute_file_hash(json_file)
            filename = json_file.name
            
            # Check if file is new or has changed
            if filename not in processed or processed[filename] != file_hash:
                new_files.append(json_file)
        
        return sorted(new_files)  # Sort for consistent ordering
    
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
            
            # Year built (from propertyDetails)
            prop["year_built"] = str(prop_details.get("yearBuilt", ""))
            
            # Expiration date (from additionalDetails)
            prop["expires_on"] = additional.get("expiresOn", "") if additional else ""
            
            # Contingencies
            contingencies = listing.get("contingencies", [])
            prop["contingencies"] = json.dumps(contingencies) if contingencies else ""
            
            # Websites
            websites = listing.get("websites", [])
            prop["websites"] = json.dumps(websites) if websites else ""
            
            # Primary Agent info (denormalized into properties for simplicity)
            primary_agent = listing.get("primaryAgent", {})
            prop["agent_id"] = primary_agent.get("personGuid", "")
            prop["agent_first_name"] = primary_agent.get("firstName", "")
            prop["agent_last_name"] = primary_agent.get("lastName", "")
            prop["agent_email"] = primary_agent.get("primaryEmailAddress", "")
            prop["agent_vanity_email"] = primary_agent.get("vanityEmailAddress", "")
            prop["agent_photo_url"] = primary_agent.get("defaultPhotoUrl", "")
            
            # Agent's company
            agent_company = primary_agent.get("company", {})
            prop["company_id"] = agent_company.get("companyGuid", "")
            prop["company_name"] = agent_company.get("companyName", "")
            prop["company_code"] = agent_company.get("companyId", "")
            
            # Agent's primary office
            agent_office = primary_agent.get("primaryOffice", {})
            prop["agent_office_id"] = agent_office.get("officeGuid", "")
            prop["agent_office_code"] = agent_office.get("officeId", "")
            
            # Listing office (direct from listing)
            listing_office = listing.get("office", {})
            prop["listing_office_id"] = listing_office.get("officeGuid", "")
            prop["listing_office_code"] = listing_office.get("officeId", "")
            
            # Source identifier and office key
            prop["source"] = "dash_sothebys"
            prop["office_key"] = self.office_key
            
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
                media["description"] = media_item.get("description", "")
                media["html_description"] = media_item.get("htmlDescription", "")
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
                
                # Source identifier and office key
                media["source"] = "dash_sothebys"
                media["office_key"] = self.office_key
                
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
    
    async def load_properties(self, properties: list, append: bool = False):
        """Load properties into dash_bronze.properties table."""
        if not properties:
            print("⚠️  No properties to load")
            return
        
        columns = list(properties[0].keys())
        columns_str = ", ".join([f"`{col}`" for col in columns])
        
        # Build VALUES clause
        values_clauses = []
        for prop in properties:
            values = []
            for col in columns:
                val = prop.get(col, "")
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
        
        if not append:
            # Drop and recreate (full refresh mode)
            drop_table_sql = f"DROP TABLE IF EXISTS {self.catalog}.{self.schema}.properties"
            await self.execute_query(drop_table_sql)
            await self.execute_query(create_table_sql)
        
        # Insert in batches
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
    
    async def load_media(self, media_items: list, append: bool = False):
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
        
        if not append:
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
    
    async def delete_by_office_key(self, office_key: str):
        """Delete all records for a specific office_key from bronze tables."""
        print(f"🗑️  Deleting old data for office_key: {office_key}")
        
        # Delete from properties table
        try:
            delete_properties_sql = f"""
                DELETE FROM {self.catalog}.{self.schema}.properties
                WHERE office_key = '{office_key}'
            """
            await self.execute_query(delete_properties_sql)
            print(f"✅ Deleted properties with office_key = '{office_key}'")
        except Exception as e:
            if "TABLE_OR_VIEW_NOT_FOUND" in str(e) or "does not exist" in str(e).lower():
                print(f"⚠️  Properties table doesn't exist yet, skipping delete")
            else:
                raise
        
        # Delete from media table
        try:
            delete_media_sql = f"""
                DELETE FROM {self.catalog}.{self.schema}.media
                WHERE office_key = '{office_key}'
            """
            await self.execute_query(delete_media_sql)
            print(f"✅ Deleted media with office_key = '{office_key}'")
        except Exception as e:
            if "TABLE_OR_VIEW_NOT_FOUND" in str(e) or "does not exist" in str(e).lower():
                print(f"⚠️  Media table doesn't exist yet, skipping delete")
            else:
                raise
        
        # Delete from processed_files table
        try:
            delete_files_sql = f"""
                DELETE FROM {self.catalog}.{self.schema}.processed_files
                WHERE office_key = '{office_key}'
            """
            await self.execute_query(delete_files_sql)
            print(f"✅ Deleted processed_files tracking for office_key = '{office_key}'")
        except Exception as e:
            if "TABLE_OR_VIEW_NOT_FOUND" in str(e) or "does not exist" in str(e).lower():
                print(f"⚠️  Processed_files table doesn't exist yet, skipping delete")
            else:
                raise
    
    async def load_file(self, json_file: Path, country_code: Optional[str] = None, append: bool = False, delete_old: bool = False) -> int:
        """Load Dash JSON file into Databricks Bronze. Returns record count.
        
        Args:
            json_file: Path to JSON file to load
            country_code: Optional country code override
            append: If True, append to existing data. If False, full refresh (drops table).
            delete_old: If True, delete old data for this office_key before loading (safer than full refresh).
        """
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
        print(f"🏢 Office key: {self.office_key}")
        
        # Ensure schema exists
        await self.ensure_schema_exists()
        
        # Delete old data for this office_key if requested
        if delete_old:
            await self.delete_by_office_key(self.office_key)
            # After deleting, we should append (not full refresh) to preserve other office_keys
            append = True
        
        # Transform data
        print("\n🔄 Transforming properties...")
        properties = self.transform_dash_to_bronze_properties(listings, country_code or "HU")
        
        print("🔄 Transforming media...")
        media_items = self.transform_dash_to_bronze_media(listings)
        
        # Load into Databricks
        print("\n💾 Loading properties into Databricks...")
        await self.load_properties(properties, append=append)
        
        print("\n💾 Loading media into Databricks...")
        await self.load_media(media_items, append=append)
        
        print(f"\n✅ Dash Bronze load complete for {json_file.name}!")
        return len(listings)
    
    async def load_all_new_files(self, force: bool = False) -> int:
        """
        Auto-scan source directory and load all new/changed files.
        Returns total number of records processed.
        """
        if not self.source_dir:
            print("❌ DASH_SOURCE_DIR not configured in .env")
            return 0
        
        if not self.source_dir.exists():
            print(f"❌ Source directory not found: {self.source_dir}")
            return 0
        
        print(f"📁 Source directory: {self.source_dir}")
        print(f"🏢 Office key: {self.office_key}")
        
        # Ensure schema and tracking table exist
        await self.ensure_schema_exists()
        await self.ensure_tracking_table_exists()
        
        # Get processed files
        if force:
            print("⚠️  Force mode: reprocessing all files")
            processed = {}
        else:
            processed = await self.get_processed_files()
            print(f"📋 Already processed: {len(processed)} files")
        
        # Find new files
        new_files = self.find_new_files(processed)
        
        if not new_files:
            print("✅ No new files to process")
            return 0
        
        print(f"📥 Found {len(new_files)} new/changed files to process:")
        for f in new_files:
            print(f"   - {f.name}")
        
        # Process files - first file does full refresh, subsequent append
        total_records = 0
        for i, json_file in enumerate(new_files):
            print(f"\n{'='*60}")
            print(f"Processing file {i+1}/{len(new_files)}: {json_file.name}")
            print(f"{'='*60}")
            
            try:
                # First file = full refresh, rest = append
                append = (i > 0)
                record_count = await self.load_file(json_file, append=append)
                total_records += record_count
                
                # Mark as processed
                file_hash = self.compute_file_hash(json_file)
                await self.mark_file_processed(json_file.name, file_hash, record_count)
                print(f"✅ Marked {json_file.name} as processed")
                
            except Exception as e:
                print(f"❌ Error processing {json_file.name}: {e}")
                raise
        
        print(f"\n{'='*60}")
        print(f"✅ Processed {len(new_files)} files, {total_records} total records")
        print(f"{'='*60}")
        
        return total_records


async def main():
    parser = argparse.ArgumentParser(description="Load Dash JSON data into Databricks Bronze")
    parser.add_argument("--file", type=str, help="Specific JSON file to load (optional)")
    parser.add_argument("--country", type=str, help="Country code override (e.g., HU, CY)")
    parser.add_argument("--force", action="store_true", help="Force reprocess all files")
    parser.add_argument("--delete-old", action="store_true", help="Delete old data for office_key before loading (use with --file)")
    
    args = parser.parse_args()
    
    loader = DashBronzeLoader()
    
    if args.file:
        # Process specific file
        json_path = Path(args.file)
        if not json_path.is_absolute():
            # Check source dir first, then relative to script
            if loader.source_dir and (loader.source_dir / json_path).exists():
                json_path = loader.source_dir / json_path
            else:
                json_path = Path(__file__).parent.parent / json_path
        
        await loader.load_file(json_path, args.country, delete_old=args.delete_old)
    else:
        # Auto-scan and process all new files
        await loader.load_all_new_files(force=args.force)


if __name__ == "__main__":
    asyncio.run(main())
