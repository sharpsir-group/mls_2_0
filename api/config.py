# Copyright 2025 SharpSir Group
# Licensed under the Apache License, Version 2.0
# See LICENSE file for details.
"""
RESO Web API Configuration

Multi-tenant OAuth support with office-based data isolation.
Supports multiple data sources (Qobrix, DASH API, DASH JSON).
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from dotenv import load_dotenv
import os
import re


# Find the .env file in parent directory (mls_2_0/.env)
API_DIR = Path(__file__).parent
MLS2_ROOT = API_DIR.parent
ENV_FILE = MLS2_ROOT / ".env"

# Load .env into os.environ for SRC_* and OAUTH_CLIENT_* parsing
if ENV_FILE.exists():
    load_dotenv(ENV_FILE, override=True)


@dataclass
class DataSource:
    """
    Data source configuration aligned with RESO Data Dictionary.
    
    Attributes:
        office_key: OriginatingSystemOfficeKey (e.g., SHARPSIR-CY-001)
        system_name: OriginatingSystemName (e.g., Cyprus Sotheby's International Realty)
        system_id: OriginatingSystemID (e.g., QOBRIX_CY)
        source_type: QOBRIX, DASH_API, or DASH_JSON
        country: ISO 3166-1 alpha-2 country code
        
    Type-specific attributes:
        currency: Currency code for QOBRIX sources
        api_user: API user for QOBRIX sources
        api_key: API key for QOBRIX/DASH sources
        api_url: API URL for QOBRIX/DASH sources
        source_dir: Directory for DASH_JSON sources
        dash_office_guid: Office GUID for DASH_API sources
        dash_okta_client_id: Okta client ID for DASH_API sources
        dash_okta_client_secret: Okta secret for DASH_API sources
        dash_okta_token_url: Okta token URL for DASH_API sources
        dash_okta_scope: Okta scope for DASH_API sources
    """
    office_key: str
    system_name: str
    system_id: str
    source_type: str  # QOBRIX, DASH_API, DASH_JSON
    country: str = ""
    
    # QOBRIX-specific
    currency: str = ""
    api_user: str = ""
    api_key: str = ""
    api_url: str = ""
    
    # DASH_JSON-specific
    source_dir: str = ""
    
    # DASH_API-specific
    dash_office_guid: str = ""
    dash_api_key: str = ""
    dash_okta_client_id: str = ""
    dash_okta_client_secret: str = ""
    dash_okta_token_url: str = ""
    dash_okta_scope: str = ""
    dash_api_url: str = ""


@dataclass
class OAuthClient:
    """OAuth client configuration with office-based access control."""
    client_id: str
    client_secret: str
    offices: list[str] = field(default_factory=list)
    
    def has_office_access(self, office_key: str) -> bool:
        """Check if client has access to a specific office."""
        # Empty offices list means access to ALL offices
        if not self.offices:
            return True
        return office_key in self.offices


def _parse_data_sources() -> list[DataSource]:
    """
    Parse SRC_N_* environment variables into DataSource objects.
    
    Expects pattern: SRC_1_OFFICE_KEY, SRC_1_TYPE, SRC_1_SYSTEM_NAME, etc.
    """
    sources = []
    
    # Find all source indices (SRC_1, SRC_2, etc.)
    source_indices = set()
    for key in os.environ:
        match = re.match(r'^SRC_(\d+)_', key)
        if match:
            source_indices.add(int(match.group(1)))
    
    for idx in sorted(source_indices):
        prefix = f"SRC_{idx}_"
        
        office_key = os.getenv(f"{prefix}OFFICE_KEY", "")
        source_type = os.getenv(f"{prefix}TYPE", "")
        
        if not office_key or not source_type:
            continue
        
        source = DataSource(
            office_key=office_key,
            system_name=os.getenv(f"{prefix}SYSTEM_NAME", ""),
            system_id=os.getenv(f"{prefix}SYSTEM_ID", ""),
            source_type=source_type,
            country=os.getenv(f"{prefix}COUNTRY", ""),
            # QOBRIX
            currency=os.getenv(f"{prefix}CURRENCY", ""),
            api_user=os.getenv(f"{prefix}API_USER", ""),
            api_key=os.getenv(f"{prefix}API_KEY", ""),
            api_url=os.getenv(f"{prefix}API_URL", ""),
            # DASH_JSON
            source_dir=os.getenv(f"{prefix}DIR", ""),
            # DASH_API
            dash_office_guid=os.getenv(f"{prefix}DASH_OFFICE_GUID", ""),
            dash_api_key=os.getenv(f"{prefix}DASH_API_KEY", ""),
            dash_okta_client_id=os.getenv(f"{prefix}DASH_OKTA_CLIENT_ID", ""),
            dash_okta_client_secret=os.getenv(f"{prefix}DASH_OKTA_CLIENT_SECRET", ""),
            dash_okta_token_url=os.getenv(f"{prefix}DASH_OKTA_TOKEN_URL", ""),
            dash_okta_scope=os.getenv(f"{prefix}DASH_OKTA_SCOPE", ""),
            dash_api_url=os.getenv(f"{prefix}DASH_API_URL", ""),
        )
        sources.append(source)
    
    return sources


def _parse_oauth_clients() -> list[OAuthClient]:
    """
    Parse OAUTH_CLIENT_N_* environment variables into OAuthClient objects.
    
    Expects pattern: OAUTH_CLIENT_1_ID, OAUTH_CLIENT_1_SECRET, OAUTH_CLIENT_1_OFFICES
    """
    clients = []
    
    # Find all client indices
    client_indices = set()
    for key in os.environ:
        match = re.match(r'^OAUTH_CLIENT_(\d+)_', key)
        if match:
            client_indices.add(int(match.group(1)))
    
    for idx in sorted(client_indices):
        prefix = f"OAUTH_CLIENT_{idx}_"
        
        client_id = os.getenv(f"{prefix}ID", "")
        client_secret = os.getenv(f"{prefix}SECRET", "")
        
        if not client_id or not client_secret:
            continue
        
        offices_str = os.getenv(f"{prefix}OFFICES", "")
        offices = [o.strip() for o in offices_str.split(",") if o.strip()]
        
        clients.append(OAuthClient(
            client_id=client_id,
            client_secret=client_secret,
            offices=offices
        ))
    
    return clients


class Settings(BaseSettings):
    """API Configuration from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE) if ENV_FILE.exists() else None,
        env_file_encoding="utf-8",
        extra="ignore"
    )
    
    # Databricks connection
    databricks_host: str = ""
    databricks_token: str = ""
    databricks_warehouse_id: str = ""
    databricks_catalog: str = "mls2"
    databricks_schema: str = "reso_gold"
    
    # API server settings
    reso_api_host: str = "0.0.0.0"
    reso_api_port: int = 3900
    
    # API metadata
    api_title: str = "RESO Web API"
    api_version: str = "2.0.0"
    api_description: str = "RESO Data Dictionary 2.0 compliant API for MLS data"
    
    # Query limits
    max_page_size: int = 1000
    default_page_size: int = 100
    query_timeout_seconds: int = 30
    
    # CORS settings
    cors_origins: list = ["*"]
    
    # Main brokerage identity (RESO ListOfficeKey)
    list_office_key: str = ""
    list_office_name: str = ""
    
    # Qobrix API settings (for URL transformation)
    qobrix_default_currency: str = "EUR"
    qobrix_api_base_url: str = "https://sothebys6113.eu1.qobrix.com/api/v2"
    
    # OAuth 2.0 settings
    oauth_jwt_secret: str = ""
    oauth_token_expire_minutes: int = 60
    
    # Cached parsed data
    _data_sources: list[DataSource] = None
    _oauth_clients: list[OAuthClient] = None
    
    @property
    def oauth_enabled(self) -> bool:
        """Check if OAuth is configured."""
        return bool(self.oauth_jwt_secret and self.get_oauth_clients())
    
    def get_data_sources(self) -> list[DataSource]:
        """Get all configured data sources."""
        if self._data_sources is None:
            self._data_sources = _parse_data_sources()
        return self._data_sources
    
    def get_source_by_office_key(self, office_key: str) -> Optional[DataSource]:
        """Get a data source by its office key."""
        for source in self.get_data_sources():
            if source.office_key == office_key:
                return source
        return None
    
    def get_sources_by_type(self, source_type: str) -> list[DataSource]:
        """Get all data sources of a specific type (QOBRIX, DASH_API, DASH_JSON)."""
        return [s for s in self.get_data_sources() if s.source_type == source_type]
    
    def get_all_office_keys(self) -> list[str]:
        """Get all configured office keys."""
        return [s.office_key for s in self.get_data_sources()]
    
    def get_oauth_clients(self) -> list[OAuthClient]:
        """Get all configured OAuth clients."""
        if self._oauth_clients is None:
            self._oauth_clients = _parse_oauth_clients()
        return self._oauth_clients
    
    def get_client_by_id(self, client_id: str) -> Optional[OAuthClient]:
        """Look up an OAuth client by client_id."""
        for client in self.get_oauth_clients():
            if client.client_id == client_id:
                return client
        return None
    
    def validate_client_credentials(self, client_id: str, client_secret: str) -> Optional[OAuthClient]:
        """Validate client credentials and return the client if valid."""
        for client in self.get_oauth_clients():
            if client.client_id == client_id and client.client_secret == client_secret:
                return client
        return None


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
