# Compliance — GDPR, Data Protection, and Regulatory Requirements

> **For Lovable**: This document defines data protection requirements that affect how apps
> handle personal data. Follow these rules when building features that create, store, or
> process personal information.

## Regulatory Landscape

Sharp Matrix operates in three jurisdictions with distinct data protection regimes:

| Market | Regulation | Authority | Key Requirement |
|--------|-----------|-----------|-----------------|
| **Cyprus** (EU) | GDPR | Commissioner for Personal Data Protection | Full GDPR compliance required |
| **Hungary** (EU) | GDPR | NAIH (National Authority for Data Protection) | Full GDPR compliance required |
| **Kazakhstan** | PDPL (Personal Data Protection Law) | Ministry of Digital Development | Data localization requirements, consent-based processing |

GDPR applies to both EU markets. Kazakhstan's PDPL has similar principles but different procedural requirements.

## Data Inventory

### Personal Data by System

| System | Data Categories | Data Subjects | Legal Basis |
|--------|----------------|--------------|-------------|
| **SSO Instance** | Names, emails, phone numbers, role assignments, login history, IP addresses | Staff, brokers, agents | Contractual necessity (employment/contractor) |
| **CDL (RESO tables)** | Client names, emails, phones, budgets, property preferences, transaction history | Buyers, sellers, tenants, landlords | Legitimate interest (brokerage operations) |
| **App DBs (domain)** | Employee records (HRMS), financial records (Finance) | Staff | Contractual necessity (employment) |
| **Databricks DWH** | Listing data with agent info, contact records, transaction history | Agents, clients | Legitimate interest (analytics, BI) |
| **Audit tables** | User actions, IP addresses, user agents, change history | Staff, brokers | Legitimate interest (security, compliance) |

### Sensitive Data Categories

| Category | Where Stored | Protection |
|----------|-------------|------------|
| Financial (salary, commissions, budgets) | HRMS DB, Finance DB, CDL | Column-level masking in views, RLS scope restrictions |
| Authentication credentials | SSO Instance | Hashed (Supabase Auth), client secrets masked in audit logs |
| Health/personal (passport, tax ID) | HRMS DB | Column-level access control via CASE statements |
| Client financial (deal values, budgets) | CDL | RLS tenant + scope isolation |

## Data Retention Policy

| Data Category | Retention Period | Legal Basis | Action After Expiry |
|---------------|-----------------|-------------|-------------------|
| Active client records | Duration of business relationship + 3 years | Legitimate interest | Archive, then delete |
| Completed transactions | 7 years from completion | EU tax law (Directive 2011/16/EU) | Delete |
| Marketing consent records | Indefinitely while consent is active | GDPR Art. 7 | Delete on withdrawal |
| Inactive user profiles | 2 years from last activity | Legitimate interest | Notify, then delete |
| Audit logs | 5 years | Legitimate interest (security) | Purge |
| Pipeline/ETL logs | 1 year | Operational necessity | Rotate |
| Session/visitor data | 90 days (anonymous), linked to user retention (authenticated) | Consent (cookie banner) | Auto-purge |

## Data Subject Rights (DSAR)

GDPR Articles 15-22 grant data subjects the following rights. Each must be fulfillable within 30 days.

| Right | GDPR Article | Implementation |
|-------|-------------|----------------|
| **Access** (export) | Art. 15 | `admin-data-export` Edge Function generates a personal data package (JSON) from SSO + app DBs |
| **Rectification** (update) | Art. 16 | Standard app edit flows; admin override for locked fields |
| **Erasure** (right to be forgotten) | Art. 17 | `admin-data-delete` Edge Function cascades deletion across SSO + app DBs; Databricks records anonymized |
| **Portability** | Art. 20 | `admin-data-export` output in machine-readable JSON format |
| **Restriction** | Art. 18 | Set `processing_restricted = true` flag on user record; apps check before processing |
| **Objection** | Art. 21 | Logged via `data_deletion_requests` table; reviewed by DPO |

### DSAR Tracking

The `data_deletion_requests` table in the SSO instance tracks the lifecycle of every data subject request:

| Column | Type | Purpose |
|--------|------|---------|
| `id` | uuid | Request identifier |
| `request_type` | text | access, rectification, erasure, portability, restriction, objection |
| `subject_email` | text | Data subject's email |
| `subject_user_id` | uuid | Linked SSO user (if exists) |
| `status` | text | received, in_progress, completed, rejected |
| `requested_at` | timestamptz | When request was received |
| `completed_at` | timestamptz | When request was fulfilled |
| `handled_by` | uuid | Admin who processed the request |
| `notes` | text | Processing notes |
| `tenant_id` | uuid | Organization scope |

**SLA**: All requests must be acknowledged within 72 hours and completed within 30 calendar days (GDPR requirement).

## Cross-Border Data Transfers

| Transfer | Mechanism | Status |
|----------|----------|--------|
| **Supabase** (data hosting) | EU region deployment available | Use EU region for GDPR compliance |
| **Databricks** (DWH/ETL) | EU workspace available | Configure EU workspace |
| **Lovable** (app builder) | Code generation only; no persistent PII storage | No transfer concerns |
| **Azure AD** (SSO sync) | Standard Contractual Clauses (Microsoft DPA) | Microsoft DPA covers GDPR |
| **Cyprus ↔ Hungary** | Intra-EU, no additional mechanism required | Compliant |
| **EU ↔ Kazakhstan** | Adequacy assessment required; Kazakhstan not on EU adequacy list | Implement Standard Contractual Clauses or obtain explicit consent |

## Data Processing Agreements (DPAs)

| Vendor | Role | DPA Status | Key Terms |
|--------|------|-----------|-----------|
| **Supabase** | Data processor (CDL hosting) | Standard DPA available | GDPR-compliant, EU hosting option, SOC 2 Type II |
| **Databricks** | Data processor (ETL/DWH) | Standard DPA available | GDPR-compliant, EU workspace option |
| **Microsoft** (Azure AD) | Data processor (identity sync) | Microsoft DPA | Standard Contractual Clauses included |
| **Lovable** | Data processor (app building) | Review required | Assess PII exposure during development |

## Breach Notification

### Timeline (GDPR Article 33-34)

| Step | Deadline | Action | Responsible |
|------|----------|--------|-------------|
| 1. Detection | Immediate | Security event detected via audit logs or monitoring | Any team member |
| 2. Assessment | + 4 hours | Determine scope: affected data subjects, data types, risk level | CDTO + IT |
| 3. DPA notification | + 72 hours | Notify relevant Data Protection Authority (Cyprus or Hungary) if risk to data subjects | CDTO |
| 4. Subject notification | + 72 hours | Notify affected data subjects if high risk | CDTO + Legal |
| 5. Vendor notification | + 24 hours | Notify affected data processors (Supabase, Databricks) | CDTO |
| 6. Remediation | ASAP | Fix vulnerability, revoke compromised credentials | IT |
| 7. Documentation | + 30 days | Full incident report with root cause analysis | CDTO |

### Notification Contacts

| Authority | Market | Contact |
|-----------|--------|---------|
| Commissioner for Personal Data Protection | Cyprus | www.dataprotection.gov.cy |
| NAIH | Hungary | www.naih.hu |
| Ministry of Digital Development | Kazakhstan | www.gov.kz |

## Kazakhstan PDPL Specifics

Key differences from GDPR:

| Aspect | GDPR | Kazakhstan PDPL |
|--------|------|----------------|
| Data localization | No requirement (with adequate safeguards) | Personal data of KZ citizens must be stored in KZ (with exceptions) |
| Consent | Explicit consent for special categories | Consent required for all processing (broader scope) |
| DPO requirement | Required for large-scale processing | Not mandatory but recommended |
| Breach notification | 72 hours to DPA | No specific timeline (report "without delay") |

**Recommendation**: For Kazakhstan operations, ensure the Supabase instance or a replica handles KZ citizen data within an appropriate hosting region, and obtain explicit consent for all data processing activities.

## Implementation Status

| Component | Status | Priority |
|-----------|--------|----------|
| Data retention policy (documented) | This document | P0 |
| DSAR tracking table (`data_deletion_requests`) | Planned migration | P0 |
| `admin-data-export` Edge Function | Planned | P1 |
| `admin-data-delete` Edge Function | Planned | P1 |
| Cookie consent banner (website + Client Portal) | Planned | P1 |
| DPA review with all vendors | In progress | P0 |
| Kazakhstan data localization assessment | Planned | P2 |

## Cross-Reference

| For | See |
|-----|-----|
| Security model (auth, RLS, roles) | [security-model.md](security-model.md) |
| Operations and audit trail | [operations.md](operations.md) |
| Data models and RESO schema | [mls-cdl-schema.md](../data-models/mls-cdl-schema.md) |
| Digital strategy and markets | [digital-strategy-2026-2028.md](../vision/digital-strategy-2026-2028.md) |
