# Copyright 2025 SharpSir Group
# Licensed under the Apache License, Version 2.0
# See LICENSE file for details.
"""
Base router with shared OData query handling logic.

Supports office-based data filtering via OriginatingSystemOfficeKey.
"""
from typing import Any, Optional
from fastapi import Query, HTTPException
import sys
sys.path.insert(0, '..')
from services.databricks import get_databricks_connector
from services.odata_parser import get_odata_parser
from config import get_settings


# Fields that should be returned as numbers per RESO Data Dictionary
NUMERIC_FIELDS = {
    # Price fields
    'ListPrice', 'OriginalListPrice', 'ClosePrice', 'ListPriceLow', 'PreviousListPrice',
    'LeaseAmount', 'AssociationFee', 'AssociationFee2', 'TaxAnnualAmount',
    # Area/Size fields
    'LivingArea', 'LotSizeSquareFeet', 'LotSizeAcres', 'BuildingAreaTotal',
    'GarageSpaces', 'CarportSpaces', 'OpenParkingSpaces',
    # Room counts
    'BedroomsTotal', 'BathroomsTotalInteger', 'BathroomsFull', 'BathroomsHalf',
    'RoomsTotal', 'StoriesTotal', 'Flooring',
    # Location
    'Latitude', 'Longitude',
    # Year fields
    'YearBuilt', 'YearBuiltEffective',
    # Days on market
    'DaysOnMarket', 'CumulativeDaysOnMarket',
    # Media
    'Order', 'ImageWidth', 'ImageHeight', 'ImageSizeBytes',
}


def convert_numeric_fields(record: dict[str, Any]) -> dict[str, Any]:
    """Convert string numeric values to actual numbers per RESO spec."""
    for key, value in record.items():
        if key in NUMERIC_FIELDS and value is not None:
            try:
                # Try to convert to number
                if isinstance(value, str):
                    if '.' in value:
                        record[key] = float(value)
                    else:
                        record[key] = int(value)
            except (ValueError, TypeError):
                pass  # Keep original value if conversion fails
    return record


def build_office_filter(allowed_offices: list[str]) -> str:
    """
    Build SQL WHERE clause for office-based filtering.
    
    BACKWARD COMPATIBILITY:
    - If allowed_offices is empty or None, returns "" (no filter applied)
    - This ensures existing clients without OAUTH_CLIENT_OFFICES configured
      continue to see all data as before
    - Existing tokens without 'offices' claim also get empty list → no filter
    
    Args:
        allowed_offices: List of allowed OriginatingSystemOfficeKey values (e.g., ['CSIR', 'HSIR'])
        
    Returns:
        SQL condition string or empty string if no filter needed
    """
    if not allowed_offices:
        # No office filter - return all data
        # This maintains backward compatibility for:
        # 1. Clients without OAUTH_CLIENT_OFFICES configured
        # 2. Tokens issued before multi-tenant support (no 'offices' claim)
        # 3. Admin clients with access to all offices
        # 4. OAuth disabled scenarios
        return ""
    
    # Build IN clause with escaped values
    escaped_offices = [office.replace("'", "''") for office in allowed_offices]
    office_list = ", ".join(f"'{office}'" for office in escaped_offices)
    return f"OriginatingSystemOfficeKey IN ({office_list})"


def combine_filters(user_filter: Optional[str], office_filter: str) -> Optional[str]:
    """
    Combine user OData filter with office filter.
    
    Args:
        user_filter: User-provided $filter expression (may be None)
        office_filter: Office filter SQL condition
        
    Returns:
        Combined filter expression or None
    """
    if not office_filter:
        return user_filter
    
    if not user_filter:
        return office_filter
    
    # Combine with AND - office filter is already SQL, user filter will be converted
    # The OData parser will handle the user_filter, we wrap it with office filter
    return f"({user_filter}) AND {office_filter}"


async def execute_odata_query(
    table_name: str,
    resource_name: str,
    filter: Optional[str] = None,
    select: Optional[str] = None,
    orderby: Optional[str] = None,
    top: Optional[int] = None,
    skip: Optional[int] = None,
    count: bool = False,
    base_url: str = "",
    allowed_offices: Optional[list[str]] = None
) -> dict[str, Any]:
    """
    Execute an OData query against Databricks with office-based filtering.
    
    Args:
        table_name: Databricks table name
        resource_name: OData resource name for response
        filter: OData $filter expression
        select: OData $select expression
        orderby: OData $orderby expression
        top: OData $top value
        skip: OData $skip value
        count: Include @odata.count
        base_url: Base URL for response links
        allowed_offices: List of allowed OriginatingSystemOfficeKey values for filtering
        
    Returns:
        OData-formatted response dict
    """
    settings = get_settings()
    connector = get_databricks_connector()
    parser = get_odata_parser()
    
    # Build office filter
    office_filter = build_office_filter(allowed_offices or [])
    
    try:
        # Build and execute main query with office filter injected
        sql = parser.build_query(
            table_name=table_name,
            filter_expr=filter,
            select_expr=select,
            orderby_expr=orderby,
            top=top,
            skip=skip,
            additional_where=office_filter  # Inject office filter
        )
        
        result = await connector.execute_query(sql)
        
        # Convert to list of dicts
        columns = result["columns"]
        values = []
        for row in result["data"]:
            record = {}
            for i, col in enumerate(columns):
                value = row[i] if i < len(row) else None
                # Convert empty strings to None for cleaner output
                if value == "":
                    value = None
                record[col] = value
            # Convert numeric fields per RESO spec
            record = convert_numeric_fields(record)
            values.append(record)
        
        # Build response
        response = {
            "@odata.context": f"{base_url}/$metadata#{resource_name}",
            "value": values
        }
        
        # Add count if requested (with office filter applied)
        if count:
            count_sql = parser.build_count_query(table_name, filter, additional_where=office_filter)
            count_result = await connector.execute_query(count_sql)
            total_count = int(count_result["data"][0][0]) if count_result["data"] else 0
            response["@odata.count"] = total_count
        
        # Add nextLink for pagination
        actual_top = parser.parse_top(top)
        actual_skip = parser.parse_skip(skip)
        if len(values) == actual_top:
            next_skip = actual_skip + actual_top
            response["@odata.nextLink"] = f"{base_url}/odata/{resource_name}?$skip={next_skip}&$top={actual_top}"
            if filter:
                response["@odata.nextLink"] += f"&$filter={filter}"
            if select:
                response["@odata.nextLink"] += f"&$select={select}"
            if orderby:
                response["@odata.nextLink"] += f"&$orderby={orderby}"
        
        return response
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "QueryExecutionError",
                    "message": str(e)
                }
            }
        )


async def get_entity_by_key(
    table_name: str,
    resource_name: str,
    key_column: str,
    key_value: str,
    base_url: str = "",
    allowed_offices: Optional[list[str]] = None
) -> dict[str, Any]:
    """
    Get a single entity by its key with office-based filtering.
    
    Args:
        table_name: Databricks table name
        resource_name: OData resource name for response
        key_column: Primary key column name
        key_value: Primary key value
        base_url: Base URL for response links
        allowed_offices: List of allowed OriginatingSystemOfficeKey values for filtering
        
    Returns:
        Single entity dict or raises 404
    """
    connector = get_databricks_connector()
    settings = get_settings()
    
    # Build office filter
    office_filter = build_office_filter(allowed_offices or [])
    
    try:
        # Build WHERE clause with key and office filter
        where_parts = [f"{key_column} = '{key_value}'"]
        if office_filter:
            where_parts.append(office_filter)
        
        where_clause = " AND ".join(where_parts)
        
        sql = f"""
            SELECT * FROM {settings.databricks_catalog}.{settings.databricks_schema}.{table_name}
            WHERE {where_clause}
            LIMIT 1
        """
        
        result = await connector.execute_query(sql)
        
        if not result["data"]:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": {
                        "code": "ResourceNotFound",
                        "message": f"{resource_name} with key '{key_value}' not found"
                    }
                }
            )
        
        # Convert to dict
        columns = result["columns"]
        row = result["data"][0]
        record = {}
        for i, col in enumerate(columns):
            value = row[i] if i < len(row) else None
            if value == "":
                value = None
            record[col] = value
        
        # Convert numeric fields per RESO spec
        record = convert_numeric_fields(record)
        record["@odata.context"] = f"{base_url}/$metadata#{resource_name}/$entity"
        
        return record
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "QueryExecutionError",
                    "message": str(e)
                }
            }
        )

