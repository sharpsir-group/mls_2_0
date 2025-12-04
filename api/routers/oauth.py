# Copyright 2025 SharpSir Group
# Licensed under the Apache License, Version 2.0
# See LICENSE file for details.
"""
OAuth 2.0 Token Endpoint - RESO Web API Compliant

Implements OAuth 2.0 Client Credentials flow as required by RESO Web API Core.
https://transport.reso.org/proposals/web-api-core.html
"""
from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Form, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_401_UNAUTHORIZED

from config import get_settings
from auth import create_access_token

router = APIRouter(tags=["OAuth 2.0"])

# HTTP Basic auth for client credentials in Authorization header
security = HTTPBasic(auto_error=False)


class TokenResponse(BaseModel):
    """OAuth 2.0 Token Response per RFC 6749."""
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    scope: Optional[str] = None


class TokenError(BaseModel):
    """OAuth 2.0 Error Response per RFC 6749."""
    error: str
    error_description: Optional[str] = None


@router.post(
    "/oauth/token",
    response_model=TokenResponse,
    responses={
        400: {"model": TokenError, "description": "Invalid request"},
        401: {"model": TokenError, "description": "Invalid client credentials"}
    },
    summary="OAuth 2.0 Token Endpoint",
    description="""
    Obtain an access token using OAuth 2.0 Client Credentials flow.
    
    **RESO Web API Core Compliant**
    
    ## Authentication Methods
    
    ### Method 1: HTTP Basic Auth (Recommended)
    ```
    Authorization: Basic base64(client_id:client_secret)
    ```
    
    ### Method 2: Form Body
    ```
    grant_type=client_credentials
    client_id=your_client_id
    client_secret=your_client_secret
    ```
    
    ## Example Request
    ```bash
    curl -X POST https://your-server.com/reso/oauth/token \\
      -u "client_id:client_secret" \\
      -d "grant_type=client_credentials"
    ```
    
    ## Example Response
    ```json
    {
      "access_token": "eyJhbGciOiJIUzI1NiIs...",
      "token_type": "Bearer",
      "expires_in": 3600
    }
    ```
    """
)
async def token(
    grant_type: str = Form(..., description="Must be 'client_credentials'"),
    client_id: Optional[str] = Form(None, description="Client ID (if not using Basic Auth)"),
    client_secret: Optional[str] = Form(None, description="Client Secret (if not using Basic Auth)"),
    scope: Optional[str] = Form(None, description="Requested scope (optional)"),
    credentials: Optional[HTTPBasicCredentials] = Depends(security)
):
    """
    OAuth 2.0 Token Endpoint - Client Credentials Grant.
    
    Supports client authentication via:
    1. HTTP Basic Authentication header (recommended)
    2. Form body parameters (client_id, client_secret)
    """
    settings = get_settings()
    
    # Check if OAuth is configured
    if not settings.oauth_enabled:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail={
                "error": "server_error",
                "error_description": "OAuth is not configured. Set OAUTH_CLIENT_ID, OAUTH_CLIENT_SECRET, and OAUTH_JWT_SECRET in .env"
            }
        )
    
    # Validate grant_type
    if grant_type != "client_credentials":
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail={
                "error": "unsupported_grant_type",
                "error_description": "Only 'client_credentials' grant type is supported"
            }
        )
    
    # Get client credentials from Basic Auth or form body
    if credentials:
        # HTTP Basic Auth
        auth_client_id = credentials.username
        auth_client_secret = credentials.password
    elif client_id and client_secret:
        # Form body
        auth_client_id = client_id
        auth_client_secret = client_secret
    else:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail={
                "error": "invalid_client",
                "error_description": "Client credentials required via Basic Auth or form body"
            },
            headers={"WWW-Authenticate": "Basic"}
        )
    
    # Validate credentials
    if auth_client_id != settings.oauth_client_id or auth_client_secret != settings.oauth_client_secret:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail={
                "error": "invalid_client",
                "error_description": "Invalid client credentials"
            },
            headers={"WWW-Authenticate": "Basic"}
        )
    
    # Create access token
    token_data = {
        "sub": auth_client_id,
        "scope": scope or "odata"
    }
    
    expires_delta = timedelta(minutes=settings.oauth_token_expire_minutes)
    access_token = create_access_token(token_data, expires_delta)
    
    return TokenResponse(
        access_token=access_token,
        token_type="Bearer",
        expires_in=settings.oauth_token_expire_minutes * 60,  # Convert to seconds
        scope=scope
    )


@router.get(
    "/oauth/authorize",
    include_in_schema=True,
    summary="OAuth 2.0 Authorization (Not Supported)",
    description="Authorization Code flow is not supported. Use Client Credentials flow via POST /oauth/token."
)
async def authorize():
    """
    Authorization endpoint placeholder.
    
    RESO Web API uses Client Credentials flow which doesn't require this endpoint.
    """
    raise HTTPException(
        status_code=HTTP_400_BAD_REQUEST,
        detail={
            "error": "unsupported_response_type",
            "error_description": "This API uses Client Credentials flow. Use POST /oauth/token with grant_type=client_credentials"
        }
    )


