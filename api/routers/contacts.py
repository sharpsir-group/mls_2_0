"""
RESO Contacts Resource Router
"""
from typing import Optional, Any
from fastapi import APIRouter, Query, Request
from .base import execute_odata_query, get_entity_by_key


router = APIRouter(prefix="/odata", tags=["Contacts"])

TABLE_NAME = "contacts"
RESOURCE_NAME = "Contacts"
KEY_COLUMN = "ContactKey"


@router.get("/Contacts")
async def list_contacts(
    request: Request,
    filter: Optional[str] = Query(None, alias="$filter"),
    select: Optional[str] = Query(None, alias="$select"),
    orderby: Optional[str] = Query(None, alias="$orderby"),
    top: Optional[int] = Query(None, alias="$top"),
    skip: Optional[int] = Query(None, alias="$skip"),
    count: bool = Query(False, alias="$count")
) -> dict[str, Any]:
    """
    Query RESO Contacts resources.
    
    ## RESO Fields
    
    ContactKey, ContactFirstName, ContactLastName, ContactFullName,
    ContactEmail, ContactPhone, ContactType, ContactStatus
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


@router.get("/Contacts('{contact_key}')")
async def get_contact(
    request: Request,
    contact_key: str
) -> dict[str, Any]:
    """Get a single Contact by ContactKey."""
    base_url = str(request.base_url).rstrip("/")
    return await get_entity_by_key(
        table_name=TABLE_NAME,
        resource_name=RESOURCE_NAME,
        key_column=KEY_COLUMN,
        key_value=contact_key,
        base_url=base_url
    )

