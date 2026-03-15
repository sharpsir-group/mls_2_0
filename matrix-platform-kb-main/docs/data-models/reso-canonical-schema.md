# RESO DD 2.0 — Interoperability Standard for Sharp Matrix

> RESO DD 2.0 provides the **interoperability standard** for syndication, portal exports,
> and the RESO Web API. For everyday app development, use Dash field names from
> [dash-data-model.md](dash-data-model.md). This document maps RESO resources to Dash fields.

## Resources Used by Sharp Matrix

| RESO Resource | Sharp Matrix Usage | Primary Apps |
|--------------|-------------------|--------------|
| **Property** | Listings: residential sale, lease, commercial, land | Broker, Manager, Client Portal, Marketing |
| **Member** | Broker/agent profiles and assignments | Broker, Manager, SSO Console |
| **Office** | Brokerage offices and regional offices | Manager |
| **Contacts** | Buyers, sellers, leads, prospects | Broker, Manager, Client Portal, AI Copilot |
| **Teams** | Agent teams and team assignments | Manager |
| **Media** | Photos, videos, floor plans, documents | Broker, Marketing |
| **ShowingAppointment** | Property viewings and scheduling | Broker, Client Portal |
| **HistoryTransactional** | Closed transactions, deal history | Manager, Finance |
| **OpenHouse** | Open house events | Broker, Marketing |
| **Prospecting** | Lead scoring, prospect status tracking | Broker, AI Copilot |

## Property Resource — Field Classification

### Required Fields (must be populated for every listing)

| StandardName | Type | Why Required |
|-------------|------|-------------|
| ListingId | String | Unique identifier across all apps |
| StandardStatus | Lookup | Listing lifecycle (Active, Pending, Closed, etc.) |
| PropertyType | Lookup | Residential, CommercialSale, CommercialLease, Farm, Land |
| PropertySubType | Lookup | Apartment, SingleFamilyResidence, Townhouse, etc. |
| ListPrice | Number | Listing price in EUR |
| City | String | Location city |
| Country | String | Country (CY, HU, KZ) |
| BedroomsTotal | Number | Bedroom count (residential) |
| BathroomsFull | Number | Full bathroom count |
| LivingArea | Number | Internal area in sq.m. |
| LivingAreaUnits | Lookup | Always "SquareMeters" for Sharp Matrix |
| PublicRemarks | String | Property description (130-190 words) |
| ListAgentKey | String | Assigned listing agent |
| ListingContractDate | Date | When listing agreement was signed |

### Recommended Fields (should be populated when available)

| StandardName | Type | Usage |
|-------------|------|-------|
| StreetNumber, StreetName | String | Full address |
| PostalCode | String | Postal code |
| Latitude, Longitude | Number | Map coordinates |
| BuildingAreaTotal | Number | Total area including verandas |
| LotSizeArea | Number | Plot/garden area |
| StoriesTotal | Number | Floors in building |
| Stories | Number | Unit floor level |
| YearBuilt | Number | Construction year |
| View | Lookup Multi | Sea, Mountain, City, Garden, Pool |
| Heating | Lookup Multi | Central, Electric, HeatPump, etc. |
| Cooling | Lookup Multi | CentralAir, WallUnit |
| Furnished | Lookup | Furnished, PartiallyFurnished, Unfurnished |
| PoolPrivateYN | Boolean | Private pool flag |
| CoveredSpaces | Number | Covered parking count |
| OpenParkingSpaces | Number | Open parking count |
| Appliances | Lookup Multi | White goods / appliances |
| AssociationAmenities | Lookup Multi | Complex amenities |
| PrivateRemarks | String | Agent-only notes |
| ExclusiveAgency | Boolean | Exclusive listing flag |
| ListAgentCommission | Number | Commission percentage |
| OriginalListPrice | Number | Original asking price |
| DaysOnMarket | Number | Days since listing (calculated) |
| ExpirationDate | Date | Listing expiration |

### Optional Fields (context-dependent)

| StandardName | Type | When Used |
|-------------|------|-----------|
| StorageArea | Boolean/Number | Store room presence/size |
| WaterfrontFeatures | Lookup Multi | Beachfront properties |
| Zoning | String | Land listings |
| Electric | Lookup | Land listings — electricity type |
| BathroomsHalf | Number | Guest WC |
| BuildingName | String | Project-based developments |
| UnitNumber | String | Unit within a project |
| ParkingFeatures | Lookup Multi | Detailed parking |
| Directions | String | Access directions |

## Contacts Resource — Field Classification

### Required Fields

| StandardName | Type |
|-------------|------|
| ContactFirstName | String |
| ContactLastName | String |
| ContactEmail | String |
| ContactPhone | String |

### Recommended Fields

| StandardName | Type |
|-------------|------|
| ContactCountry | String |
| LeadSource | Lookup |

## Member Resource — Field Classification

### Required Fields

| StandardName | Type |
|-------------|------|
| MemberFirstName | String |
| MemberLastName | String |
| MemberEmail | String |
| MemberMlsId | String |
| MemberStatus | Lookup |

## Platform Extension Naming Convention

When a field needed by Sharp Matrix does not exist in RESO DD 2.0:

1. **Prefix**: All extensions use `x_sm_` (Sharp Matrix)
2. **Naming**: Use snake_case after prefix, descriptive of the field's purpose
3. **Examples**: `x_sm_vat_applicable`, `x_sm_crypto_payment`, `x_sm_suitable_for_pr`

### Extension Governance Process

| Step | Action | Who |
|------|--------|-----|
| 1 | Verify the field does not exist in RESO DD 2.0 (check all resources) | Developer |
| 2 | Check if another RESO field can serve the same purpose with a different lookup value | Developer |
| 3 | Propose the extension with: name, type, reason, which apps need it | Developer |
| 4 | Register in [platform-extensions.md](platform-extensions.md) | Developer |
| 5 | Add to the app's data schema with `x_sm_` prefix | Developer |

### Rules for Extensions

- Extensions MUST NOT override or shadow existing RESO field names
- Extensions MUST be documented in `platform-extensions.md` before use
- Extensions SHOULD be as specific as possible (prefer `x_sm_vat_applicable` over `x_sm_tax_flag`)
- Lookup extensions (new picklist values) for existing RESO fields should be prefixed with `x_sm_` in the lookup value name
- When RESO DD adds a field that matches an existing extension, migrate to the RESO name

## Cross-Reference

| For | See |
|-----|-----|
| Full RESO DD 2.0 field list | [reso-dd-fields-summary.md](../references/reso-dd-fields-summary.md) |
| All platform extensions | [platform-extensions.md](platform-extensions.md) |
| Field mapping (RESO ← Qobrix ← SIR) | [property-field-mapping.md](property-field-mapping.md) |
| Raw RESO data | `reso dd/RESO_Data_Dictionary_2.0.xlsx` |
