# Copyright 2025 SharpSir Group
# Licensed under the Apache License, Version 2.0
# See LICENSE file for details.
"""
RESO Property Resource Router

Endpoints:
- GET /odata/Property - List properties with OData query
- GET /odata/Property('{key}') - Get single property by ListingKey
"""
from typing import Optional, Any
from fastapi import APIRouter, Query, Request
from .base import execute_odata_query, get_entity_by_key
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import get_settings


router = APIRouter(prefix="/odata", tags=["Property"])

TABLE_NAME = "property"
RESOURCE_NAME = "Property"
KEY_COLUMN = "ListingKey"


def add_currency_code(data: dict[str, Any]) -> dict[str, Any]:
    """Add ListPriceCurrencyCode to property responses."""
    settings = get_settings()
    currency = settings.qobrix_default_currency
    
    if not currency:
        return data
    
    # Add to list response
    if "value" in data:
        for item in data["value"]:
            if "ListPrice" in item:
                item["ListPriceCurrencyCode"] = currency
    # Add to single entity response
    elif "ListPrice" in data:
        data["ListPriceCurrencyCode"] = currency
    
    return data


@router.get("/Property")
async def list_properties(
    request: Request,
    filter: Optional[str] = Query(None, alias="$filter", description="OData filter expression"),
    select: Optional[str] = Query(None, alias="$select", description="Comma-separated list of fields"),
    orderby: Optional[str] = Query(None, alias="$orderby", description="Sort order (e.g., 'ListPrice desc')"),
    top: Optional[int] = Query(None, alias="$top", description="Max records to return"),
    skip: Optional[int] = Query(None, alias="$skip", description="Records to skip"),
    count: bool = Query(False, alias="$count", description="Include total count")
) -> dict[str, Any]:
    """
    Query RESO Property resources.
    
    ## OData Query Examples
    
    - `$filter=StandardStatus eq 'Active'`
    - `$filter=ListPrice gt 100000 and BedroomsTotal ge 3`
    - `$filter=contains(City,'Miami')`
    - `$select=ListingKey,ListPrice,City,BedroomsTotal`
    - `$orderby=ListPrice desc`
    - `$top=50&$skip=100`
    - `$count=true`
    
    ## RESO Standard Fields
    
    ListingKey, ListingId, StandardStatus, PropertyType, PropertySubType,
    City, StateOrProvince, PostalCode, Country, StreetName, StreetNumber,
    ListPrice, OriginalListPrice, BedroomsTotal, BathroomsTotalInteger,
    LivingArea, LotSizeSquareFeet, YearBuilt, Latitude, Longitude, etc.
    
    ## Extension Fields (X_*)
    
    X_QobrixId, X_Reference, X_Status, X_ShortDescription, X_LongDescription, etc.
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
        base_url=base_url
    )
    return add_currency_code(result)


@router.get("/Property('{listing_key}')")
async def get_property(
    request: Request,
    listing_key: str
) -> dict[str, Any]:
    """
    Get a single Property by ListingKey.
    
    ## Example
    
    `GET /odata/Property('ABC123')`
    """
    base_url = str(request.base_url).rstrip("/")
    result = await get_entity_by_key(
        table_name=TABLE_NAME,
        resource_name=RESOURCE_NAME,
        key_column=KEY_COLUMN,
        key_value=listing_key,
        base_url=base_url
    )
    return add_currency_code(result)
