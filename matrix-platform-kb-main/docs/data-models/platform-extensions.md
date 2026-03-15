# Sharp Matrix Platform Extensions (x_sm_*)

> Fields and lookup values required by Sharp Matrix that do not exist in RESO DD 2.0.
> All extensions follow the `x_sm_` prefix convention. See [reso-canonical-schema.md](reso-canonical-schema.md)
> for the governance process.

## Extension Fields — Property Resource

### Financial & Legal

| Extension Field | Data Type | Reason | SIR Source Field | Qobrix Source | Apps |
|----------------|-----------|--------|-----------------|---------------|------|
| x_sm_vat_applicable | Boolean | Cyprus VAT on property — not a RESO concept | +VAT (yes/no) | property.vat_applicable | Broker, Finance |
| x_sm_introducer_fee | Number | Fee paid to party who introduced the deal | Introducer fee | property.introducer_fee | Broker, Finance |
| x_sm_title_deeds | Boolean | Whether title deeds are available (Cyprus legal requirement) | Title deeds availability | property.title_deeds | Broker |
| x_sm_suitable_for_pr | Boolean | Whether the property qualifies buyer for Permanent Residency (Cyprus immigration) | Suitable for PR | property.suitable_for_pr | Broker, Client Portal |
| x_sm_crypto_payment | Boolean | Whether cryptocurrency payment is accepted | Crypto payment possible | property.crypto_payment | Broker, Client Portal |

### Structure & Layout

| Extension Field | Data Type | Reason | SIR Source Field | Qobrix Source | Apps |
|----------------|-----------|--------|-----------------|---------------|------|
| x_sm_uncovered_verandas | Number (sq.m.) | RESO has no separate uncovered veranda field — relevant for Mediterranean properties | Uncovered Verandas (sq.m.) | property.uncovered_verandas | Broker, Client Portal |
| x_sm_roof_garden | Number (sq.m.) | Roof garden area — common in Cyprus high-rises, not in RESO | Roof garden (sq.m.) | property.roof_garden | Broker, Client Portal |
| x_sm_elevator | Boolean | Building has elevator — not a standalone RESO field | Elevator | property.elevator | Broker, Client Portal |
| x_sm_maids_room | Boolean | Maid's/service room — common in luxury Cyprus properties | Maid's room | property.maids_room | Broker, Client Portal |
| x_sm_smart_home | Boolean | Smart home features installed | Smart home | property.smart_home | Broker, Client Portal, Marketing |
| x_sm_year_renovated | Number | Year of last renovation — RESO only has YearBuilt | Year of renovation | property.year_renovated | Broker, Client Portal |
| x_sm_extras | String | Free-text additional features not captured elsewhere | Additional Extras | property.extras | Broker |
| x_sm_heating_medium | String List | Specific heating medium (underfloor, fan coil, etc.) — RESO Heating only covers type | Heating Medium | property.heating_medium | Broker, Client Portal |

### Land & Zoning (Cyprus-specific)

| Extension Field | Data Type | Reason | SIR Source Field | Qobrix Source | Apps |
|----------------|-----------|--------|-----------------|---------------|------|
| x_sm_building_density | Number (%) | Building density percentage — Cyprus town planning regulation | Building density % | property.building_density | Broker |
| x_sm_coverage | Number (%) | Coverage percentage — Cyprus town planning regulation | Coverage % | property.coverage | Broker |
| x_sm_floors_allowed | Number | Maximum floors allowed by zoning | Floors allowed | property.floors_allowed | Broker |
| x_sm_height_allowed | Number (m) | Maximum building height allowed by zoning | Height allowed (m) | property.height_allowed | Broker |

### Contact Extensions

| Extension Field | Data Type | Reason | SIR Source Field | Qobrix Source | Apps |
|----------------|-----------|--------|-----------------|---------------|------|
| x_sm_keyholder_name | String | Property keyholder/representative in Cyprus for absentee owners | Keyholder/Representative in CY | — (custom) | Broker |
| x_sm_keyholder_contact | String | Keyholder phone/email | Telephone/email of keyholder | — | Broker |

## Extension Lookup Values — PropertySubType

RESO DD 2.0 `PropertySubType` doesn't cover all Cyprus/Mediterranean property types.
These are registered as platform-specific lookup values:

| Lookup Extension | Maps To | RESO Closest Equivalent | Reason Needed |
|-----------------|---------|------------------------|---------------|
| x_sm_duplex | Duplex Apartment | — | Multi-level apartment unit, not a standalone duplex |
| x_sm_ground_floor | Ground Floor Apartment | — | Ground-level apartment with garden access |
| x_sm_penthouse | Penthouse | — | Top-floor luxury unit (RESO has no specific subtype) |
| x_sm_whole_floor | Whole Floor Apartment | — | Entire building floor as single unit |
| x_sm_semi_detached | Semi-detached Villa | — | Semi-detached house (common in Cyprus) |
| x_sm_mansion | Mansion / Villa | — | Large luxury estate property |
| x_sm_bungalow | Bungalow | — | Single-story house |
| x_sm_maisonette | Maisonette | — | Multi-level within a building (European concept) |
| x_sm_plot | Plot (Building Land) | — | Serviced building plot (distinct from UnimprovedLand) |
| x_sm_plot_settlement | Plot within Settlement | — | Plot within settlement boundaries (Cyprus zoning) |

## Summary Statistics

| Category | Count |
|----------|-------|
| Extension fields (Property) | 16 |
| Extension fields (Contact) | 2 |
| Extension lookup values (PropertySubType) | 10 |
| **Total extensions** | **28** |

## Governance Notes

- **Regional scope**: Most extensions are Cyprus-specific or Mediterranean-specific. When Sharp Matrix expands to Hungary and Kazakhstan, additional regional extensions may be needed (e.g., Hungarian land registry fields, Kazakh property registration).
- **Retirement**: If a future RESO DD version (e.g., DD 2.1) adds a field that matches an `x_sm_*` extension, the extension should be migrated to the RESO name with a deprecation period.
- **Naming collisions**: Never reuse a retired extension name for a different purpose.

## Cross-Reference

| For | See |
|-----|-----|
| Extension governance rules | [reso-canonical-schema.md](reso-canonical-schema.md) |
| Full field mapping with extensions flagged | [property-field-mapping.md](property-field-mapping.md) |
| RESO DD 2.0 field reference | [reso-dd-fields-summary.md](../references/reso-dd-fields-summary.md) |
