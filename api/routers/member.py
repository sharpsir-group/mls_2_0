# Copyright 2025 SharpSir Group
# Licensed under the Apache License, Version 2.0
# See LICENSE file for details.
"""
RESO Member Resource Router

Endpoints:
- GET /odata/Member - List members with OData query
- GET /odata/Member('{key}') - Get single member by MemberKey
"""
from typing import Optional, Any
from fastapi import APIRouter, Query, Request
from .base import execute_odata_query, get_entity_by_key


router = APIRouter(prefix="/odata", tags=["Member"])

TABLE_NAME = "member"
RESOURCE_NAME = "Member"
KEY_COLUMN = "MemberKey"


@router.get("/Member")
async def list_members(
    request: Request,
    filter: Optional[str] = Query(None, alias="$filter"),
    select: Optional[str] = Query(None, alias="$select"),
    orderby: Optional[str] = Query(None, alias="$orderby"),
    top: Optional[int] = Query(None, alias="$top"),
    skip: Optional[int] = Query(None, alias="$skip"),
    count: bool = Query(False, alias="$count")
) -> dict[str, Any]:
    """
    Query RESO Member resources.
    
    ## RESO Fields
    
    MemberKey, MemberMlsId, MemberFirstName, MemberLastName, MemberFullName,
    MemberEmail, MemberDirectPhone, MemberMobilePhone, MemberStateLicense,
    MemberStatus, OfficeName, OfficeKey
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


@router.get("/Member('{member_key}')")
async def get_member(
    request: Request,
    member_key: str
) -> dict[str, Any]:
    """Get a single Member by MemberKey."""
    base_url = str(request.base_url).rstrip("/")
    return await get_entity_by_key(
        table_name=TABLE_NAME,
        resource_name=RESOURCE_NAME,
        key_column=KEY_COLUMN,
        key_value=member_key,
        base_url=base_url
    )

