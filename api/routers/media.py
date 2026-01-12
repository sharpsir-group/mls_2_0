# Copyright 2025 SharpSir Group
# Licensed under the Apache License, Version 2.0
# See LICENSE file for details.
"""
RESO Media Resource Router

Data is filtered by OriginatingSystemOfficeKey based on authenticated client's office access.
"""
from typing import Optional, Any
from fastapi import APIRouter, Query, Request, Depends
from .base import execute_odata_query, get_entity_by_key
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import get_settings
from auth import AuthContext, get_auth_context


router = APIRouter(prefix="/odata", tags=["Media"])

TABLE_NAME = "media"
RESOURCE_NAME = "Media"
KEY_COLUMN = "MediaKey"


def transform_media_urls(data: dict[str, Any]) -> dict[str, Any]:
    """Transform relative MediaURL paths to full URLs."""
    settings = get_settings()
    
    # Extract base domain from QOBRIX_API_BASE_URL
    # e.g., https://sothebys6113.eu1.qobrix.com/api/v2 -> https://sothebys6113.eu1.qobrix.com
    base_url = settings.qobrix_api_base_url
    if base_url:
        # Remove trailing path to get just the domain
        if "/api/" in base_url:
            base_url = base_url.split("/api/")[0]
        elif base_url.endswith("/"):
            base_url = base_url.rstrip("/")
    
    if not base_url:
        return data
    
    # Transform URLs in the response
    if "value" in data:
        for item in data["value"]:
            if "MediaURL" in item and item["MediaURL"]:
                url = item["MediaURL"]
                if url.startswith("/"):
                    item["MediaURL"] = base_url + url
    elif "MediaURL" in data and data["MediaURL"]:
        url = data["MediaURL"]
        if url.startswith("/"):
            data["MediaURL"] = base_url + url
    
    return data


@router.get("/Media")
async def list_media(
    request: Request,
    auth: AuthContext = Depends(get_auth_context),
    filter: Optional[str] = Query(None, alias="$filter"),
    select: Optional[str] = Query(None, alias="$select"),
    orderby: Optional[str] = Query(None, alias="$orderby"),
    top: Optional[int] = Query(None, alias="$top"),
    skip: Optional[int] = Query(None, alias="$skip"),
    count: bool = Query(False, alias="$count")
) -> dict[str, Any]:
    """
    Query RESO Media resources.
    
    Data is filtered by client's allowed offices (OriginatingSystemOfficeKey).
    
    ## RESO Fields
    
    MediaKey, ResourceRecordKey, ResourceName, MediaURL, MediaType,
    MediaCategory, Order, ShortDescription
    
    ## Common Filters
    
    - `$filter=ResourceRecordKey eq 'PROP123'` - Get media for a property
    - `$filter=MediaCategory eq 'Photo'` - Get only photos
    """
    base_url = str(request.base_url).rstrip("/")
    result = await execute_odata_query(
        table_name=TABLE_NAME,
        resource_name=RESOURCE_NAME,
        filter=filter,
        select=select,
        orderby=orderby,
        top=top,
        skip=skip,
        count=count,
        base_url=base_url,
        allowed_offices=auth.offices
    )
    return transform_media_urls(result)


@router.get("/Media('{media_key}')")
async def get_media(
    request: Request,
    media_key: str,
    auth: AuthContext = Depends(get_auth_context)
) -> dict[str, Any]:
    """Get a single Media by MediaKey."""
    base_url = str(request.base_url).rstrip("/")
    result = await get_entity_by_key(
        table_name=TABLE_NAME,
        resource_name=RESOURCE_NAME,
        key_column=KEY_COLUMN,
        key_value=media_key,
        base_url=base_url,
        allowed_offices=auth.offices
    )
    return transform_media_urls(result)
