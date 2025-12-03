"""
OData $metadata Endpoint

Returns service metadata and entity schemas.
"""
from typing import Any
from fastapi import APIRouter, Request
from fastapi.responses import Response
import sys
sys.path.insert(0, '..')
from services.databricks import get_databricks_connector


router = APIRouter(tags=["Metadata"])


# RESO resources with their key fields
RESOURCES = {
    "Property": {"table": "property", "key": "ListingKey"},
    "Member": {"table": "member", "key": "MemberKey"},
    "Office": {"table": "office", "key": "OfficeKey"},
    "Media": {"table": "media", "key": "MediaKey"},
    "Contacts": {"table": "contacts", "key": "ContactKey"},
    "ShowingAppointment": {"table": "showingappointment", "key": "ShowingAppointmentKey"},
}


@router.get("/odata/$metadata")
async def get_metadata(request: Request) -> Response:
    """
    Returns OData service metadata document.
    
    This is an XML document describing the entity types and their properties.
    """
    base_url = str(request.base_url).rstrip("/")
    
    xml = f'''<?xml version="1.0" encoding="utf-8"?>
<edmx:Edmx Version="4.0" xmlns:edmx="http://docs.oasis-open.org/odata/ns/edmx">
  <edmx:DataServices>
    <Schema Namespace="RESO.OData" xmlns="http://docs.oasis-open.org/odata/ns/edm">
'''
    
    # Add entity type definitions (simplified)
    for resource_name, info in RESOURCES.items():
        xml += f'''      <EntityType Name="{resource_name}">
        <Key>
          <PropertyRef Name="{info['key']}"/>
        </Key>
        <Property Name="{info['key']}" Type="Edm.String" Nullable="false"/>
      </EntityType>
'''
    
    xml += '''      <EntityContainer Name="Container">
'''
    
    # Add entity sets
    for resource_name in RESOURCES:
        xml += f'''        <EntitySet Name="{resource_name}" EntityType="RESO.OData.{resource_name}"/>
'''
    
    xml += '''      </EntityContainer>
    </Schema>
  </edmx:DataServices>
</edmx:Edmx>'''
    
    return Response(content=xml, media_type="application/xml")


@router.get("/odata")
async def get_service_document(request: Request) -> dict[str, Any]:
    """
    Returns OData service document listing available resources.
    """
    base_url = str(request.base_url).rstrip("/")
    
    return {
        "@odata.context": f"{base_url}/odata/$metadata",
        "value": [
            {"name": name, "kind": "EntitySet", "url": name}
            for name in RESOURCES.keys()
        ]
    }


@router.get("/odata/{resource}/$count")
async def get_resource_count(resource: str) -> int:
    """Get count of records in a resource."""
    if resource not in RESOURCES:
        return 0
    
    connector = get_databricks_connector()
    table_name = RESOURCES[resource]["table"]
    
    from config import get_settings
    settings = get_settings()
    
    sql = f"SELECT COUNT(*) FROM {settings.databricks_catalog}.{settings.databricks_schema}.{table_name}"
    result = await connector.execute_query(sql)
    
    return int(result["data"][0][0]) if result["data"] else 0

