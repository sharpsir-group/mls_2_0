# Copyright 2025 SharpSir Group
# Licensed under the Apache License, Version 2.0
# See LICENSE file for details.
"""
RESO Web API Configuration

Multi-tenant OAuth support with office-based data isolation.
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
import os


# Find the .env file in parent directory (mls_2_0/.env)
API_DIR = Path(__file__).parent
MLS2_ROOT = API_DIR.parent
ENV_FILE = MLS2_ROOT / ".env"


@dataclass
class OAuthClient:
    """OAuth client configuration with office-based access control."""
    client_id: str
    client_secret: str
    offices: list[str]  # List of allowed OriginatingSystemOfficeKey values (e.g., ['CSIR', 'HSIR'])
    
    def has_office_access(self, office_key: str) -> bool:
        """Check if client has access to a specific office."""
        return office_key in self.offices


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
    query_timeout_seconds: int = 30  # Databricks SQL API limit: 5-50 seconds
    
    # CORS settings
    cors_origins: list = ["*"]
    
    # Qobrix API base URL for media files
    qobrix_api_base_url: str = ""
    
    # Qobrix default currency (ISO 4217 code) - set in .env
    qobrix_default_currency: str = ""
    
    # Qobrix API office key (e.g., CSIR for Cyprus SIR)
    qobrix_api_office_key: str = "CSIR"
    
    # MLS List Office Key (brokerage identity for RESO exports)
    mls_list_office_key: str = "SHARP_SIR"
    
    # Dash Loader Settings
    dash_source_dir: str = ""  # Directory containing Dash JSON source files
    dash_office_key: str = "HSIR"  # OriginatingSystemOfficeKey for Dash data
    
    # OAuth 2.0 Client Credentials (RESO compliant)
    # Generate with: openssl rand -hex 32
    oauth_jwt_secret: str = ""  # For signing JWT tokens
    oauth_token_expire_minutes: int = 60  # Token expiry (default: 1 hour)
    
    # Primary OAuth client (OAUTH_CLIENT_ID, OAUTH_CLIENT_SECRET, OAUTH_CLIENT_OFFICES)
    # 
    # BACKWARD COMPATIBILITY:
    # - If OAUTH_CLIENT_OFFICES is not set (empty), client sees ALL data (no filtering)
    # - Existing clients can continue without changes to .env
    # - To enable office filtering, set OAUTH_CLIENT_OFFICES (e.g., "CSIR")
    # - NOTE: Office filtering requires OriginatingSystemOfficeKey column in tables
    #   (run ETL notebooks after updating to add this column)
    oauth_client_id: str = ""
    oauth_client_secret: str = ""
    oauth_client_offices: str = ""  # Comma-separated list of offices (e.g., "CSIR" or "CSIR,HSIR")
    
    # Additional OAuth clients (OAUTH_CLIENT_2_*, OAUTH_CLIENT_3_*, etc.)
    oauth_client_2_id: str = ""
    oauth_client_2_secret: str = ""
    oauth_client_2_offices: str = ""
    
    oauth_client_3_id: str = ""
    oauth_client_3_secret: str = ""
    oauth_client_3_offices: str = ""
    
    oauth_client_4_id: str = ""
    oauth_client_4_secret: str = ""
    oauth_client_4_offices: str = ""
    
    oauth_client_5_id: str = ""
    oauth_client_5_secret: str = ""
    oauth_client_5_offices: str = ""
    
    @property
    def oauth_enabled(self) -> bool:
        """Check if OAuth is configured (at least one client with JWT secret)."""
        return bool(self.oauth_jwt_secret and self.oauth_client_id and self.oauth_client_secret)
    
    def get_oauth_clients(self) -> list[OAuthClient]:
        """
        Get all configured OAuth clients.
        
        Parses primary client (OAUTH_CLIENT_*) and additional clients (OAUTH_CLIENT_N_*).
        Returns list of OAuthClient objects with their allowed offices.
        """
        clients = []
        
        # Primary client
        if self.oauth_client_id and self.oauth_client_secret:
            offices = [o.strip() for o in self.oauth_client_offices.split(",") if o.strip()]
            clients.append(OAuthClient(
                client_id=self.oauth_client_id,
                client_secret=self.oauth_client_secret,
                offices=offices
            ))
        
        # Additional clients (2-5)
        client_configs = [
            (self.oauth_client_2_id, self.oauth_client_2_secret, self.oauth_client_2_offices),
            (self.oauth_client_3_id, self.oauth_client_3_secret, self.oauth_client_3_offices),
            (self.oauth_client_4_id, self.oauth_client_4_secret, self.oauth_client_4_offices),
            (self.oauth_client_5_id, self.oauth_client_5_secret, self.oauth_client_5_offices),
        ]
        
        for client_id, client_secret, client_offices in client_configs:
            if client_id and client_secret:
                offices = [o.strip() for o in client_offices.split(",") if o.strip()]
                clients.append(OAuthClient(
                    client_id=client_id,
                    client_secret=client_secret,
                    offices=offices
                ))
        
        return clients
    
    def get_client_by_id(self, client_id: str) -> Optional[OAuthClient]:
        """
        Look up an OAuth client by client_id.
        
        Returns OAuthClient if found, None otherwise.
        """
        for client in self.get_oauth_clients():
            if client.client_id == client_id:
                return client
        return None
    
    def validate_client_credentials(self, client_id: str, client_secret: str) -> Optional[OAuthClient]:
        """
        Validate client credentials and return the client if valid.
        
        Returns OAuthClient if credentials match, None otherwise.
        """
        for client in self.get_oauth_clients():
            if client.client_id == client_id and client.client_secret == client_secret:
                return client
        return None


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
