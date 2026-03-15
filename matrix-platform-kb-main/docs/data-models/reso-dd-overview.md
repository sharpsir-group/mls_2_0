# RESO Data Dictionary 2.0 — Interoperability Standard

> Source: `reso dd/RESO_Data_Dictionary_2.0.xlsx` (XLSX created 2024-10-14, DD Wiki Version 2.0, Wiki Date 04/16/2024)
> Ratified: October 23, 2023 — current standard for RESO certification testing
>
> **For Lovable**: For app development, use Dash-derived field names from
> [dash-data-model.md](dash-data-model.md). RESO DD names are used for syndication
> and the RESO Web API only.

## RESO DD's Role in Sharp Matrix

RESO DD 2.0 is the **interoperability standard** for the Sharp Matrix Platform. It provides industry-standard field names for data exchange, syndication, and external APIs — but it is not the everyday field naming convention used by apps.

| Use Case | Field Names |
|----------|-------------|
| App development (CDL tables, UI, queries) | **Dash-derived** (`list_price`, `bedrooms`, `city`) |
| RESO Web API (outbound data feed) | **RESO DD** (`ListPrice`, `BedroomsTotal`, `City`) |
| Portal exports (HomeOverseas, etc.) | **RESO DD** |
| MLS syndication | **RESO DD** |

### Why RESO DD Remains Important

1. **Industry alignment** — RESO is the international standard adopted by MLS systems, portals, and CRMs globally. Building on RESO means Sharp Matrix data can integrate with any RESO-compliant system.
2. **Multi-market readiness** — As Sharp Matrix expands across Cyprus, Hungary, and Kazakhstan, RESO provides a common vocabulary for cross-border syndication.
3. **ETL Gold layer** — The Databricks Gold layer stores data in RESO format for analytics and external consumers.
4. **Dash mapping** — Every Dash field has a documented RESO equivalent (see `dash-data-model.md`) for easy conversion.

## What RESO DD Defines

The RESO Data Dictionary defines **standard field names, data types, and lookup values** for real estate data exchange. It ensures interoperability between MLS systems, CRMs, portals, and applications.

## Spreadsheet Structure

| Sheet | Contents | Row Count |
|-------|----------|-----------|
| **Fields** | All standard field definitions across all resources | ~3,800 rows |
| **Lookups** | All enumeration/picklist values for lookup fields | ~15,000+ values |
| **Version Info** | DD version metadata | 5 rows |

## Fields Sheet Columns

| Column | Description |
|--------|-------------|
| ResourceName | Which RESO resource this field belongs to (e.g., Property, Member, Office) |
| StandardName | The canonical field name (e.g., `ListPrice`, `BedroomsTotal`, `City`) |
| DisplayName | Human-readable label |
| Definition | Full description of the field's meaning |
| Groups | Logical grouping (e.g., Structure, Location, Financial) |
| SimpleDataType | Data type: String, Number, Boolean, Date, String List Single/Multi, Timestamp |
| SugMaxLength | Suggested maximum character length |
| SugMaxPrecision | Suggested decimal precision for numeric fields |
| PropertyTypes | Which property types use this field (RESI, RLSE, RINC, MOBI, FARM, COMS, COML) |
| ElementStatus | Active, Deprecated, or Proposed |
| LookupName | If the field has picklist values, the name of the lookup table |

## RESO Resources (Data Tables)

| Resource | Description | Example Fields |
|----------|-------------|---------------|
| **Property** | Real estate listings | ListPrice, BedroomsTotal, BathroomsTotal, City, PostalCode, PropertyType, StandardStatus |
| **Member** | Real estate agents/brokers | MemberFirstName, MemberLastName, MemberEmail, MemberMlsId |
| **Office** | Brokerage offices | OfficeName, OfficePhone, OfficeAddress1 |
| **Contacts** | Client/lead records | ContactFirstName, ContactLastName, ContactEmail |
| **Teams** | Agent teams | TeamName, TeamLead |
| **OpenHouse** | Open house events | OpenHouseDate, OpenHouseStartTime |
| **Media** | Photos, videos, documents | MediaURL, MediaType, MediaCategory |
| **HistoryTransactional** | Transaction history | ClosePrice, CloseDate |
| **ShowingAppointment** | Showing scheduling | ShowingDate, ShowingStartTime |
| **Prospecting** | Lead/prospect tracking | ProspectingStatus |

## Property Types (RESO Abbreviations)

| Code | Full Name | Description |
|------|-----------|-------------|
| RESI | Residential | Single-family homes, condos, townhouses |
| RLSE | Residential Lease | Rental properties |
| RINC | Residential Income | Multi-family investment properties |
| MOBI | Mobile Home | Manufactured housing |
| FARM | Farm/Ranch | Agricultural properties |
| COMS | Commercial Sale | Commercial properties for sale |
| COML | Commercial Lease | Commercial properties for lease |

## Lookups Sheet Columns

| Column | Description |
|--------|-------------|
| LookupName | The lookup category (e.g., PropertyType, StandardStatus, HeatingOrCooling) |
| StandardLookupValue | The standard display value (e.g., "Residential", "Active", "Central Air") |
| LegacyODataValue | Machine-readable value for API use |
| Definition | Full description of this lookup value |
| References | Which property types use this lookup |

## Key Lookup Categories for Sharp Matrix

| LookupName | Example Values | Used For |
|-----------|---------------|----------|
| PropertyType | Residential, Commercial Sale, Commercial Lease | Property classification |
| PropertySubType | Apartment, Condominium, SingleFamilyResidence, Townhouse, Villa | Detailed type |
| StandardStatus | Active, Pending, Closed, Withdrawn, Expired | Listing status |
| Country | CY (Cyprus), HU (Hungary), KZ (Kazakhstan) | Multi-market locations |
| Heating | Central, Electric, Solar, None | Property features |
| Cooling | CentralAir, WallUnit, None | Property features |
| View | CityView, GardenView, MountainView, OceanView, PoolView | Property features |
| Furnished | Furnished, PartiallyFurnished, Unfurnished | Property condition |
| ParkingFeatures | AttachedGarage, CoveredParking, OpenParking | Parking |

## Platform Extensions Beyond RESO DD

RESO DD covers the vast majority of real estate data needs, but Sharp Matrix requires some fields specific to Cyprus/Mediterranean markets and the company's business practices. These are documented as **platform extensions** with the `x_sm_*` prefix:

- **18 extension fields** (e.g., `x_sm_vat_applicable`, `x_sm_crypto_payment`, `x_sm_suitable_for_pr`)
- **10 property subtype lookup extensions** (e.g., Penthouse, Maisonette, Bungalow)

For the full catalog, see [platform-extensions.md](platform-extensions.md).
For the governance process, see [reso-canonical-schema.md](reso-canonical-schema.md).

## How to Use This Reference

1. When defining a data field for any Sharp Matrix app, look up the RESO `StandardName` first
2. When defining picklist values, use RESO `StandardLookupValue` names
3. When building API responses, use RESO `ResourceName` as the top-level grouping
4. If no RESO field exists, propose an `x_sm_*` extension following the governance process
5. For the full field list, see [reso-dd-fields-summary.md](../references/reso-dd-fields-summary.md)
6. For the raw data, open `reso dd/RESO_Data_Dictionary_2.0.xlsx`
