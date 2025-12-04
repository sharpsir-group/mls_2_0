# Copyright 2025 SharpSir Group
# Licensed under the Apache License, Version 2.0
# See LICENSE file for details.
"""
RESO Web API Authentication

Supports:
1. OAuth 2.0 Bearer Token (RESO compliant) - Recommended
2. API Key (legacy) - For backward compatibility

RESO Web API Core requires OAuth 2.0 Client Credentials flow.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException, Security, Depends
from fastapi.security import APIKeyHeader, APIKeyQuery, OAuth2PasswordBearer
from jose import JWTError, jwt
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN

from config import get_settings

# OAuth 2.0 Bearer Token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/oauth/token", auto_error=False)

# Legacy API Key support
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
api_key_query = APIKeyQuery(name="api_key", auto_error=False)

# JWT Algorithm
ALGORITHM = "HS256"


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: Payload to encode in the token
        expires_delta: Token expiry time
        
    Returns:
        Encoded JWT token string
    """
    settings = get_settings()
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.oauth_token_expire_minutes)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "iss": "reso-web-api",
        "aud": "reso-api-client"
    })
    
    encoded_jwt = jwt.encode(to_encode, settings.oauth_jwt_secret, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> dict:
    """
    Verify and decode a JWT token.
    
    Args:
        token: JWT token string
        
    Returns:
        Decoded token payload
        
    Raises:
        HTTPException: If token is invalid or expired
    """
    settings = get_settings()
    
    try:
        payload = jwt.decode(
            token, 
            settings.oauth_jwt_secret, 
            algorithms=[ALGORITHM],
            audience="reso-api-client"
        )
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "InvalidToken",
                    "message": f"Token validation failed: {str(e)}"
                }
            },
            headers={"WWW-Authenticate": "Bearer"}
        )


async def authenticate(
    bearer_token: Optional[str] = Security(oauth2_scheme),
    api_key_header_value: Optional[str] = Security(api_key_header),
    api_key_query_value: Optional[str] = Security(api_key_query)
) -> dict:
    """
    Authenticate request using OAuth 2.0 Bearer Token or legacy API Key.
    
    Authentication methods (in order of precedence):
    1. OAuth 2.0 Bearer Token (Authorization: Bearer <token>) - RESO compliant
    2. API Key Header (X-API-Key: <key>) - Legacy
    3. API Key Query (?api_key=<key>) - Legacy
    
    If no authentication is configured, all requests are allowed.
    
    Returns:
        dict with auth info: {"method": "oauth"|"api_key"|"none", "client_id": ...}
    """
    settings = get_settings()
    
    # Check if any auth is configured
    auth_configured = settings.oauth_enabled or settings.api_keys_list
    
    if not auth_configured:
        # No auth configured - allow all requests
        return {"method": "none", "client_id": "anonymous"}
    
    # 1. Try OAuth 2.0 Bearer Token first (RESO compliant)
    if bearer_token:
        payload = verify_token(bearer_token)
        return {
            "method": "oauth",
            "client_id": payload.get("sub"),
            "scope": payload.get("scope", "")
        }
    
    # 2. Try legacy API Key
    api_key = api_key_header_value or api_key_query_value
    
    if api_key and api_key in settings.api_keys_list:
        return {
            "method": "api_key",
            "client_id": api_key[:8] + "..."  # Masked for logging
        }
    
    # No valid auth provided
    if settings.oauth_enabled:
        # OAuth is configured - require Bearer token
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "Unauthorized",
                    "message": "Bearer token required. Use POST /oauth/token to obtain an access token."
                }
            },
            headers={"WWW-Authenticate": "Bearer"}
        )
    else:
        # Only API keys configured
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "Unauthorized",
                    "message": "API key required. Provide via X-API-Key header or api_key query parameter."
                }
            }
        )


# Dependency to use in routers
require_auth = Depends(authenticate)
