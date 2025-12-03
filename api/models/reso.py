# Copyright 2025 SharpSir Group
# Licensed under the Apache License, Version 2.0
# See LICENSE file for details.
"""
RESO Data Dictionary 2.0 Pydantic Models

Based on RESO Data Dictionary 2.0 specification.
https://ddwiki.reso.org/
"""
from typing import Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime


class ODataResponse(BaseModel):
    """Standard OData response wrapper."""
    
    odata_context: str = Field(alias="@odata.context")
    odata_count: Optional[int] = Field(None, alias="@odata.count")
    odata_nextLink: Optional[str] = Field(None, alias="@odata.nextLink")
    value: list[dict[str, Any]]
    
    class Config:
        populate_by_name = True


class ODataError(BaseModel):
    """OData error response."""
    
    error: dict[str, Any] = Field(
        default_factory=lambda: {
            "code": "500",
            "message": "Internal Server Error"
        }
    )


# RESO Property Resource
class Property(BaseModel):
    """RESO Property resource (subset of fields)."""
    
    # Identifiers
    ListingKey: str
    ListingId: Optional[str] = None
    
    # Status
    StandardStatus: Optional[str] = None
    MlsStatus: Optional[str] = None
    
    # Property Type
    PropertyType: Optional[str] = None
    PropertySubType: Optional[str] = None
    
    # Location
    City: Optional[str] = None
    StateOrProvince: Optional[str] = None
    PostalCode: Optional[str] = None
    Country: Optional[str] = None
    StreetName: Optional[str] = None
    StreetNumber: Optional[str] = None
    UnparsedAddress: Optional[str] = None
    Latitude: Optional[float] = None
    Longitude: Optional[float] = None
    
    # Pricing
    ListPrice: Optional[float] = None
    OriginalListPrice: Optional[float] = None
    ClosePrice: Optional[float] = None
    
    # Details
    BedroomsTotal: Optional[int] = None
    BathroomsTotalInteger: Optional[int] = None
    LivingArea: Optional[float] = None
    LotSizeSquareFeet: Optional[float] = None
    YearBuilt: Optional[int] = None
    
    # Dates
    ListingContractDate: Optional[str] = None
    ModificationTimestamp: Optional[str] = None
    
    class Config:
        extra = "allow"  # Allow extension fields (X_*)


# RESO Member Resource
class Member(BaseModel):
    """RESO Member resource."""
    
    MemberKey: str
    MemberMlsId: Optional[str] = None
    MemberFirstName: Optional[str] = None
    MemberLastName: Optional[str] = None
    MemberFullName: Optional[str] = None
    MemberEmail: Optional[str] = None
    MemberDirectPhone: Optional[str] = None
    MemberMobilePhone: Optional[str] = None
    MemberStateLicense: Optional[str] = None
    MemberStatus: Optional[str] = None
    OfficeName: Optional[str] = None
    OfficeKey: Optional[str] = None
    
    class Config:
        extra = "allow"


# RESO Office Resource
class Office(BaseModel):
    """RESO Office resource."""
    
    OfficeKey: str
    OfficeMlsId: Optional[str] = None
    OfficeName: Optional[str] = None
    OfficePhone: Optional[str] = None
    OfficeEmail: Optional[str] = None
    OfficeAddress1: Optional[str] = None
    OfficeCity: Optional[str] = None
    OfficeStateOrProvince: Optional[str] = None
    OfficePostalCode: Optional[str] = None
    OfficeStatus: Optional[str] = None
    
    class Config:
        extra = "allow"


# RESO Media Resource
class Media(BaseModel):
    """RESO Media resource."""
    
    MediaKey: str
    ResourceRecordKey: Optional[str] = None
    ResourceName: Optional[str] = None
    MediaURL: Optional[str] = None
    MediaType: Optional[str] = None
    MediaCategory: Optional[str] = None
    Order: Optional[int] = None
    ShortDescription: Optional[str] = None
    
    class Config:
        extra = "allow"


# RESO Contacts Resource
class Contacts(BaseModel):
    """RESO Contacts resource."""
    
    ContactKey: str
    ContactFirstName: Optional[str] = None
    ContactLastName: Optional[str] = None
    ContactFullName: Optional[str] = None
    ContactEmail: Optional[str] = None
    ContactPhone: Optional[str] = None
    ContactType: Optional[str] = None
    ContactStatus: Optional[str] = None
    
    class Config:
        extra = "allow"


# RESO ShowingAppointment Resource
class ShowingAppointment(BaseModel):
    """RESO ShowingAppointment resource."""
    
    ShowingAppointmentKey: str
    ListingKey: Optional[str] = None
    ShowingAgentKey: Optional[str] = None
    ShowingDate: Optional[str] = None
    ShowingStartTime: Optional[str] = None
    ShowingEndTime: Optional[str] = None
    ShowingStatus: Optional[str] = None
    ShowingRemarks: Optional[str] = None
    
    class Config:
        extra = "allow"


# Metadata response
class MetadataSchema(BaseModel):
    """Schema information for OData $metadata."""
    
    name: str
    type: str
    nullable: bool = True


class ResourceMetadata(BaseModel):
    """Resource metadata."""
    
    name: str
    kind: str = "EntitySet"
    url: str
    schema_fields: list[MetadataSchema] = Field(alias="schema")
    
    class Config:
        populate_by_name = True

