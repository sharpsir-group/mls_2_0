"""
RESO ShowingAppointment Resource Router
"""
from typing import Optional, Any
from fastapi import APIRouter, Query, Request
from .base import execute_odata_query, get_entity_by_key


router = APIRouter(prefix="/odata", tags=["ShowingAppointment"])

TABLE_NAME = "showing_appointment"
RESOURCE_NAME = "ShowingAppointment"
KEY_COLUMN = "ShowingAppointmentKey"


@router.get("/ShowingAppointment")
async def list_showings(
    request: Request,
    filter: Optional[str] = Query(None, alias="$filter"),
    select: Optional[str] = Query(None, alias="$select"),
    orderby: Optional[str] = Query(None, alias="$orderby"),
    top: Optional[int] = Query(None, alias="$top"),
    skip: Optional[int] = Query(None, alias="$skip"),
    count: bool = Query(False, alias="$count")
) -> dict[str, Any]:
    """
    Query RESO ShowingAppointment resources.
    
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
        base_url=base_url
    )


@router.get("/ShowingAppointment('{showing_key}')")
async def get_showing(
    request: Request,
    showing_key: str
) -> dict[str, Any]:
    """Get a single ShowingAppointment by ShowingAppointmentKey."""
    base_url = str(request.base_url).rstrip("/")
    return await get_entity_by_key(
        table_name=TABLE_NAME,
        resource_name=RESOURCE_NAME,
        key_column=KEY_COLUMN,
        key_value=showing_key,
        base_url=base_url
    )

