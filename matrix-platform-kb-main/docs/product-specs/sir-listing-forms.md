# SIR Listing Form Specifications — Reference Source

> Source: `dash/BlankForm_*.docx` (6 form templates from SIR Anywhere.com / Sotheby's International Realty)
>
> **Role in Sharp Matrix**: These forms are a **reference source** — they document what fields
> brokers currently fill in when creating listings. Sharp Matrix uses these to ensure all
> required business fields are covered, mapped to RESO DD standard names.
> See [property-field-mapping.md](../data-models/property-field-mapping.md) for the RESO ← SIR mapping.

## Residential Sale Listing

### Form Sections & Fields

#### Section 1: Seller Details
| Field | Required | Picklist Values |
|-------|----------|----------------|
| Name of the Seller (as per agreement) | Yes | — |
| Contact person if Seller is a Company | No | — |
| Telephone | Yes | — |
| E-mail | Yes | — |
| Source of contact | Yes | Personal, Introducer, Company/CRM |
| Country of origin/residence | No | — |
| Preferred method of communication | No | — |
| Keyholder/Representative in CY | No | — |
| Telephone/email of keyholder | No | — |
| Keys in the office (yes/no) | Yes | YES / NO |

#### Section 2: Selling Details
| Field | Required | Picklist Values | Website Visible |
|-------|----------|----------------|-----------------|
| Price € | Yes | — | Yes |
| +VAT (yes/no) | Yes | YES / NO | Yes |
| VAT expiration date | No | — | No |
| Commissions % | Yes | — | No |
| Introducer fee | No | — | Not visible to seller |
| Exclusivity (yes/no) | Yes | YES / NO | Yes |
| Title deeds availability | Yes | YES / NO | Yes |
| Suitable for PR | Yes | YES / NO | Yes |
| Excluded from Marketing | No | YES / NO | No |
| Who else is selling | No | — | No |
| Where payments accepted | No | — | No |
| Seller's Banks of preference | No | — | No |
| Crypto payment possible | No | YES / NO | No |
| Check-list Data approved by Seller | Yes | YES / NO | No |

#### Section 3: Property Technical Details (Apartment)
| Field | Required | Picklist Values | Website Visible |
|-------|----------|----------------|-----------------|
| City, Area of location | Yes | — | Yes |
| Google maps point | Yes | — | Extended area |
| Address: str, № | Yes | — | No |
| Project name and unit number | No | — | No |
| Link to photos | Yes | — | Yes |
| Type of property | Yes | Apartment (standard), Duplex, Ground Floor, Penthouse, Studio, Whole Floor | Yes |
| Number of floors in building | Yes | Number | Yes |
| What floor | Yes | Number | Yes |
| № Bedrooms | Yes | Number | Yes |
| № Bathrooms | Yes | Number | Yes |
| № Guest WC | No | Number | Yes |
| Views | Yes | City, Garden, Mountain, Pool, Sea | Yes |
| Internal area (sq.m.) | Yes | Number | Yes |
| Covered Verandas (sq.m.) | Yes | Number | Yes |
| Covered area (calculated) | Auto | internal + covered verandas | Yes |
| Uncovered Verandas (sq.m.) | No | Number | Yes |
| Uncovered area (sq.m.) | No | Number | Yes |
| Roof garden (sq.m.) | No | Number | Yes |
| Garden area (sq.m.) | No | Number | Yes |
| Total area (sq.m.) | Auto | Sum of all areas | Yes |
| Elevator | Yes | YES / NO | Yes |
| Store room | Yes | YES / NO | Yes |
| Maid's room | No | YES / NO | Yes |
| Separate laundry room | No | YES / NO | Yes |
| Smart home | No | YES / NO | Yes |
| Swimming Pool | Yes | Private, Communal, None | Yes |
| Parking Covered Count | Yes | Number | Yes |
| Parking Uncovered Count | No | Number | Yes |
| Year of construction | Yes | — | Yes |
| Year of renovation | No | — | Yes |
| Furnishing | Yes | Furnished, Semi_furnished, Optionally_furnished, Unfurnished | Yes |
| Appliances/white goods | Yes | YES / NO | Yes |
| Air condition, VRV | Yes | YES / NO | Yes |
| Heating Type | Yes | Autonomous_heating_system, None | Yes |
| Heating Medium | Yes | underfloor_heating, fan_coil, electric_heating, gas, heat_pump, geothermal, lpg, fireplace, storage_heating, petrol, none | Yes |
| Amenities (complex) | No | — | Yes |
| Additional Extras | No | — | Yes |
| Distance to beach | No | — | Yes |
| Special notes | No | — | Yes |
| Property description (180 words) | Yes | — | Yes |

#### Section 4: Document Checklist
**With Title Deed**: Copy of Title Deed + Plans
**Without Title Deed**: Contract of Sale + Land Title Deed + Building Permit + Plans + Certificate of Final Approval

#### Section 5: Listing Agreement
- Listing agreement signed (yes/no)

#### Section 6: Viewing Checklist
- Key holder, Contact person, Notice requirements

### House-Specific Differences
- No "Number of floors in building" / "What floor"
- Has "Plot area (sq.m.)" instead of "Garden area for ground-floor"

### Land-Specific Fields
| Field | Picklist Values |
|-------|----------------|
| Total land area (sq.m.) | Number |
| Land Type | Agricultural, Field, Plot, Plot within settlement |
| Town Planning Zone | Agricultural, Commercial, Industrial, Residential, Tourist, Other |
| Building Type | Commercial, Mixed-use, Office, Residential, Retail |
| Building density % | Number |
| Coverage % | Number |
| Floors allowed | Number |
| Height allowed (m) | Number |
| Electricity Type | Single_phase, Three_phase, Industrial |

### Multiple Apartments
Same as Apartment form but with columns for up to 4 units (B, C, D, E) sharing common seller details.

## Commercial Sale Listing (SIR Form)

### Property Subtypes & Styles

| Subtype | Styles |
|---------|--------|
| Hospitality | Bed & Breakfast, Hotel/Motel, Resort Business |
| Industrial | Flex Space, Manufacturing, R&D, Warehouse |
| Multi-Family | 2-4 Units, 5-20 Units, Over 20 Units |
| Office Building | General, Government, Medical, Condo |
| Retail | Restaurant, Auto/Vehicle, Daycare, Free Standing, Street Retail, General Use, Local Strip, Neighborhood Center, Regional Mall, SGL User (BigBox), Business |
| Other | Other Style |

### Commercial-Specific Fields
- Property Name, Building Area, Year Built
- Number of Floors, Zoning, Lot Size
- Parking Spaces (total, covered, uncovered)
- Net Operating Income, Capitalization Rate, Gross Income
- Operating Expense, Tax Amount, Tax Year

## Commercial Lease Listing (SIR Form)

Same property types as Commercial Sale, with lease-specific fields:
- Minimum Lease Rate, Maximum Lease Rate
- Date Available, Lease Type, Expires On

## Residential Rental Listing

Same property details as Residential Sale, with rental-specific fields:
- Monthly Rent, Date Available, Lease Term, Furnished status

## Person (Contact) Form

### SIR Contact Fields
- Title, First Name, Middle Name, Last Name, Suffix
- Company Name, Job Title
- Phone (Business, Mobile, Home, Fax)
- Email (Primary, Secondary)
- Address (Business, Home)
- Social Media (LinkedIn, Facebook, Twitter, Instagram, Other)
- Notes, Tags, Source

## Team Form

### SIR Team Fields
- Team Name, Team Description
- Team Leader (Person)
- Office Association
- Team Members list
- Team Phone, Team Email, Team Website
