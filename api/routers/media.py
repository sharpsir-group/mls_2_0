"""
RESO Media Resource Router
"""
from typing import Optional, Any
from fastapi import APIRouter, Query, Request
from .base import execute_odata_query, get_entity_by_key


router = APIRouter(prefix="/odata", tags=["Media"])

TABLE_NAME = "media"
RESOURCE_NAME = "Media"
KEY_COLUMN = "MediaKey"


@router.get("/Media")
async def list_media(
    request: Request,
    filter: Optional[str] = Query(None, alias="$filter"),
    select: Optional[str] = Query(None, alias="$select"),
    orderby: Optional[str] = Query(None, alias="$orderby"),
    top: Optional[int] = Query(None, alias="$top"),
    skip: Optional[int] = Query(None, alias="$skip"),
    count: bool = Query(False, alias="$count")
) -> dict[str, Any]:
    """
    Query RESO Media resources.
    
    ## RESO Fields
    
    MediaKey, ResourceRecordKey, ResourceName, MediaURL, MediaType,
    MediaCategory, Order, ShortDescription
    
    ## Common Filters
    
    - `$filter=ResourceRecordKey eq 'PROP123'` - Get media for a property
    - `$filter=MediaCategory eq 'Photo'` - Get only photos
    """
    base_url = str(request.base_url).rstrip("/")
    return await execute_odata_query(
        table_name=TABLE_NAME,
        resource_name=RESOURCE_NAME,
        filter=filter,
        select=select,
        orderby=orderby,
        top=top,
        skip=skip,
        count=count,
        base_url=base_url
    )


@router.get("/Media('{media_key}')")
async def get_media(
    request: Request,
    media_key: str
) -> dict[str, Any]:
    """Get a single Media by MediaKey."""
    base_url = str(request.base_url).rstrip("/")
    return await get_entity_by_key(
        table_name=TABLE_NAME,
        resource_name=RESOURCE_NAME,
        key_column=KEY_COLUMN,
        key_value=media_key,
        base_url=base_url
    )

