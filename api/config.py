# Copyright 2025 SharpSir Group
# Licensed under the Apache License, Version 2.0
# See LICENSE file for details.
"""
RESO Web API Configuration
"""
import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


# Find the .env file in parent directory (mls_2_0/.env)
API_DIR = Path(__file__).parent
MLS2_ROOT = API_DIR.parent
ENV_FILE = MLS2_ROOT / ".env"



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
    
    # API settings
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
    
    # API Keys for authentication (comma-separated list) - Legacy support
    # Example: API_KEYS=key1,key2,key3
    api_keys: str = ""
    
    # OAuth 2.0 Client Credentials (RESO compliant)
    # Generate with: openssl rand -hex 32
    oauth_client_id: str = ""
    oauth_client_secret: str = ""
    oauth_jwt_secret: str = ""  # For signing JWT tokens
    oauth_token_expire_minutes: int = 60  # Token expiry (default: 1 hour)
    
    @property
    def api_keys_list(self) -> list:
        """Parse API keys from comma-separated string."""
        if not self.api_keys:
            return []
        return [k.strip() for k in self.api_keys.split(",") if k.strip()]
    
    @property
    def oauth_enabled(self) -> bool:
        """Check if OAuth is configured."""
        return bool(self.oauth_client_id and self.oauth_client_secret and self.oauth_jwt_secret)


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

