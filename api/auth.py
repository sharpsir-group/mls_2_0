# Copyright 2025 SharpSir Group
# Licensed under the Apache License, Version 2.0
# See LICENSE file for details.
"""
API Key Authentication for RESO Web API
"""
from fastapi import HTTPException, Security, Depends
from fastapi.security import APIKeyHeader, APIKeyQuery
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN
from config import get_settings

# API Key can be passed via header or query parameter
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
api_key_query = APIKeyQuery(name="api_key", auto_error=False)


async def get_api_key(
    api_key_header_value: str = Security(api_key_header),
    api_key_query_value: str = Security(api_key_query)
) -> str:
    """
    Validate API key from header or query parameter.
    
    API key can be provided via:
    - Header: X-API-Key: your-api-key
    - Query: ?api_key=your-api-key
    
    If no API keys are configured (API_KEYS is empty), authentication is disabled.
    """
    settings = get_settings()
    valid_keys = settings.api_keys_list
    
    # If no API keys configured, allow all requests (auth disabled)
    if not valid_keys:
        return "auth_disabled"
    
    # Check header first, then query parameter
    api_key = api_key_header_value or api_key_query_value
    
    if not api_key:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "Unauthorized",
                    "message": "API key required. Provide via X-API-Key header or api_key query parameter."
                }
            }
        )
    
    if api_key not in valid_keys:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "Forbidden",
                    "message": "Invalid API key."
                }
            }
        )
    
    return api_key


# Dependency to use in routers
require_api_key = Depends(get_api_key)

