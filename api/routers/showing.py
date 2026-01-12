# Copyright 2025 SharpSir Group
# Licensed under the Apache License, Version 2.0
# See LICENSE file for details.
"""
RESO ShowingAppointment Resource Router

Data is filtered by OriginatingSystemOfficeKey based on authenticated client's office access.
"""
from typing import Optional, Any
from fastapi import APIRouter, Query, Request, Depends
from .base import execute_odata_query, get_entity_by_key
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from auth import AuthContext, get_auth_context


router = APIRouter(prefix="/odata", tags=["ShowingAppointment"])

TABLE_NAME = "showing_appointment"
RESOURCE_NAME = "ShowingAppointment"
KEY_COLUMN = "ShowingAppointmentKey"


@router.get("/ShowingAppointment")
async def list_showings(
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
    Query RESO ShowingAppointment resources.
    
    Data is filtered by client's allowed offices (OriginatingSystemOfficeKey).
    
    ## RESO Fields
    
    ShowingAppointmentKey, ListingKey, ShowingAgentKey, ShowingDate,
    ShowingStartTime, ShowingEndTime, ShowingStatus, ShowingRemarks
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
        base_url=base_url,
        allowed_offices=auth.offices
    )


@router.get("/ShowingAppointment('{showing_key}')")
async def get_showing(
    request: Request,
    showing_key: str,
    auth: AuthContext = Depends(get_auth_context)
) -> dict[str, Any]:
    """Get a single ShowingAppointment by ShowingAppointmentKey."""
    base_url = str(request.base_url).rstrip("/")
    return await get_entity_by_key(
        table_name=TABLE_NAME,
        resource_name=RESOURCE_NAME,
        key_column=KEY_COLUMN,
        key_value=showing_key,
        base_url=base_url,
        allowed_offices=auth.offices
    )

