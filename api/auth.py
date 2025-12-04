# Copyright 2025 SharpSir Group
# Licensed under the Apache License, Version 2.0
# See LICENSE file for details.
"""
RESO Web API Authentication

OAuth 2.0 Client Credentials flow as required by RESO Web API Core.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException, Security, Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from starlette.status import HTTP_401_UNAUTHORIZED

from config import get_settings

# OAuth 2.0 Bearer Token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/oauth/token", auto_error=False)

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
    bearer_token: Optional[str] = Security(oauth2_scheme)
) -> dict:
    """
    Authenticate request using OAuth 2.0 Bearer Token.
    
    If OAuth is not configured, all requests are allowed.
    
    Returns:
        dict with auth info: {"method": "oauth"|"none", "client_id": ...}
    """
    settings = get_settings()
    
    # Check if OAuth is configured
    if not settings.oauth_enabled:
        # No auth configured - allow all requests
        return {"method": "none", "client_id": "anonymous"}
    
    # Require Bearer token
    if bearer_token:
        payload = verify_token(bearer_token)
        return {
            "method": "oauth",
            "client_id": payload.get("sub"),
            "scope": payload.get("scope", "")
        }
    
    # No token provided
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


# Dependency to use in routers
require_auth = Depends(authenticate)
