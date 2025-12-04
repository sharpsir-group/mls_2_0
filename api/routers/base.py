# Copyright 2025 SharpSir Group
# Licensed under the Apache License, Version 2.0
# See LICENSE file for details.
"""
Base router with shared OData query handling logic.
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


async def execute_odata_query(
    table_name: str,
    resource_name: str,
    filter: Optional[str] = None,
    select: Optional[str] = None,
    orderby: Optional[str] = None,
    top: Optional[int] = None,
    skip: Optional[int] = None,
    count: bool = False,
    base_url: str = ""
) -> dict[str, Any]:
    """
    Execute an OData query against Databricks.
    
    Returns OData-formatted response.
    """
    settings = get_settings()
    connector = get_databricks_connector()
    parser = get_odata_parser()
    
    try:
        # Build and execute main query
        sql = parser.build_query(
            table_name=table_name,
            filter_expr=filter,
            select_expr=select,
            orderby_expr=orderby,
            top=top,
            skip=skip
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
        
        # Add count if requested
        if count:
            count_sql = parser.build_count_query(table_name, filter)
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
    base_url: str = ""
) -> dict[str, Any]:
    """
    Get a single entity by its key.
    
    Returns single entity or raises 404.
    """
    connector = get_databricks_connector()
    settings = get_settings()
    
    try:
        sql = f"""
            SELECT * FROM {settings.databricks_catalog}.{settings.databricks_schema}.{table_name}
            WHERE {key_column} = '{key_value}'
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

