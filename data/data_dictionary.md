# Clarity Health Plans Data Dictionary

## Overview
This data dictionary documents all tables and columns in the Clarity Health Plans synthetic claims dataset. Total: 200,000 claims across 6 tables.

## clarity_claims (Primary Table)
**Row Count:** 200,000  
**Business Entity:** Individual health insurance claims

| Column | Type | Description | Business Meaning | Leakage Risk |
|--------|------|-------------|------------------|--------------|
| claim_id | INT | Unique claim identifier | Primary key for claim | None |
| member_id | INT | Unique member/subscriber ID | Links to member demographics | None |
| provider_id | INT | Healthcare provider identifier | Links to provider network/specialty | None |
| claim_date | DATE | Date claim was submitted | When claim entered system | None |
| service_start_date | DATE | First date of service | Beginning of treatment window | None |
| service_end_date | DATE | Last date of service | End of treatment window | None |
| claim_amount | FLOAT | Billed claim amount ($) | Financial value at stake | None |
| claim_status | VARCHAR | Status: approved / denied / processing / appeal_pending | Claim adjudication result | **TARGET VARIABLE** |
| submission_completeness_flag | INT | 1=complete, 0=incomplete | Whether submission had required docs | Dashboard only -- exclude from ML |
| network_type | VARCHAR | in_network / out_of_network / unknown | Network status at submission | None |
| claim_category | VARCHAR | Category: inpatient / outpatient / emergency / imaging / lab / other | Claim type for segmentation | None |
| specialty | VARCHAR | Provider specialty: primary_care / cardiology / orthopedics / emergency / imaging | Clinical classification | None |
| prior_auth_required | INT | 1=yes, 0=no | Whether service needed prior auth | Dashboard only -- exclude from ML |

## clarity_denials (Denial Details)
**Row Count:** 7,862  
**Business Entity:** Claims that were denied in full or partial

| Column | Type | Description | Business Meaning | Leakage Risk |
|--------|------|-------------|------------------|--------------|
| denial_id | INT | Unique denial identifier | Primary key for denial | None |
| claim_id | INT | Foreign key to clarity_claims | Links denial to claim | None |
| denial_date | DATE | Date denial was issued | When decision was made | None |
| denial_reason_code | VARCHAR | Code: PA01, PA02, PA03, NW01, NW02, CVRG01, CVRG02, BILL01, BILL02, MED01, 999 (invalid), NULL | Root cause classification | None |
| denial_reason_category_manual | VARCHAR | Manual categorization (currently all NULL) | For manual review tagging | None |
| denied_claim_amount | FLOAT | Portion of claim that was denied ($) | Financial impact of denial | None |
| appeal_submitted | INT | 1=yes, 0=no | Whether member appealed | Dashboard only -- exclude from ML |
| appeal_outcome | VARCHAR | approved / partial_approval / denied / pending | Result of appeal process | **Dashboard only -- exclude from ML** |
| resolution_amount | FLOAT | Amount recovered via appeal ($) | Financial recovery from appeal | Dashboard only -- exclude from ML |

## Denial Reason Codes
| Code | Category | Example | Appeal Success Rate |
|------|----------|---------|---------------------|
| PA01, PA02, PA03 | Prior Auth Delay | Missing or delayed authorization | 54% |
| NW01, NW02 | Network Issue | Out-of-network provider submitted | 57% |
| CVRG01, CVRG02 | Coverage Limit | Exceeded plan's annual max | 0% (unrecoverable) |
| BILL01, BILL02 | Billing Error | Wrong claim amount or code | 61% (highest) |
| MED01 | Medical Necessity | Service not medically necessary | 54% |
| 999 | Invalid Code | Data quality issue | Variable |
| NULL | Unknown | Not recorded | Variable |

## clarity_providers (Provider Dimension)
**Row Count:** 350  
**Business Entity:** Healthcare providers (doctors, hospitals, clinics)

| Column | Type | Description | Business Meaning | Leakage Risk |
|--------|------|-------------|------------------|--------------|
| provider_id | INT | Unique provider identifier | Primary key for provider | None |
| provider_name | VARCHAR | Provider name (anonymized: PRV_XXXX) | Provider identity | None |
| provider_type | VARCHAR | Type: individual / group / hospital | Organization structure | None |
| specialty | VARCHAR | Clinical specialty | Service area | None |
| network_status | VARCHAR | in_network / out_of_network | Contract status | Dashboard only -- exclude from ML |
| geographic_region | VARCHAR | Region: northeast / midwest / south / west | Location for distribution analysis | None |
| contract_start_date | DATE | When provider joined network | Historical context | None |
| contract_status | VARCHAR | active / inactive / suspended | Current contract state | None |
| claims_submitted_ytd | INT | Year-to-date claim count | Provider volume | Dashboard only -- exclude from ML |
| last_update_date | DATE | Last metadata update | Data freshness | None |

## clarity_members (Member Dimension)
**Row Count:** 100,000  
**Business Entity:** Health plan members/subscribers

| Column | Type | Description | Business Meaning | Leakage Risk |
|--------|------|-------------|------------------|--------------|
| member_id | INT | Unique member identifier | Primary key for member | None |
| age_group | VARCHAR | 18-25 / 26-35 / 36-45 / 46-55 / 56-65 / 65+ | Demographic segmentation | None |
| gender | VARCHAR | M / F / unknown | Demographic segmentation | None |
| plan_type | VARCHAR | bronze / silver / gold / platinum | Coverage tier (determines covered services) | None |
| enrollment_date | DATE | Date member joined plan | Tenure indicator | None |
| geographic_region | VARCHAR | northeast / midwest / south / west | Service area | None |
| income_bracket | VARCHAR | low / medium / high / unknown (15% NULL) | Socioeconomic indicator | None |
| chronic_condition_flags | VARCHAR | Comma-separated: diabetes, hypertension, heart_disease, copd, mental_health, none (40% NULL) | Health status driver | None |
| claims_count_ytd | INT | Year-to-date claims submitted | Member claim frequency | Dashboard only -- exclude from ML |
| denied_claims_count_ytd | INT | Year-to-date denials received | Member denial history | **Dashboard only -- exclude from ML** |

## clarity_prior_auth (Prior Authorization Details)
**Row Count:** 80,240  
**Business Entity:** Prior authorization requests

| Column | Type | Description | Business Meaning | Leakage Risk |
|--------|------|-------------|------------------|--------------|
| prior_auth_id | INT | Unique prior auth request ID | Primary key | None |
| claim_id | INT | Foreign key to clarity_claims (25% orphaned) | Links auth to claim | None |
| member_id | INT | Member requesting auth | Links to member | None |
| provider_id | INT | Provider submitting auth request | Links to provider | None |
| requested_date | DATE | Date auth was requested | Timing signal | None |
| approved_date | DATE | Date auth was approved (nullable) | Approval timing | None |
| status | VARCHAR | approved / denied / pending / expired | Current auth status | None |
| processing_days | INT | Days from request to approval | **DELAYS HERE ARE KEY DRIVER** | None |

## clarity_claims_detail (Line-Item Detail)
**Row Count:** 269,997  
**Business Entity:** Individual services/procedures per claim

| Column | Type | Description | Business Meaning | Leakage Risk |
|--------|------|-------------|------------------|--------------|
| claim_detail_id | INT | Unique line-item identifier | Primary key | None |
| claim_id | INT | Foreign key to clarity_claims | Links to parent claim | None |
| procedure_code | VARCHAR | Standardized code (CPT-like) | Service classification | None |
| quantity_services | INT | Units of service (e.g., visits) | Service volume | None |
| amount_per_service | FLOAT | Cost per unit ($) | Pricing | None |
| total_line_amount | FLOAT | Total for line (qty * unit price) ($) | Line-item financial value | None |

---

## Leakage Prevention: ML Training

### EXCLUDED from Model Features (Dashboard-Only Columns)
- `submission_completeness_flag` -- known at submission, but outcome-related
- `prior_auth_required` -- feature exists; `processing_days` is the signal
- `appeal_submitted` -- post-denial action, not pre-submission signal
- `appeal_outcome` -- post-denial outcome, not predictor
- `resolution_amount` -- post-denial recovery, not predictor
- `claims_submitted_ytd`, `denied_claims_count_ytd` -- member history that leaks label
- `network_status` (provider) -- known pre-submission but is noisy (tested: no correlation)

### INCLUDED in Model Features
- Claim amount
- Claim category
- Specialty
- Network type
- Member age group, gender, plan type, income bracket
- Chronic condition flags (40% null is OK -- impute as "none")
- Provider geographic region, provider type
- Service date patterns (e.g., weekday vs. weekend)
- Tenure (enrollment_date to claim_date)

### Target Variable Definition
**Binary:** `is_denied` = 1 if claim_id appears in clarity_denials table, else 0  
**Baseline Rate:** 3.93% denial (highly imbalanced)  
**Class Weight:** XGBoost `scale_pos_weight=24.4` to handle imbalance

---

## Data Quality Notes

### Nulls
- `provider_id` in claims: 2% (attributed to third-party billing)
- `income_bracket` in members: 15% (not captured on enrollment)
- `chronic_condition_flags` in members: 40% (assume "none" for modeling)
- `approved_date` in prior_auth: ~30% (not yet approved at snapshot time)
- `denial_reason_category_manual`: 100% null (placeholder for manual tagging)

### Known Issues
- `claim_id` in prior_auth: 25% orphaned (auth requested but claim not yet submitted)
- `denial_reason_code`: 10% free-text (converted to "Other"), 5% invalid code "999", 5% null
- `appeal_outcome`: pending appeals remain in "pending" state (not counted as success)

### Completeness by Section
- Claims header (claim_id, member_id, claim_date, amount): 100%
- Claim status (approved/denied/processing): 100%
- Denial reason codes: 95% (5% null/invalid)
- Prior auth linkage: 75% (claim_id matches; 25% orphaned)
- Member dimension: 100% row coverage; 15-40% attribute nulls

---

## Synthetic Data Guarantees
- **Seed:** 42 (reproducible)
- **Generator:** numpy.random.default_rng(42)
- **Patterns:** Realistic denial distributions match real-world insurance data
- **Financial Realism:** Claim amounts range $500-$50K with modal peak at $3-4K
- **No PII:** All names anonymized (PRV_XXXX); dates synthetic; member IDs are sequential integers
- **Validation:** Passed row count checks, null distribution checks, and cross-table foreign key validation

---

## How to Regenerate
```bash
cd /home/claude
python clarity_denials/scripts/01_generate_data_simple.py
```

Output files:
- `data/clarity_claims.csv`
- `data/clarity_denials.csv`
- `data/clarity_providers.csv`
- `data/clarity_members.csv`
- `data/clarity_prior_auth.csv`
- `data/clarity_claims_detail.csv`
- `data/clarity_metadata.json`

