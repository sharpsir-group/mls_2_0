# RESO Web API - Field Reference

This document lists all fields available through the RESO Web API.

## Data Sources

The API aggregates data from multiple sources, identified by:

| Field | Values | Description |
|-------|--------|-------------|
| `OriginatingSystemOfficeKey` | `CSIR`, `HSIR` | Office key for filtering |
| `X_DataSource` | `qobrix`, `dash_sothebys` | Source system identifier |
| `ListingKey` | `QOBRIX_*`, `DASH_*` | Unique ID with source prefix |

---

## Property Resource

**Endpoint:** `GET /odata/Property`

### Core Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `ListingKey` | STRING | Unique identifier | `QOBRIX_abc123`, `DASH_xyz789` |
| `ListingId` | STRING | MLS number / reference | `REF-12345` |
| `StandardStatus` | ENUM | Listing status | `Active`, `Pending`, `Closed`, `Withdrawn` |
| `PropertyType` | STRING | Property type | `Apartment`, `SingleFamilyDetached`, `Land` |
| `PropertySubType` | STRING | Property subtype | `Townhouse`, `Villa` |
| `PropertyClass` | ENUM | Sale/Lease classification | `RESI`, `RLSE`, `COMS`, `COML`, `LAND` |

### PropertyClass Values

| Value | Description |
|-------|-------------|
| `RESI` | Residential Sale |
| `RLSE` | Residential Lease (Rental) |
| `COMS` | Commercial Sale |
| `COML` | Commercial Lease |
| `LAND` | Land |

### Pricing

| Field | Type | Description |
|-------|------|-------------|
| `ListPrice` | DECIMAL | Listing price |
| `OriginalListPrice` | DECIMAL | Original listing price |
| `LeasePrice` | DECIMAL | Rental price (if applicable) |
| `LeaseAmountFrequency` | ENUM | `Monthly`, `Weekly`, `Yearly` |

### Location

| Field | Type | Description |
|-------|------|-------------|
| `UnparsedAddress` | STRING | Street address |
| `City` | STRING | City name |
| `StateOrProvince` | STRING | State or province |
| `PostalCode` | STRING | Postal/ZIP code |
| `Country` | STRING | Country code (e.g., `CY`, `HU`) |
| `Latitude` | DOUBLE | GPS latitude |
| `Longitude` | DOUBLE | GPS longitude |

### Property Details

| Field | Type | Description |
|-------|------|-------------|
| `BedroomsTotal` | INT | Number of bedrooms |
| `BathroomsTotalInteger` | INT | Number of full bathrooms |
| `BathroomsHalf` | INT | Number of half bathrooms |
| `LivingArea` | DECIMAL | Interior living area (m²) |
| `LivingAreaUnits` | STRING | Always `SquareMeters` |
| `LotSizeSquareFeet` | DECIMAL | Lot size (m²) |
| `LotSizeAcres` | DECIMAL | Lot size in acres |
| `YearBuilt` | INT | Year constructed |
| `StoriesTotal` | INT | Number of stories in building |
| `Stories` | INT | Floor number of unit |
| `DevelopmentStatus` | ENUM | `Proposed`, `Under Construction`, `Complete` |

### Features

| Field | Type | Description |
|-------|------|-------------|
| `View` | STRING | View description |
| `Flooring` | STRING | Flooring types |
| `Heating` | STRING | Heating system |
| `Cooling` | STRING | Cooling/AC system |
| `PoolFeatures` | STRING | Pool description |
| `FireplaceYN` | BOOLEAN | Has fireplace |
| `FireplaceFeatures` | STRING | Fireplace details |
| `ParkingFeatures` | STRING | Parking/garage |
| `Fencing` | STRING | Fencing type |
| `PatioAndPorchFeatures` | STRING | Outdoor living |
| `ExteriorFeatures` | STRING | Exterior features |
| `InteriorFeatures` | STRING | Interior features |
| `Appliances` | STRING | Kitchen appliances |
| `Basement` | STRING | Basement type |
| `Roof` | STRING | Roof type |
| `WaterSource` | STRING | Water source |
| `Sewer` | STRING | Sewer type |
| `Electric` | STRING | Electrical |
| `LotFeatures` | STRING | Lot characteristics |
| `WaterfrontFeatures` | STRING | Waterfront details |
| `RoadSurfaceType` | STRING | Road type |
| `PropertyCondition` | STRING | Property condition |
| `AssociationAmenities` | STRING | Community amenities |

### Agent & Office

| Field | Type | Description |
|-------|------|-------------|
| `ListAgentKey` | STRING | Agent identifier |
| `ListAgentFirstName` | STRING | Agent first name |
| `ListAgentLastName` | STRING | Agent last name |
| `ListAgentEmail` | STRING | Agent email |
| `ListOfficeKey` | STRING | Office identifier |
| `ListOfficeName` | STRING | Office/brokerage name |
| `CoListAgentKey` | STRING | Co-listing agent |

### Dates

| Field | Type | Description |
|-------|------|-------------|
| `ListingContractDate` | DATE | Date listed |
| `ExpirationDate` | DATE | Listing expiration |
| `ModificationTimestamp` | TIMESTAMP | Last modified |
| `OriginalEntryTimestamp` | TIMESTAMP | Originally created |
| `DaysOnMarket` | INT | Days on market |

### Description

| Field | Type | Description |
|-------|------|-------------|
| `PublicRemarks` | STRING | Public description |

### Extension Fields (X_)

| Field | Type | Description |
|-------|------|-------------|
| `X_DataSource` | STRING | `qobrix` or `dash_sothebys` |
| `X_ListingUrl` | STRING | Link to original listing |
| `X_CurrencyCode` | STRING | Currency (e.g., `EUR`, `USD`, `HUF`) |
| `X_ListPriceUSD` | DECIMAL | Price in USD |
| `X_PriceUponRequest` | BOOLEAN | Price hidden |
| `X_IsAuction` | BOOLEAN | Auction listing |
| `X_District` | STRING | District/neighborhood |
| `X_StyleCode` | STRING | Architectural style code |
| `X_StyleDescription` | STRING | Architectural style |
| `X_HeatingFuel` | STRING | Heating fuel type |
| `X_KitchenFeatures` | STRING | Kitchen details |
| `X_BathFeatures` | STRING | Bathroom details |
| `X_Lifestyles` | STRING | Lifestyle tags |
| `X_SpecialMarket` | STRING | Market segment (e.g., Luxury) |
| `X_ListAgentPhotoUrl` | STRING | Agent photo URL |
| `X_MainPhoto` | STRING | Main listing photo URL |
| `X_SeaView` | BOOLEAN | Has sea view |
| `X_MountainView` | BOOLEAN | Has mountain view |
| `X_PrivateSwimmingPool` | BOOLEAN | Has private pool |
| `X_CommonSwimmingPool` | BOOLEAN | Has common pool |
| `X_GardenArea` | DECIMAL | Garden size (m²) |
| `X_Furnished` | STRING | Furnished status |
| `X_PetsAllowed` | STRING | Pet policy |

---

## Media Resource

**Endpoint:** `GET /odata/Media`

| Field | Type | Description |
|-------|------|-------------|
| `MediaKey` | STRING | Unique media identifier |
| `ResourceRecordKey` | STRING | Links to Property.ListingKey |
| `ResourceName` | STRING | Always `Property` |
| `MediaURL` | STRING | Full URL to media file |
| `MediaCategory` | STRING | `Photo`, `Video`, `Document` |
| `MediaType` | STRING | MIME type |
| `Order` | INT | Display order (0 = main photo) |
| `ShortDescription` | STRING | Caption/title |
| `LongDescription` | STRING | Detailed description |
| `ImageWidth` | INT | Image width in pixels |
| `ImageHeight` | INT | Image height in pixels |
| `ImageSizeBytes` | BIGINT | File size |
| `PreferredPhotoYN` | BOOLEAN | Is main photo |
| `MediaModificationTimestamp` | TIMESTAMP | Last modified |
| `OriginatingSystemOfficeKey` | STRING | `CSIR` or `HSIR` |
| `X_DataSource` | STRING | Source system |

---

## Member Resource

**Endpoint:** `GET /odata/Member`

| Field | Type | Description |
|-------|------|-------------|
| `MemberKey` | STRING | Unique agent identifier |
| `MemberFirstName` | STRING | First name |
| `MemberLastName` | STRING | Last name |
| `MemberEmail` | STRING | Email address |
| `MemberDirectPhone` | STRING | Office phone |
| `MemberMobilePhone` | STRING | Mobile phone |
| `OfficeKey` | STRING | Associated office |

---

## Office Resource

**Endpoint:** `GET /odata/Office`

| Field | Type | Description |
|-------|------|-------------|
| `OfficeKey` | STRING | Unique office identifier |
| `OfficeName` | STRING | Office/brokerage name |
| `OfficeEmail` | STRING | Office email |
| `OfficePhone` | STRING | Office phone |

---

## Contacts Resource

**Endpoint:** `GET /odata/Contacts`

| Field | Type | Description |
|-------|------|-------------|
| `ContactKey` | STRING | Unique contact identifier |
| `ContactFirstName` | STRING | First name |
| `ContactLastName` | STRING | Last name |
| `ContactEmail` | STRING | Email address |
| `ContactPhone` | STRING | Phone number |

---

## ShowingAppointment Resource

**Endpoint:** `GET /odata/ShowingAppointment`

| Field | Type | Description |
|-------|------|-------------|
| `ShowingKey` | STRING | Unique showing identifier |
| `ListingKey` | STRING | Associated property |
| `BuyerAgentKey` | STRING | Requesting agent/contact |
| `ShowingStartTimestamp` | TIMESTAMP | Scheduled time |
| `ShowingStatus` | STRING | Appointment status |

---

## Field Availability by Source

Some fields are only available from specific data sources:

| Field | Qobrix (CSIR) | Dash (HSIR) |
|-------|---------------|-------------|
| `YearBuilt` | ❌ | ✅ |
| `View` | Limited | ✅ Full |
| `Flooring` | Limited | ✅ Full |
| `Heating` | Limited | ✅ Full |
| `Cooling` | Limited | ✅ Full |
| `PoolFeatures` | Limited | ✅ Full |
| `Appliances` | ❌ | ✅ |
| `ListAgentFirstName` | ❌ | ✅ |
| `ListAgentLastName` | ❌ | ✅ |
| `ListAgentEmail` | ❌ | ✅ |
| `X_ListingUrl` | ❌ | ✅ |
| `X_ListAgentPhotoUrl` | ❌ | ✅ |
| `ImageWidth` | ❌ | ✅ |
| `ImageHeight` | ❌ | ✅ |
| `DevelopmentStatus` | ✅ | ❌ |
| `X_SeaView` | ✅ | ❌ |
| `X_MountainView` | ✅ | ❌ |
