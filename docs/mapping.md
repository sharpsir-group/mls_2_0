# Qobrix → RESO Data Mapping

This document describes the complete mapping from Qobrix CRM data to RESO Data Dictionary 2.0 standard format.

**Total Qobrix Property Fields:** 474 columns  
**RESO Standard Fields:** 48  
**Extension Fields (X_):** 129  
**Total Gold Property Fields:** 179

## Overview

| Layer | Source | Target | Description |
|-------|--------|--------|-------------|
| Bronze | Qobrix API | `qobrix_bronze.*` | Raw data, all columns as STRING |
| Silver | Bronze tables | `qobrix_silver.*` | Normalized, typed, cleaned |
| Gold | Silver tables | `reso_gold.*` | RESO-compliant format |

---

## RESO Resources Implemented

| RESO Resource | Qobrix Source | Silver Table | Gold Table |
|---------------|---------------|--------------|------------|
| Property | `properties` | `property` | `property` |
| Member | `agents`, `users` | `agent` | `member` |
| Office | `agents` (agencies) | `agent` | `office` |
| Media | `property_media` | `media` | `media` |
| Contacts | `contacts` | `contact` | `contacts` |
| ShowingAppointment | `property_viewings` | `viewing` | `showing_appointment` |

---

## Legend

| Symbol | Meaning |
|--------|---------|
| ✅ | Mapped to RESO Standard Field |
| 🔷 | Mapped to RESO Extension Field (X_) |
| ⚪ | Available in Bronze only (not mapped to Gold) |

---

## RESO Standard Fields (48)

### Core Identifiers & Status

| Qobrix Field | RESO Field | Type | Transformation |
|--------------|------------|------|----------------|
| `id` | `ListingKey` | STRING | `CONCAT('QOBRIX_', id)` |
| `ref` | `ListingId` | STRING | Direct |
| `status` | `StandardStatus` | ENUM | available→Active, reserved→Pending, sold→Closed |
| `property_type` | `PropertyType` | ENUM | apartment→Apartment, house→SingleFamilyDetached |
| `property_subtype` | `PropertySubType` | STRING | Lookup from property_subtypes |
### PropertyClass (Sale vs Lease)

| Qobrix Fields | RESO Field | Type | Transformation |
|---------------|------------|------|----------------|
| `sale_rent` + `property_type` | `PropertyClass` | ENUM | See mapping below |

**PropertyClass Mapping:**

| PropertyClass | Description | Qobrix Mapping |
|---------------|-------------|----------------|
| `RESI` | Residential Sale | apartment/house + for_sale |
| `RLSE` | Residential Lease | apartment/house + for_rent |
| `COMS` | Commercial Sale | office/retail/etc + for_sale |
| `COML` | Commercial Lease | office/retail/etc + for_rent |
| `LAND` | Land | land (any sale_rent) |

### DevelopmentStatus (Construction Stage)

| Qobrix Field | RESO Field | Type | Transformation |
|--------------|------------|------|----------------|
| `project_project_construction_stage` | `DevelopmentStatus` | ENUM | See mapping below |

**DevelopmentStatus Mapping:**

| DevelopmentStatus | Description | Qobrix Value |
|-------------------|-------------|--------------|
| `Proposed` | Off-plan, not yet started | `offplans` |
| `Under Construction` | Currently being built | `construction_phase` |
| `Complete` | Finished construction | `completed` |
| *(null)* | Unknown/not specified | *(empty)* |


### Property Details

| Qobrix Field | RESO Field | Type | Transformation |
|--------------|------------|------|----------------|
| `bedrooms` | `BedroomsTotal` | INT | TRY_CAST |
| `bathrooms` | `BathroomsTotalInteger` | INT | TRY_CAST |
| `internal_area_amount` | `LivingArea` | DECIMAL | TRY_CAST |
| `plot_area_amount` | `LotSizeSquareFeet` | DECIMAL | TRY_CAST |
| `list_selling_price_amount` | `ListPrice` | DECIMAL | TRY_CAST |
| `list_rental_price_amount` | `LeasePrice` | DECIMAL | TRY_CAST |

### Location

| Qobrix Field | RESO Field | Type | Transformation |
|--------------|------------|------|----------------|
| `street` | `UnparsedAddress` | STRING | Direct |
| `city` | `City` | STRING | Direct |
| `state` | `StateOrProvince` | STRING | Direct |
| `post_code` | `PostalCode` | STRING | Direct |
| `country` | `Country` | STRING | Direct |
| `coordinates` | `Latitude` | DOUBLE | SPLIT()[0] |
| `coordinates` | `Longitude` | DOUBLE | SPLIT()[1] |

### Dates

| Qobrix Field | RESO Field | Type |
|--------------|------------|------|
| `listing_date` | `ListingContractDate` | DATE |
| `modified` | `ModificationTimestamp` | TIMESTAMP |

### Building Details

| Qobrix Field | RESO Field | Type | Transformation |
|--------------|------------|------|----------------|
| `construction_year` | `YearBuilt` | INT | TRY_CAST |
| `renovation_year` | `YearBuiltEffective` | INT | TRY_CAST |
| `floors_building` | `StoriesTotal` | INT | TRY_CAST |
| `floor_number` | `Stories` | INT | TRY_CAST |

### Features (RESO Standard)

| Qobrix Field | RESO Field | Type | Transformation |
|--------------|------------|------|----------------|
| `view` | `View` | STRING | Direct |
| `pool_features` | `PoolFeatures` | STRING | Direct |
| `heating` | `Heating` | STRING | Direct |
| `cooling` | `Cooling` | STRING | Direct |
| `flooring` | `Flooring` | STRING | Direct |
| `fencing` | `Fencing` | STRING | Direct |
| `fireplace` | `FireplaceYN` | BOOLEAN | true/false mapping |
| `fireplace_features` | `FireplaceFeatures` | STRING | Direct |
| `waterfront_features` | `WaterfrontFeatures` | STRING | Direct |
| `patio_porch` | `PatioAndPorchFeatures` | STRING | Direct |
| `other_structures` | `OtherStructures` | STRING | Direct |
| `association_amenities` | `AssociationAmenities` | STRING | Direct |
| `parking` | `ParkingFeatures` | STRING | Combined with covered/uncovered |
| `furnished` | `Furnished` | ENUM | true→Furnished, false→Unfurnished |
| `pets_allowed` | `PetsAllowed` | ENUM | true→Yes, false→No |

### Agent Linkage

| Qobrix Field | RESO Field | Type | Transformation |
|--------------|------------|------|----------------|
| `agent` | `ListAgentKey` | STRING | `CONCAT('QOBRIX_AGENT_', agent)` |
| `salesperson` | `CoListAgentKey` | STRING | `CONCAT('QOBRIX_AGENT_', salesperson)` |

### Remarks

### Bathrooms (NEW)

| Qobrix Field | RESO Field | Type | Transformation |
|--------------|------------|------|----------------|
| `wc_bathrooms` | `BathroomsHalf` | INT | TRY_CAST (WC = half bath) |

### Lot Size (NEW)

| Qobrix Field | RESO Field | Type | Transformation |
|--------------|------------|------|----------------|
| `plot_area_amount` | `LotSizeAcres` | DECIMAL | `plot_area * 0.000247105` (m² → acres) |

### Lease (NEW)

| Qobrix Field | RESO Field | Type | Transformation |
|--------------|------------|------|----------------|
| `rent_frequency` | `LeaseAmountFrequency` | ENUM | monthly→Monthly, weekly→Weekly |

### Office Linkage (NEW)

| Qobrix Field | RESO Field | Type | Transformation |
|--------------|------------|------|----------------|
| `agent` | `ListOfficeKey` | STRING | `CONCAT('QOBRIX_OFFICE_', agent)` |

| Qobrix Field | RESO Field | Type |
|--------------|------------|------|
| `description` | `PublicRemarks` | STRING |

---

## Extension Fields (X_) - 129 Fields

### Views & Amenities

| Qobrix Field | RESO Field |
|--------------|------------|
| `sea_view` | `X_SeaView` |
| `mountain_view` | `X_MountainView` |
| `beach_front` | `X_BeachFront` |
| `abuts_green_area` | `X_AbutsGreenArea` |
| `elevated_area` | `X_ElevatedArea` |
| `private_swimming_pool` | `X_PrivateSwimmingPool` |
| `common_swimming_pool` | `X_CommonSwimmingPool` |
| `garden_area_amount` | `X_GardenArea` |
| `roof_garden_area_amount` | `X_RoofGardenArea` |

### Property Features

| Qobrix Field | RESO Field |
|--------------|------------|
| `elevator` | `X_Elevator` |
| `air_condition` | `X_AirCondition` |
| `alarm` | `X_Alarm` |
| `smart_home` | `X_SmartHome` |
| `solar_water_heater` | `X_SolarWaterHeater` |
| `storage_space` | `X_StorageSpace` |
| `maids_room` | `X_MaidsRoom` |
| `concierge_reception` | `X_ConciergeReception` |
| `secure_door` | `X_SecureDoor` |
| `kitchenette` | `X_Kitchenette` |
| `home_office` | `X_HomeOffice` |
| `separate_laundry_room` | `X_SeparateLaundryRoom` |
| `reception` | `X_Reception` |
| `store_room` | `X_StoreRoom` |

### Building Info

| Qobrix Field | RESO Field |
|--------------|------------|
| `construction_type` | `X_ConstructionType` |
| `construction_stage` | `X_ConstructionStage` |
| `floor_type` | `X_FloorType` |
| `new_build` | `X_NewBuild` |
| `height` | `X_Height` |
| `storeys_max_floor` | `X_MaxFloor` |
| `unit_number` | `X_UnitNumber` |

### Energy & Utilities

| Qobrix Field | RESO Field |
|--------------|------------|
| `energy_efficiency_grade` | `X_EnergyEfficiencyGrade` |
| `energy_consumption_rating` | `X_EnergyConsumptionRating` |
| `energy_consumption_value` | `X_EnergyConsumptionValue` |
| `energy_emission_rating` | `X_EnergyEmissionRating` |
| `heating_type` | `X_HeatingType` |
| `heating_medium` | `X_HeatingMedium` |
| `cooling_type` | `X_CoolingType` |
| `electricity` | `X_Electricity` |
| `electricity_type` | `X_ElectricityType` |
| `water` | `X_Water` |

### Distances

| Qobrix Field | RESO Field |
|--------------|------------|
| `distance_from_beach` | `X_DistanceFromBeach` |
| `distance_from_airport` | `X_DistanceFromAirport` |
| `distance_from_centre` | `X_DistanceFromCentre` |
| `distance_from_school` | `X_DistanceFromSchool` |
| `distance_from_shops` | `X_DistanceFromShops` |
| `distance_from_hospital` | `X_DistanceFromHospital` |
| `distance_from_university` | `X_DistanceFromUniversity` |
| `distance_from_rail_station` | `X_DistanceFromRailStation` |
| `distance_from_tube_station` | `X_DistanceFromTubeStation` |

### Room Details

| Qobrix Field | RESO Field |
|--------------|------------|
| `living_rooms` | `X_LivingRooms` |
| `kitchens` | `X_Kitchens` |
| `kitchen_type` | `X_KitchenType` |
| `wc_bathrooms` | `X_WCBathrooms` |
| `office_spaces` | `X_OfficeSpaces` |
| `verandas` | `X_VerandasCount` |

### Area Details

| Qobrix Field | RESO Field |
|--------------|------------|
| `covered_area_amount` | `X_CoveredArea` |
| `uncovered_area_amount` | `X_UncoveredArea` |
| `total_area_amount` | `X_TotalArea` |
| `mezzanine_amount` | `X_MezzanineArea` |
| `storage_amount` | `X_StorageArea` |
| `covered_verandas_amount` | `X_CoveredVerandas` |
| `uncovered_verandas_amount` | `X_UncoveredVerandas` |
| `frontage_amount` | `X_Frontage` |

### Land Details

| Qobrix Field | RESO Field |
|--------------|------------|
| `building_density` | `X_BuildingDensity` |
| `coverage` | `X_Coverage` |
| `cover_factor` | `X_CoverFactor` |
| `corner_plot` | `X_CornerPlot` |
| `right_of_way` | `X_RightOfWay` |
| `registered_road` | `X_RegisteredRoad` |
| `town_planning_zone` | `X_TownPlanningZone` |
| `land_locked` | `X_LandLocked` |
| `cadastral_reference` | `X_CadastralReference` |

### Commercial

| Qobrix Field | RESO Field |
|--------------|------------|
| `ideal_for` | `X_IdealFor` |
| `licensed_for` | `X_LicensedFor` |
| `business_transfer_or_sale` | `X_BusinessTransferOrSale` |
| `business_transfer_price` | `X_BusinessTransferPrice` |
| `business_transfer_commercial_activity` | `X_BusinessActivity` |
| `conference` | `X_ConferenceRoom` |
| `server_room` | `X_ServerRoom` |
| `enclosed_office_room` | `X_EnclosedOffice` |
| `office_layout` | `X_OfficeLayout` |

### Pricing Details

| Qobrix Field | RESO Field |
|--------------|------------|
| `price_per_square` | `X_PricePerSquare` |
| `price_qualifier` | `X_PriceQualifier` |
| `plus_vat` | `X_PlusVAT` |
| `rent_frequency` | `X_RentFrequency` |
| `minimum_tenancy` | `X_MinimumTenancy` |
| `tenancy_type` | `X_TenancyType` |
| `occupancy` | `X_Occupancy` |

### Price History

| Qobrix Field | RESO Field |
|--------------|------------|
| `previous_list_selling_price` | `X_PreviousListPrice` |
| `previous_list_rental_price` | `X_PreviousLeasePrice` |
| `list_selling_price_modified` | `X_ListPriceModified` |
| `list_rental_price_modified` | `X_LeasePriceModified` |

### Auction

| Qobrix Field | RESO Field |
|--------------|------------|
| `auction_start_date` | `X_AuctionStartDate` |
| `auction_end_date` | `X_AuctionEndDate` |
| `reserve_price_amount` | `X_ReservePrice` |
| `starting_bidding_amount` | `X_StartingBid` |

### Project/Development

| Qobrix Field | RESO Field |
|--------------|------------|
| `project` | `X_ProjectId` |
| `developer_id` | `X_DeveloperId` |

### Marketing

| Qobrix Field | RESO Field |
|--------------|------------|
| `featured` | `X_Featured` |
| `featured_priority` | `X_FeaturedPriority` |
| `property_of_the_month` | `X_PropertyOfTheMonth` |
| `video_link` | `X_VideoLink` |
| `virtual_tour_link` | `X_VirtualTourLink` |
| `website_url` | `X_WebsiteUrl` |
| `website_status` | `X_WebsiteStatus` |
| `short_description` | `X_ShortDescription` |
| `name` | `X_PropertyName` |

### Property Subtypes (Detailed)

| Qobrix Field | RESO Field |
|--------------|------------|
| `apartment_type` | `X_ApartmentType` |
| `house_type` | `X_HouseType` |
| `land_type` | `X_LandType` |
| `office_type` | `X_OfficeType` |
| `retail_type` | `X_RetailType` |
| `industrial_type` | `X_IndustrialType` |
| `hotel_type` | `X_HotelType` |
| `building_type` | `X_BuildingType` |
| `investment_type` | `X_InvestmentType` |

### Parking Details

| Qobrix Field | RESO Field |
|--------------|------------|
| `customer_parking` | `X_CustomerParking` |

### Feature Arrays (JSON)

| Qobrix Field | RESO Field |
|--------------|------------|
| `additional_features` | `X_AdditionalFeatures` |
| `interior_features` | `X_InteriorFeatures` |
| `exterior_features` | `X_ExteriorFeatures` |
| `community_features` | `X_CommunityFeatures` |
| `lot_features` | `X_LotFeatures` |
| `security_features` | `X_SecurityFeatures` |
| `appliances` | `X_Appliances` |

### Qobrix Metadata

| Qobrix Field | RESO Field |
|--------------|------------|
| `id` | `X_QobrixId` |
| `ref` | `X_QobrixRef` |
| `source` | `X_QobrixSource` |
| `legacy_id` | `X_QobrixLegacyId` |
| `seller` | `X_QobrixSellerId` |
| `created` | `X_QobrixCreated` |
| `modified` | `X_QobrixModified` |

---

## Bronze-Only Fields (Not Mapped to Gold)

These fields are available in the bronze layer but not mapped to gold due to being:
- System/audit fields
- Internal tracking
- Nested entity references

| Field | Reason |
|-------|--------|
| `trashed` | Soft delete flag |
| `cloned_from` | Internal tracking |
| `original_ref`, `original_name` | Migration data |
| `original_website_url` | Historical |
| `created_by`, `modified_by` | Audit (UUIDs only) |
| `location` | UUID reference |
| `media` | JSON blob |
| `group`, `group_id` | Internal grouping |
| `campaign_id` | Marketing internal |
| `key_holder_details` | Operational |
| `inherit_project_media` | Internal flag |
| `geocode_type` | Technical |
| `direct_sources` | Lead tracking |
| `source_description` | Lead tracking |
| `engagement_letter_date` | Legal/internal |
| `inspection_date` | Internal |
| `last_media_update` | Internal |
| `website_listing_date` | Internal |
| `price_field_amount` | Unknown purpose |
| `developer` | JSON blob |
| `custom_*` | Instance-specific custom fields |
| Nested entity fields | Flattened references |

---

## Other RESO Resources

### Member (from agents/users)

| Qobrix Field | RESO Field |
|--------------|------------|
| `id` | `MemberKey` |
| `email` | `MemberEmail` |
| `first_name` | `MemberFirstName` |
| `last_name` | `MemberLastName` |
| `phone_number` | `MemberDirectPhone` |
| `mobile_number` | `MemberMobilePhone` |
| `agency_id` | `OfficeKey` |

### Office (from agents)

| Qobrix Field | RESO Field |
|--------------|------------|
| `agency_id` | `OfficeKey` |
| `agency_name` | `OfficeName` |
| `agency_email` | `OfficeEmail` |
| `agency_phone` | `OfficePhone` |

### Media (from property_media)

| Qobrix Field | RESO Field |
|--------------|------------|
| `id` | `MediaKey` |
| `property_id` | `ResourceRecordKey` |
| `file_url` | `MediaURL` |
| `file_type` | `MediaType` |
| `file_category` | `MediaCategory` |
| `order` | `Order` |

### Contacts

| Qobrix Field | RESO Field |
|--------------|------------|
| `id` | `ContactKey` |
| `first_name` | `ContactFirstName` |
| `last_name` | `ContactLastName` |
| `email` | `ContactEmail` |
| `phone_number` | `ContactPhone` |

### ShowingAppointment (from property_viewings)

| Qobrix Field | RESO Field |
|--------------|------------|
| `id` | `ShowingKey` |
| `property_id` | `ListingKey` |
| `contact_id` | `BuyerAgentKey` |
| `viewing_date` | `ShowingStartTimestamp` |
| `status` | `ShowingStatus` |

---

## Newly Added RESO Standard Fields (4)

These fields were added to improve RESO compliance from 85% to 92%:

| RESO Field | Qobrix Source | Transformation |
|------------|---------------|----------------|
| `BathroomsHalf` | `wc_bathrooms` | Direct (WC = half bath) |
| `LotSizeAcres` | `plot_area_amount` | `plot_area * 0.000247105` (m² → acres) |
| `LeaseAmountFrequency` | `rent_frequency` | monthly→Monthly, weekly→Weekly, etc. |
| `ListOfficeKey` | `agent` | `CONCAT('QOBRIX_OFFICE_', agent)` |

### RESO Core Coverage: 48/52 (92%)

**Still Missing (no Qobrix equivalent):**
- `OriginalListPrice` - Qobrix doesn't track original price
- `ClosePrice` - Qobrix doesn't track sale price
- `PrivateRemarks` - No private notes field
- `BathroomsFull` - Only total bathrooms available

---

## Dash (Sotheby's) → RESO Data Mapping

**NEW: January 2026** - The API now includes data from Dash/Sotheby's International Realty.

### Data Source Identification

| Field | Qobrix Value | Dash Value | Description |
|-------|--------------|------------|-------------|
| `OriginatingSystemOfficeKey` | `CSIR` | `HSIR` | Office identifier for multi-tenant filtering |
| `X_DataSource` | `qobrix` | `dash_sothebys` | Explicit data source tag |
| `ListingKey` | `QOBRIX_{id}` | `DASH_{listingGuid}` | Unique identifier prefix |

### Dash JSON → Bronze → Silver → Gold Pipeline

```
dash_hsir_source/*.json → dash_bronze.properties → dash_silver.property → reso_gold.property
                        → dash_bronze.media      → dash_silver.media    → reso_gold.media
                                                 → dash_silver.property_features (parsed from JSON)
```

---

## Dash Property Field Mapping

### Core Identifiers

| Dash JSON Path | Bronze Column | Silver Column | RESO Gold Field |
|----------------|---------------|---------------|-----------------|
| `listingGuid` | `id` | `dash_id` | `ListingKey` (DASH_ prefix) |
| `listingId` | `ref` | `dash_ref` | `ListingId` |
| `statusCode` | `status` | `status` | `StandardStatus` |
| `listingUrl` | `listing_url` | `listing_url` | `X_ListingUrl` |

### Status Mapping

| Dash Status | RESO StandardStatus |
|-------------|---------------------|
| `AC` | `Active` |
| `PS` | `Pending` |
| `CL` | `Closed` |
| `WD` | `Withdrawn` |

### Property Details

| Dash JSON Path | Bronze Column | RESO Gold Field | Notes |
|----------------|---------------|-----------------|-------|
| `propertyDetails.noOfBedrooms` | `bedrooms` | `BedroomsTotal` | INT |
| `propertyDetails.fullBath` | `bathrooms` | `BathroomsTotalInteger` | INT |
| `propertyDetails.halfBath` | `half_bath` | `BathroomsHalf` | INT |
| `propertyDetails.livingArea` | `living_area` | `LivingArea` | Converted to m² |
| `propertyDetails.lotSize` | `lot_size` | `LotSizeSquareFeet` | Converted to m² |
| `propertyDetails.yearBuilt` | `year_built` | `YearBuilt` | INT |
| `listPrice` | `list_selling_price_amount` | `ListPrice` | DECIMAL |
| `listPriceInUSD` | `list_price_usd` | `X_ListPriceUSD` | DECIMAL |
| `currencyCode` | `currency_code` | `X_CurrencyCode` | STRING |
| `daysOnMarket` | `days_on_market` | `DaysOnMarket` | INT |

### Location

| Dash JSON Path | Bronze Column | RESO Gold Field |
|----------------|---------------|-----------------|
| `propertyDetails.location.addressLine1` | `street` | `UnparsedAddress` |
| `propertyDetails.location.city` | `city` | `City` |
| `propertyDetails.location.stateProvinceCode` | `state` | `StateOrProvince` |
| `propertyDetails.location.postalCode` | `post_code` | `PostalCode` |
| `propertyDetails.location.countryCode` | `country` | `Country` |
| `propertyDetails.location.district` | `district` | `X_District` |
| `propertyDetails.location.latitude` | `latitude` | `Latitude` |
| `propertyDetails.location.longitude` | `longitude` | `Longitude` |

### Agent/Office (from primaryAgent)

| Dash JSON Path | Bronze Column | RESO Gold Field |
|----------------|---------------|-----------------|
| `primaryAgent.personGuid` | `agent_id` | `ListAgentKey` (DASH_AGENT_ prefix) |
| `primaryAgent.firstName` | `agent_first_name` | `ListAgentFirstName` |
| `primaryAgent.lastName` | `agent_last_name` | `ListAgentLastName` |
| `primaryAgent.primaryEmailAddress` | `agent_email` | `ListAgentEmail` |
| `primaryAgent.defaultPhotoUrl` | `agent_photo_url` | `X_ListAgentPhotoUrl` |
| `primaryAgent.company.companyGuid` | `company_id` | `ListOfficeKey` |
| `primaryAgent.company.companyName` | `company_name` | `ListOfficeName` |

### Features (Parsed from features[] array)

Features are extracted from the `features` JSON array and aggregated by `featureGroupDescription`:

| Feature Group | Silver Column | RESO Gold Field |
|---------------|---------------|-----------------|
| `Cooling` | `cooling_features` | `Cooling` |
| `Heating Type` | `heating_features` | `Heating` |
| `Heating - Fuel Type` | `heating_fuel` | `X_HeatingFuel` |
| `Pool Description` | `pool_features` | `PoolFeatures` |
| `Fireplace Description` | `fireplace_features` | `FireplaceFeatures` |
| `Garage Description` | `garage_features` | `ParkingFeatures` |
| `Flooring` | `flooring` | `Flooring` |
| `Views` | `view` | `View` |
| `Fencing` | `fencing` | `Fencing` |
| `Exterior Living Space` | `patio_porch_features` | `PatioAndPorchFeatures` |
| `Exterior` | `exterior_features` | `ExteriorFeatures` |
| `Interior` | `interior_features` | `InteriorFeatures` |
| `Appliances` | `appliances` | `Appliances` |
| `Kitchen Features` | `kitchen_features` | `X_KitchenFeatures` |
| `Bath Features` | `bath_features` | `X_BathFeatures` |
| `Basement` | `basement` | `Basement` |
| `Roof` | `roof` | `Roof` |
| `Water` | `water_source` | `WaterSource` |
| `Sewer` | `sewer` | `Sewer` |
| `Electrical` | `electric` | `Electric` |
| `Lot Description` | `lot_features` | `LotFeatures` |
| `Amenities` | `amenities` | `AssociationAmenities` |
| `Body of Water` | `waterfront_features` | `WaterfrontFeatures` |
| `Road Type` | `road_surface` | `RoadSurfaceType` |
| `Age` | `property_condition` | `PropertyCondition` |
| `Lifestyles` | `lifestyles` | `X_Lifestyles` |
| `Special Market` | `special_market` | `X_SpecialMarket` |

### Boolean Fields

| Dash JSON Path | Bronze Column | RESO Gold Field |
|----------------|---------------|-----------------|
| `isOffTheMarket` | `is_off_market` | - |
| `isForAuction` | `is_for_auction` | `X_IsAuction` |
| `isNewConstruction` | `is_new_construction` | `NewConstructionYN` |
| `isPriceUponRequest` | `is_price_upon_request` | `X_PriceUponRequest` |
| (features contains Fireplace) | `has_fireplace` | `FireplaceYN` |
| (features contains Pool) | `has_pool` | - |

---

## Dash Media Field Mapping

| Dash JSON Path | Bronze Column | RESO Gold Field |
|----------------|---------------|-----------------|
| `media[].mediaGuid` | `id` | `MediaKey` (DASH_MEDIA_ prefix) |
| `listingGuid` | `property_id` | `ResourceRecordKey` |
| `media[].path` | `url` | `MediaURL` |
| `media[].formatCode` | `format_code` | `MediaCategory` (IM→Photo) |
| `media[].sequenceNumber` | `sequence_number` | `Order` |
| `media[].caption` | `caption` | `ShortDescription` |
| `media[].description` | `description` | `LongDescription` |
| `media[].width` | `width` | `ImageWidth` |
| `media[].height` | `height` | `ImageHeight` |
| `media[].isDefault` | `is_default` | `PreferredPhotoYN` |

---

## Combined Data Source Summary

### Property Fields Available by Source

| RESO Field | Qobrix | Dash | Notes |
|------------|--------|------|-------|
| `ListingKey` | ✅ | ✅ | Different prefix |
| `ListPrice` | ✅ | ✅ | |
| `StandardStatus` | ✅ | ✅ | |
| `BedroomsTotal` | ✅ | ✅ | |
| `BathroomsTotalInteger` | ✅ | ✅ | |
| `BathroomsHalf` | ✅ | ✅ | |
| `LivingArea` | ✅ | ✅ | |
| `YearBuilt` | ❌ | ✅ | Dash only |
| `View` | ❌ | ✅ | Dash only (from features) |
| `Flooring` | ❌ | ✅ | Dash only (from features) |
| `Heating` | ❌ | ✅ | Dash only (from features) |
| `Cooling` | ❌ | ✅ | Dash only (from features) |
| `PoolFeatures` | ❌ | ✅ | Dash only (from features) |
| `ParkingFeatures` | ❌ | ✅ | Dash only (from features) |
| `ListAgentKey` | ✅ | ✅ | Different format |
| `ListAgentFirstName` | ❌ | ✅ | Dash only |
| `ListAgentLastName` | ❌ | ✅ | Dash only |
| `PublicRemarks` | ✅ | ✅ | |
| `DevelopmentStatus` | ✅ | ❌ | Qobrix only |
| `ImageWidth` | ❌ | ✅ | Dash media only |
| `ImageHeight` | ❌ | ✅ | Dash media only |

