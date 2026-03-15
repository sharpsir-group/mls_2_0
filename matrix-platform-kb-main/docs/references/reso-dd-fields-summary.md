# RESO Data Dictionary 2.0 — Fields & Lookups Summary

> Source: `reso dd/RESO_Data_Dictionary_2.0.xlsx`
> Version: DD 2.0, Wiki Date: 04/16/2024, XLSX Created: 2024-10-14

## Resources in RESO DD 2.0

| Resource | Description | Key Fields (examples) |
|----------|-------------|----------------------|
| **Property** | Real estate listings | ListPrice, BedroomsTotal, BathroomsFull, City, StateOrProvince, PostalCode, PropertyType, PropertySubType, StandardStatus, ListingContractDate, DaysOnMarket, YearBuilt, LivingArea, LotSizeArea |
| **Member** | Agents/brokers | MemberFirstName, MemberLastName, MemberEmail, MemberMlsId, MemberStatus |
| **Office** | Brokerage offices | OfficeName, OfficePhone, OfficeAddress1, OfficeMlsId |
| **Contacts** | Client records | ContactFirstName, ContactLastName, ContactEmail, ContactPhone |
| **Teams** | Agent teams | TeamName, TeamLead, TeamMemberCount |
| **OpenHouse** | Open house events | OpenHouseDate, OpenHouseStartTime, OpenHouseEndTime |
| **Media** | Listing media | MediaURL, MediaType, MediaCategory, MediaModificationTimestamp |
| **HistoryTransactional** | Transaction history | ClosePrice, CloseDate, ListPrice |
| **ShowingAppointment** | Showings | ShowingDate, ShowingStartTime, ShowingAgentMlsId |
| **Prospecting** | Lead tracking | ProspectingStatus |

## Key Property Fields for Cyprus Real Estate

### Identification & Status
| StandardName | Type | Description |
|-------------|------|-------------|
| ListingId | String | Unique listing identifier |
| ListingKey | String | System key |
| StandardStatus | Lookup | Active, Pending, Closed, Withdrawn, Expired, ComingSoon |
| PropertyType | Lookup | Residential, ResidentialLease, ResidentialIncome, Commercial, CommercialLease, Farm |
| PropertySubType | Lookup | Apartment, Condominium, SingleFamilyResidence, Townhouse, Villa, etc. |
| ListingContractDate | Date | Date listing agreement signed |
| ExpirationDate | Date | Listing expiration |
| DaysOnMarket | Number | Days on market (calculated) |

### Pricing
| StandardName | Type | Description |
|-------------|------|-------------|
| ListPrice | Number | Listing price |
| OriginalListPrice | Number | Original asking price |
| ClosePrice | Number | Final sale price |
| PriceChangeTimestamp | Timestamp | Last price change |

### Location
| StandardName | Type | Description |
|-------------|------|-------------|
| StreetNumber | String | Street number |
| StreetName | String | Street name |
| City | String | City |
| StateOrProvince | String | State/Province |
| PostalCode | String | Postal/ZIP code |
| Country | String | Country (ISO) |
| Latitude | Number | GPS latitude |
| Longitude | Number | GPS longitude |

### Structure
| StandardName | Type | Description |
|-------------|------|-------------|
| BedroomsTotal | Number | Total bedrooms |
| BathroomsFull | Number | Full bathrooms |
| BathroomsHalf | Number | Half bathrooms |
| BathroomsTotalInteger | Number | Total bathrooms |
| LivingArea | Number | Living area |
| LivingAreaUnits | Lookup | SqFt, SqM |
| BuildingAreaTotal | Number | Total building area |
| LotSizeArea | Number | Lot/plot size |
| StoriesTotal | Number | Total stories in building |
| Stories | Number | Number of stories/floors |
| YearBuilt | Number | Year constructed |
| Furnished | Lookup | Furnished, PartiallyFurnished, Unfurnished |

### Features
| StandardName | Type | Description |
|-------------|------|-------------|
| View | Lookup Multi | City, Garden, Mountain(s), Ocean, Pool |
| Heating | Lookup Multi | Central, Electric, Geothermal, HeatPump, NaturalGas, None |
| Cooling | Lookup Multi | CentralAir, WallUnit, None |
| Appliances | Lookup Multi | Dishwasher, Dryer, Microwave, Oven, Refrigerator, Washer |
| ParkingFeatures | Lookup Multi | AttachedGarage, CoveredParking, OpenParking |
| CoveredSpaces | Number | Covered parking count |
| OpenParkingSpaces | Number | Open parking count |
| PoolPrivateYN | Boolean | Private pool |
| PoolFeatures | Lookup Multi | InGround, Communal, Private |
| AssociationAmenities | Lookup Multi | Gym, Sauna, Playground, Pool, etc. |
| WaterfrontFeatures | Lookup Multi | Beach access, waterfront |

### Agent & Office
| StandardName | Type | Description |
|-------------|------|-------------|
| ListAgentKey | String | Listing agent ID |
| ListAgentFullName | String | Listing agent name |
| ListAgentEmail | String | Listing agent email |
| ListOfficeName | String | Listing office name |
| ListAgentCommission | Number | Agent commission % |

### Descriptions
| StandardName | Type | Description |
|-------------|------|-------------|
| PublicRemarks | String | Public property description |
| PrivateRemarks | String | Agent-only notes |
| Directions | String | Driving directions |

## Key Lookup Categories

| LookupName | # Values | Example Values |
|-----------|----------|----------------|
| PropertyType | 7 | Residential, CommercialSale, CommercialLease, Farm, Land |
| PropertySubType | 50+ | Apartment, Condominium, SingleFamilyResidence, Townhouse, Villa |
| StandardStatus | 8 | Active, ActiveUnderContract, Closed, ComingSoon, Expired, Pending, Withdrawn |
| Country | 200+ | CY, US, GR, GB, RU |
| View | 20+ | City, Garden, Mountain(s), Ocean, Pool, Trees/Woods |
| Heating | 15+ | Central, Electric, Geothermal, HeatPump, NaturalGas, Radiant, None |
| Cooling | 10+ | CentralAir, WallUnit, Evaporation, None |
| Furnished | 3 | Furnished, PartiallyFurnished, Unfurnished |
| ParkingFeatures | 15+ | AttachedGarage, CircularDriveway, CoveredParking, GarageOpener |
| PoolFeatures | 10+ | AboveGround, Community, Gunite, InGround, Private |
| AccessibilityFeatures | 30+ | AccessibleApproachWithRamp, AccessibleBedroom, etc. |
| AreaSource | 10+ | Agent, Appraiser, Assessor, Builder, Estimated, PublicRecords |
| AreaUnits | 2 | SquareFeet, SquareMeters |
| LeadSource | 15+ | Agent, OpenHouse, RealEstateWebsite, Referral, SignOnProperty |

## Data Types Used

| SimpleDataType | Description | Example |
|---------------|-------------|---------|
| String | Text | "Villa Paphos" |
| Number | Numeric (with optional precision) | 850000.00 |
| Boolean | True/False | true |
| Date | Date (YYYY-MM-DD) | 2026-02-18 |
| Timestamp | Date+Time (ISO 8601) | 2026-02-18T10:30:00Z |
| String List, Single | Single picklist selection | "Active" |
| String List, Multi | Multiple picklist selections | ["Ocean", "Mountain(s)"] |
