# Property Field Mapping: RESO (Canonical) ← Qobrix ← SIR

> Cross-reference table for property data across all layers.
> **Direction**: RESO DD is the canonical name. Qobrix and SIR columns show where
> the data currently lives for migration purposes.
>
> Fields marked with `x_sm_*` are **Platform Extensions** — they don't exist in RESO DD
> and are governed by the Sharp Matrix extension process.

## Seller / Contact Details

| Sharp Matrix Field (RESO) | Qobrix Field | SIR Checklist Field | Type | Extension? |
|---------------------------|--------------|---------------------|------|------------|
| ContactFirstName, ContactLastName | contact.first_name + contact.last_name | Name of the Seller | String | — |
| — | contact.company_contact | Contact person (if Company) | String | — |
| ContactPhone | contact.phone | Telephone | String | — |
| ContactEmail | contact.email | E-mail | String | — |
| LeadSource | contact.source | Source of contact | String List | — |
| ContactCountry | contact.country | Country of origin/residence | String | — |
| — | contact.preferred_comm | Preferred method of communication | String List | — |
| **x_sm_keyholder_name** | — (custom) | Keyholder/Representative in CY | String | **Yes** |

## Selling / Financial Details

| Sharp Matrix Field (RESO) | Qobrix Field | SIR Checklist Field | Type | Extension? |
|---------------------------|--------------|---------------------|------|------------|
| ListPrice | property.list_selling_price_amount | Price € | Number | — |
| **x_sm_vat_applicable** | property.vat_applicable | +VAT (yes/no) | Boolean | **Yes** |
| ListAgentCommission | property.commission_rate | Commissions % | Number | — |
| **x_sm_introducer_fee** | property.introducer_fee | Introducer fee | Number | **Yes** |
| ExclusiveAgency | property.exclusivity | Exclusivity (yes/no) | Boolean | — |
| **x_sm_title_deeds** | property.title_deeds | Title deeds availability | Boolean | **Yes** |
| **x_sm_suitable_for_pr** | property.suitable_for_pr | Suitable for PR | Boolean | **Yes** |
| **x_sm_crypto_payment** | property.crypto_payment | Crypto payment possible | Boolean | **Yes** |

## Property Location

| Sharp Matrix Field (RESO) | Qobrix Field | SIR Checklist Field | Type | Extension? |
|---------------------------|--------------|---------------------|------|------------|
| City | property.city | City, Area | String | — |
| Latitude, Longitude | property.coordinates | Google maps point | Number | — |
| StreetNumber, StreetName | property.address | Address: str, № | String | — |
| BuildingName, UnitNumber | property.project_name, property.unit_number | Project name and unit | String | — |

## Apartment Fields

| Sharp Matrix Field (RESO) | Qobrix Field | SIR Checklist Field | Type | Extension? |
|---------------------------|--------------|---------------------|------|------------|
| PropertySubType | property.property_subtype | Type of property | String List | — |
| StoriesTotal | property.floors_in_building | Number of floors in building | Number | — |
| Stories | property.floor_number | What floor | Number | — |
| BedroomsTotal | property.bedrooms | № Bedrooms | Number | — |
| BathroomsFull | property.bathrooms | № Bathrooms | Number | — |
| BathroomsHalf | property.guest_wc | № Guest WC | Number | — |
| View | property.views | Views | String List Multi | — |
| LivingArea | property.internal_area | Internal area (sq.m.) | Number | — |
| CoveredSpaces | property.covered_verandas | Covered Verandas (sq.m.) | Number | — |
| **x_sm_uncovered_verandas** | property.uncovered_verandas | Uncovered Verandas (sq.m.) | Number | **Yes** |
| **x_sm_roof_garden** | property.roof_garden | Roof garden (sq.m.) | Number | **Yes** |
| LotSizeArea | property.garden_area | Garden area (sq.m.) | Number | — |
| BuildingAreaTotal | property.total_area | Total area (sq.m.) | Number | — |
| **x_sm_elevator** | property.elevator | Elevator | Boolean | **Yes** |
| StorageArea | property.store_room | Store room | Boolean | — |
| **x_sm_maids_room** | property.maids_room | Maid's room | Boolean | **Yes** |
| **x_sm_smart_home** | property.smart_home | Smart home | Boolean | **Yes** |
| PoolPrivateYN / PoolFeatures | property.pool_type | Swimming Pool | String List | — |
| CoveredSpaces | property.parking_covered | Parking Covered Count | Number | — |
| OpenParkingSpaces | property.parking_uncovered | Parking Uncovered Count | Number | — |
| YearBuilt | property.year_built | Year of construction | Number | — |
| **x_sm_year_renovated** | property.year_renovated | Year of renovation | Number | **Yes** |
| Furnished | property.furnishing | Furnishing | String List | — |
| Appliances | property.appliances | Appliances/white goods | Boolean | — |
| Cooling | property.air_condition | Air condition, VRV | String List | — |
| Heating | property.heating_type | Heating Type | String List | — |
| **x_sm_heating_medium** | property.heating_medium | Heating Medium | String List | **Yes** |
| AssociationAmenities | property.amenities | Amenities (complex) | String List Multi | — |
| **x_sm_extras** | property.extras | Additional Extras | String | **Yes** |
| WaterfrontFeatures | property.distance_beach | Distance to beach | String | — |
| PrivateRemarks | property.special_notes | Special notes | String | — |
| PublicRemarks | property.description | Property description | String (180w) | — |

## House-Specific Fields

| Sharp Matrix Field (RESO) | Qobrix Field | SIR Checklist Field | Type | Extension? |
|---------------------------|--------------|---------------------|------|------------|
| LotSizeArea | property.plot_area | Plot area (sq.m.) | Number | — |
| PropertySubType | property.property_subtype | Type: Detached/Semi/Townhouse | String List | — |

## Land-Specific Fields

| Sharp Matrix Field (RESO) | Qobrix Field | SIR Checklist Field | Type | Extension? |
|---------------------------|--------------|---------------------|------|------------|
| LotSizeArea | property.land_area | Total land area (sq.m.) | Number | — |
| PropertySubType | property.land_type | Land Type | String List | — |
| Zoning | property.planning_zone | Town Planning Zone | String | — |
| **x_sm_building_density** | property.building_density | Building density % | Number | **Yes** |
| **x_sm_coverage** | property.coverage | Coverage % | Number | **Yes** |
| **x_sm_floors_allowed** | property.floors_allowed | Floors allowed | Number | **Yes** |
| **x_sm_height_allowed** | property.height_allowed | Height allowed (m) | Number | **Yes** |
| Electric | property.electricity_type | Electricity Type | String List | — |

## Property Type Mapping

| RESO PropertySubType (canonical) | Qobrix property_subtype | SIR Form Type | Extension? |
|----------------------------------|------------------------|---------------|------------|
| Apartment | apartment | Apartment (standard) | — |
| — | duplex | Duplex Apartment | **x_sm_subtype needed** |
| — | ground_floor | Ground Floor Apartment | **x_sm_subtype needed** |
| — | penthouse | Penthouse | **x_sm_subtype needed** |
| Studio | studio | Studio | — |
| — | whole_floor | Whole Floor Apartment | **x_sm_subtype needed** |
| SingleFamilyResidence | detached_house | Detached House | — |
| — | semi_detached | Semi-detached Villa | **x_sm_subtype needed** |
| Townhouse | townhouse | Townhouse | — |
| — | mansion | Mansion Villa | **x_sm_subtype needed** |
| — | bungalow | Bungalow | **x_sm_subtype needed** |
| — | maisonette | Maisonette | **x_sm_subtype needed** |
| Farm | agricultural | Agricultural Land | — |
| UnimprovedLand | field | Field | — |
| — | plot | Plot | **x_sm_subtype needed** |
| — | plot_settlement | Plot within settlement | **x_sm_subtype needed** |

> **Note:** Property subtypes without a RESO equivalent need platform-defined lookup extensions.
> These should be registered in `platform-extensions.md` as `x_sm_property_subtype_*` values.

## View Mapping

| RESO View Lookup (canonical) | Qobrix Value | SIR Value |
|-----------------------------|-------------|-----------|
| City | city_view | City view |
| Garden | garden_view | Garden view |
| Mountain(s) | mountain_view | Mountain view |
| Pool | pool_view | Pool view |
| Ocean | sea_view | Sea view |

## Furnishing Mapping

| RESO Furnished Lookup (canonical) | Qobrix Value | SIR Value |
|----------------------------------|-------------|-----------|
| Furnished | furnished | Furnished |
| PartiallyFurnished | semi_furnished | Semi_furnished |
| — | optionally_furnished | Optionally_furnished |
| Unfurnished | unfurnished | Unfurnished |

## Heating Mapping

| RESO Heating Lookup (canonical) | Qobrix Value | SIR Heating Type |
|--------------------------------|-------------|-----------------|
| Central | autonomous | Autonomous heating system |
| None | none | None |

| RESO Related Lookup | Qobrix Value | SIR Heating Medium |
|--------------------|-------------|-------------------|
| Radiant | underfloor_heating | Underfloor heating |
| ForcedAir | fan_coil | Fan coil |
| Electric | electric_heating | Electric heating |
| NaturalGas | gas_heating | Gas heating system |
| HeatPump | heat_pump | Heat pump |
| Geothermal | geothermal | Geothermal energy |
| Propane | lpg | Bottle gas (LPG) |
| Fireplace | fireplace | Fireplace |
| Other | storage_heating | Storage heating |
| Other | petrol | Petrol |

## Extension Summary

This mapping identifies **18 platform extension fields** (`x_sm_*`) and **10 property subtype lookup extensions** needed beyond RESO DD 2.0. See [platform-extensions.md](platform-extensions.md) for the full governed catalog.
