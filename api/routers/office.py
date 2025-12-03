# Copyright 2025 SharpSir Group
# Licensed under the Apache License, Version 2.0
# See LICENSE file for details.
"""
RESO Office Resource Router
"""
from typing import Optional, Any
from fastapi import APIRouter, Query, Request
from .base import execute_odata_query, get_entity_by_key


router = APIRouter(prefix="/odata", tags=["Office"])

TABLE_NAME = "office"
RESOURCE_NAME = "Office"
KEY_COLUMN = "OfficeKey"


@router.get("/Office")
async def list_offices(
    request: Request,
    filter: Optional[str] = Query(None, alias="$filter"),
    select: Optional[str] = Query(None, alias="$select"),
    orderby: Optional[str] = Query(None, alias="$orderby"),
    top: Optional[int] = Query(None, alias="$top"),
    skip: Optional[int] = Query(None, alias="$skip"),
    count: bool = Query(False, alias="$count")
) -> dict[str, Any]:
    """
    Query RESO Office resources.
    
    ## RESO Fields
    
    OfficeKey, OfficeMlsId, OfficeName, OfficePhone, OfficeEmail,
    OfficeAddress1, OfficeCity, OfficeStateOrProvince, OfficePostalCode, OfficeStatus
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


@router.get("/Office('{office_key}')")
async def get_office(
    request: Request,
    office_key: str
) -> dict[str, Any]:
    """Get a single Office by OfficeKey."""
    base_url = str(request.base_url).rstrip("/")
    return await get_entity_by_key(
        table_name=TABLE_NAME,
        resource_name=RESOURCE_NAME,
        key_column=KEY_COLUMN,
        key_value=office_key,
        base_url=base_url
    )

