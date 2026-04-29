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
| `YearBuiltEffective` | INT | Last major renovation year |
| `StoriesTotal` | INT | Number of stories in building |
| `Stories` | INT | Floor number of unit |
| `DevelopmentStatus` | ENUM | RESO 2.0: `Proposed`, `Under Construction`, `New Construction`, `Existing` |
| `NewConstructionYN` | BOOL | RESO 2.0 primary new-vs-resale flag |
| `PropertyCondition` | STRING (CSV, multi) | RESO 2.0 multi-value: `Fixer`, `New Construction`, `To Be Built`, `Under Construction`, `Updated/Remodeled` |
| `BuilderName` | STRING | RESO 2.0 — developer / seller company |
| `BuilderModel` | STRING | RESO 2.0 — project / development name |

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
| `X_SellerContactKey` | STRING | Seller contact link (`QOBRIX_CONTACT_<uuid>`); joins to `Contacts.ContactKey` |
| `X_CreatedByMemberKey` | STRING | User who created the listing in source CRM (`QOBRIX_USER_<uuid>`); joins to `Member.MemberKey` |
| `X_ModifiedByMemberKey` | STRING | User who last modified the listing in source CRM (`QOBRIX_USER_<uuid>`); joins to `Member.MemberKey` |
| `X_DeveloperContactKey` | STRING | Developer contact link (`QOBRIX_CONTACT_<uuid>`); joins to `Contacts.ContactKey` (project/new-build developer) |
| `X_LeadSource` | STRING | Lead-source attribution from source CRM (e.g. `Bayut`, `Spitogatos`, `Referral`) |
| `X_WebsiteListingDate` | DATE | Date the listing went live on the consumer website (distinct from `ListingContractDate`) |
| `X_KeyHolderDetails` | STRING | Free-text operational note. Cyprus tenant overloads this with the listing-broker name when Qobrix `agent`/`salesperson` UUIDs are empty (best-effort fallback) |
| `X_ListingBrokerName` | STRING | Listing-broker name parsed heuristically from the parent `Project.name` (Cyprus tenant convention: name appended after last comma). Hint, not a key; can have false positives for two-word place names |

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

---

## Lifecycle classification ladder (Qobrix)

First match wins; emits aligned `DevelopmentStatus`, `NewConstructionYN`, `PropertyCondition`.

| # | Condition | DevelopmentStatus | NewConstructionYN | PropertyCondition |
|---|-----------|-------------------|--------------------|--------------------|
| 1 | `custom_resale = 'true'` | `Existing` | `FALSE` | `NULL` |
| 2 | `custom_presale = 'true' AND new_build = 'true'` | `Proposed` | `TRUE` | `To Be Built` |
| 3 | `construction_stage IN ('off_plan','offplans','planning')` | `Proposed` | `TRUE` | `To Be Built` |
| 4 | `construction_stage IN ('construction_phase','under_construction')` | `Under Construction` | `TRUE` | `Under Construction` |
| 5 | `construction_stage = 'resale'` | `Existing` | `FALSE` | `NULL` |
| 6 | `construction_stage = 'completed' AND new_build = 'true'` | `New Construction` | `TRUE` | `New Construction` |
| 7 | `construction_stage = 'completed' AND new_build = 'false'` | `Existing` | `FALSE` | `NULL` |
| 8 | `construction_stage = 'completed' AND new_build IS NULL AND developer_id IS NOT NULL` | `New Construction` | `TRUE` | `New Construction` |
| 9 | `construction_stage` blank → `project_project_construction_stage` (mirror rules above) | per rules | per rules | per rules |
| 10 | Default | `Existing` | `NULL` | `NULL` |

Additive: when `renovation_year > construction_year`, append `Updated/Remodeled` to `PropertyCondition`.

## CDL canonical column mapping (RESO PascalCase ↔ CDL snake_case)

`public.properties` (Atlas Supabase, after `20260428100000_canonical_reso_lifecycle`):

| RESO field | CDL column |
|---|---|
| `StandardStatus` | `standard_status` |
| `PropertyType` | `property_type` |
| `PropertySubType` | `property_sub_type` |
| `BedroomsTotal` | `bedrooms_total` |
| `BathroomsTotalInteger` | `bathrooms_total_integer` |
| `LivingArea` | `living_area` |
| `ListPrice` | `list_price` |
| `UnparsedAddress` | `unparsed_address` |
| `PublicRemarks` | `public_remarks_en` |
| `ListAgentKey` | `list_agent_key` |
| `ListAgentFullName` | `list_agent_full_name` |
| `ModifiedByMemberKey` | `modified_by_member_key` |
| `BuilderName` | `builder_name` |
| `BuilderModel` | `builder_model` |
| `DevelopmentStatus` | `development_status` |
| `NewConstructionYN` | `new_construction_yn` |
| `PropertyCondition` | `property_condition` |
| `YearBuilt` | `year_built` |
| `YearBuiltEffective` | `year_built_effective` |

## Value canonicalization (StandardStatus migration)

Pre-migration legacy values in `public.properties.status` were collapsed display labels.
Post-migration, `standard_status` carries RESO StandardStatus verbatim.

| Legacy value | RESO StandardStatus |
|---|---|
| `For Sale` | `Active` |
| `Sold` | `Closed` |
| `Off Market` | `Withdrawn` |

## Dash filter chip ↔ RESO field reference

For Atlas Lovable FE / Dash syndication consumers — single-field expressions:

| Dash chip | RESO expression |
|---|---|
| Off-plan | `PropertyCondition` contains `To Be Built` OR `DevelopmentStatus = 'Proposed'` |
| Under construction | `PropertyCondition` contains `Under Construction` OR `DevelopmentStatus = 'Under Construction'` |
| Ready / new | `PropertyCondition` contains `New Construction` OR `DevelopmentStatus = 'New Construction'` |
| Resale | `NewConstructionYN = FALSE` OR `DevelopmentStatus = 'Existing'` |
| Renovated | `PropertyCondition` contains `Updated/Remodeled` |

