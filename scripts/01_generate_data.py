"""
Clarity Health Plans - Claims Denial Analysis Dataset Generator
Author: Luciano Casillas
Version: 1.0
Date: August 2026

Generates 345,000 synthetic health insurance claims records with realistic denial patterns,
data quality issues, and relational messiness. Designed to reflect operational reality:
incomplete submissions, orphaned prior auth records, invalid denial codes, and provider
variation in denial rates.

Output files:
  - data/clarity_members.csv (145,000 rows)
  - data/clarity_providers.csv (420 rows)
  - data/clarity_claims.csv (345,000 rows)
  - data/clarity_denials.csv (21,000 rows ~6% denial rate)
  - data/clarity_prior_auth.csv (18,000 rows)
  - data/clarity_claims_detail.csv (410,000+ rows)
  - data/clarity_metadata.json (generation metadata)
"""

import pandas as pd
import numpy as np
import json
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# ============================================================
# CONFIGURATION
# ============================================================
N_CLAIMS = 345_000
N_MEMBERS = 145_000
N_PROVIDERS = 420
DENIAL_RATE_BASELINE = 0.061
SEED = 42
VERSION = "1.0"

np.random.seed(SEED)

print("="*70)
print(f"CLARITY HEALTH PLANS - CLAIMS DENIAL DATASET GENERATOR v{VERSION}")
print("="*70)
print(f"Target rows: {N_CLAIMS:,} claims")
print(f"Target members: {N_MEMBERS:,}")
print(f"Target providers: {N_PROVIDERS}")
print(f"Baseline denial rate: {DENIAL_RATE_BASELINE*100:.1f}%")
print(f"Seed: {SEED}")
print()

# ============================================================
# PHASE 1: GENERATE MEMBERS TABLE (145,000 rows)
# ============================================================
print("PHASE 1: Generating MEMBERS table (145,000 rows)")

member_ids = np.arange(1, N_MEMBERS + 1)
age_groups = np.random.choice(['<18', '18-30', '31-45', '46-65', '65+'], 
                               size=N_MEMBERS, 
                               p=[0.08, 0.18, 0.22, 0.28, 0.24])
genders = np.random.choice(['M', 'F', 'unknown'], size=N_MEMBERS, p=[0.48, 0.48, 0.04])
plan_types = np.random.choice(['bronze', 'silver', 'gold', 'platinum', 'medicaid'], 
                               size=N_MEMBERS, 
                               p=[0.15, 0.25, 0.30, 0.20, 0.10])
regions = np.random.choice(['northeast', 'midwest', 'south', 'west'], 
                            size=N_MEMBERS, 
                            p=[0.22, 0.24, 0.31, 0.23])

# Income bracket: biased so low-income members have more missing data
income_bracket = np.random.choice(['low', 'medium', 'high', 'unknown'], 
                                   size=N_MEMBERS, 
                                   p=[0.20, 0.35, 0.30, 0.15])

# Enrollment date: spread over past 5 years
enrollment_dates = [datetime(2019, 1, 1) + timedelta(days=int(x)) 
                     for x in np.random.uniform(0, 365*5, N_MEMBERS)]

# Chronic condition flags: 40% null, biased toward low-income
chronic_flags = []
for i in range(N_MEMBERS):
    if np.random.random() < 0.40:
        chronic_flags.append(None)
    elif np.random.random() < 0.35:
        chronic_flags.append('diabetes')
    elif np.random.random() < 0.25:
        chronic_flags.append('heart_disease')
    elif np.random.random() < 0.20:
        chronic_flags.append('mental_health')
    elif np.random.random() < 0.15:
        chronic_flags.append('respiratory')
    else:
        chronic_flags.append('none')

# Add bias: low-income members have MORE chronic conditions
for i in range(len(income_bracket)):
    if income_bracket[i] == 'low' and chronic_flags[i] is None:
        if np.random.random() < 0.30:  # 30% of low-income nulls → convert to condition
            chronic_flags[i] = np.random.choice(['diabetes', 'heart_disease', 'mental_health'])

members = pd.DataFrame({
    'member_id': member_ids,
    'member_name': [f'MBR_{i:06d}' for i in member_ids],
    'age_group': age_groups,
    'gender': genders,
    'plan_type': plan_types,
    'enrollment_date': enrollment_dates,
    'geographic_region': regions,
    'income_bracket': income_bracket,
    'chronic_condition_flags': chronic_flags,
    'claims_count_ytd': 0,  # will update after claims generated
    'denied_claims_count_ytd': 0  # will update after denials generated
})

# Add duplicate member IDs (0.3% - data migration artifact)
n_dups = int(N_MEMBERS * 0.003)
dup_indices = np.random.choice(N_MEMBERS, size=n_dups, replace=False)
for idx in dup_indices:
    if np.random.random() < 0.5:  # 50% chance to duplicate
        dup_date = members.loc[idx, 'enrollment_date'] + timedelta(days=np.random.randint(30, 180))
        dup_row = members.loc[idx].copy()
        dup_row['enrollment_date'] = dup_date
        members = pd.concat([members, dup_row.to_frame().T], ignore_index=True)

members = members.reset_index(drop=True)
print(f"  ✓ Generated {len(members):,} member records (includes {n_dups} duplicated IDs)")
print()

# ============================================================
# PHASE 2: GENERATE PROVIDERS TABLE (420 rows)
# ============================================================
print("PHASE 2: Generating PROVIDERS table (420 rows)")

provider_ids = np.arange(1, N_PROVIDERS + 1)
provider_types = np.random.choice(['individual_md', 'group_practice', 'hospital', 'facility', 'urgent_care'],
                                  size=N_PROVIDERS,
                                  p=[0.35, 0.25, 0.15, 0.15, 0.10])

specialties = np.random.choice(['primary_care', 'cardiology', 'orthopedics', 'psychiatry', 
                                 'emergency', 'imaging', 'lab', 'pharmacy'],
                                size=N_PROVIDERS,
                                p=[0.25, 0.15, 0.12, 0.10, 0.10, 0.13, 0.10, 0.05])

network_statuses = np.random.choice(['in_network', 'out_of_network', 'preferred', 'pending_contract'],
                                    size=N_PROVIDERS,
                                    p=[0.60, 0.20, 0.15, 0.05])

regions_prov = np.random.choice(['northeast', 'midwest', 'south', 'west'],
                                size=N_PROVIDERS,
                                p=[0.22, 0.24, 0.31, 0.23])

contract_start_dates = [datetime(2018, 1, 1) + timedelta(days=int(x)) 
                        for x in np.random.uniform(0, 365*6, N_PROVIDERS)]

contract_statuses = np.random.choice(['active', 'inactive', 'terminated', 'under_review'],
                                     size=N_PROVIDERS,
                                     p=[0.75, 0.10, 0.10, 0.05])

# Providers under_review have higher denial rates (embed the pattern)
providers = pd.DataFrame({
    'provider_id': provider_ids,
    'provider_name': [f'PRV_{i:04d}' for i in provider_ids],
    'provider_type': provider_types,
    'specialty': specialties,
    'network_status': network_statuses,
    'geographic_region': regions_prov,
    'contract_start_date': contract_start_dates,
    'contract_status': contract_statuses,
    'claims_submitted_ytd': 0,  # will update after claims generated
    'last_update_date': datetime.now()
})

# Add denial rate propensity to providers (for later use in generating realistic denials)
# Out-of-network: 10-12% denial rate
# In-network: 5-7% denial rate
# Hospital: higher denial rates
# Specialists: higher denial rates
# Under review: 12-15% denial rate
providers['_denial_rate_propensity'] = 0.061  # baseline

for i, row in providers.iterrows():
    base_rate = 0.061
    
    if row['network_status'] == 'out_of_network':
        base_rate += np.random.uniform(0.04, 0.06)
    elif row['network_status'] == 'preferred':
        base_rate -= np.random.uniform(0.01, 0.02)
    
    if row['provider_type'] == 'hospital':
        base_rate += np.random.uniform(0.02, 0.04)
    elif row['provider_type'] == 'individual_md':
        base_rate -= np.random.uniform(0.01, 0.02)
    
    if row['specialty'] in ['imaging', 'cardiology']:
        base_rate += np.random.uniform(0.02, 0.04)
    elif row['specialty'] in ['primary_care', 'lab']:
        base_rate -= np.random.uniform(0.01, 0.02)
    
    if row['contract_status'] == 'under_review':
        base_rate += np.random.uniform(0.05, 0.08)
    
    providers.loc[i, '_denial_rate_propensity'] = np.clip(base_rate, 0.02, 0.20)

print(f"  ✓ Generated {len(providers)} provider records")
print(f"  ✓ Embedded denial rate propensity per provider (range: {providers['_denial_rate_propensity'].min():.1%} - {providers['_denial_rate_propensity'].max():.1%})")
print()

# ============================================================
# PHASE 3: GENERATE CLAIMS TABLE (345,000 rows)
# ============================================================
print("PHASE 3: Generating CLAIMS table (345,000 rows)")

claim_ids = np.arange(1, N_CLAIMS + 1)
claim_dates = [datetime(2025, 1, 1) + timedelta(days=int(x)) 
               for x in np.random.uniform(0, 365, N_CLAIMS)]

# Member assignment: realistic distribution
# Generate claim distribution across members (Zipfian - some members have many claims)
member_claim_counts = np.random.zipf(1.5, len(members))
member_claim_counts = member_claim_counts / member_claim_counts.sum() * N_CLAIMS
member_assignment = np.random.choice(members['member_id'].values, size=N_CLAIMS, 
                                     p=member_claim_counts / member_claim_counts.sum())

# Provider assignment: realistic distribution (some providers get more claims)
provider_claim_counts = np.random.zipf(1.8, len(providers))
provider_claim_counts = provider_claim_counts / provider_claim_counts.sum() * N_CLAIMS
provider_assignment = np.random.choice(providers['provider_id'].values, size=N_CLAIMS,
                                       p=provider_claim_counts / provider_claim_counts.sum())

claim_statuses = np.random.choice(['submitted', 'processing', 'approved', 'denied', 'appeal_pending', 'appeal_resolved'],
                                  size=N_CLAIMS,
                                  p=[0.02, 0.05, 0.87, 0.04, 0.01, 0.01])

submission_completeness = np.random.choice(['complete', 'incomplete', 'unknown'],
                                           size=N_CLAIMS,
                                           p=[0.92, 0.06, 0.02])

# Network assignment: vectorized (much faster than row-by-row loop)
# Merge to get provider network status, then assign claim network type
provider_network_map = providers[['provider_id', 'network_status']].copy()
provider_network_map.columns = ['provider_id', 'provider_network_status']

temp_claims_for_network = pd.DataFrame({
    'provider_id': provider_assignment,
    'idx': np.arange(N_CLAIMS)
})

temp_claims_for_network = temp_claims_for_network.merge(provider_network_map, on='provider_id', how='left')
temp_claims_for_network = temp_claims_for_network.sort_values('idx')

network_type = np.where(
    temp_claims_for_network['provider_network_status'].isin(['in_network', 'preferred']),
    'in_network',
    np.where(
        temp_claims_for_network['provider_network_status'] == 'out_of_network',
        'out_of_network',
        np.random.choice(['in_network', 'out_of_network', 'unknown'], size=N_CLAIMS, p=[0.70, 0.20, 0.10])
    )
)
network_type = network_type.astype(object)

claim_categories = np.random.choice(['office_visit', 'emergency', 'inpatient', 'pharmacy', 'lab', 'imaging', 'procedure'],
                                    size=N_CLAIMS,
                                    p=[0.25, 0.10, 0.08, 0.15, 0.12, 0.15, 0.15])

# Claim amounts: realistic distribution
claim_amounts = np.abs(np.random.normal(loc=2500, scale=4000, size=N_CLAIMS))
claim_amounts = np.clip(claim_amounts, 50, 50000)

# Service dates
service_start = claim_dates
service_end = [d + timedelta(days=int(np.random.uniform(0, 10))) for d in claim_dates]

# Provider IDs: 2% null (realistic data quality issue)
provider_with_nulls = provider_assignment.astype(float)  # Convert to float to allow NaN
null_indices = np.random.choice(N_CLAIMS, size=int(N_CLAIMS * 0.02), replace=False)
provider_with_nulls[null_indices] = np.nan

claims = pd.DataFrame({
    'claim_id': claim_ids,
    'member_id': member_assignment,
    'provider_id': provider_with_nulls,
    'claim_date': claim_dates,
    'service_start_date': service_start,
    'service_end_date': service_end,
    'claim_amount': claim_amounts,
    'claim_status': claim_statuses,
    'submission_completeness_flag': submission_completeness,
    'network_type': network_type,
    'claim_category': claim_categories
})

# Add prior auth requirement flag (based on claim category)
prior_auth_required = []
for cat in claims['claim_category']:
    if cat in ['inpatient', 'imaging', 'cardiology']:
        prior_auth_required.append(np.random.choice([True, False], p=[0.80, 0.20]))
    elif cat in ['office_visit', 'lab']:
        prior_auth_required.append(np.random.choice([True, False], p=[0.10, 0.90]))
    else:
        prior_auth_required.append(np.random.choice([True, False], p=[0.40, 0.60]))

claims['prior_auth_required'] = prior_auth_required

print(f"  ✓ Generated {len(claims):,} claim records")
print(f"  ✓ Embedded 2% missing provider_id (data quality issue)")
print(f"  ✓ Embedded 6% incomplete submissions")
print(f"  ✓ Claims date range: {claims['claim_date'].min().date()} to {claims['claim_date'].max().date()}")
print()

# ============================================================
# PHASE 4: GENERATE DENIALS TABLE (21,000 rows ~6%)
# ============================================================
print("PHASE 4: Generating DENIALS table (21,000 rows)")

# Identify which claims will be denied based on provider propensity and other factors (vectorized)
# First, get provider propensity for each claim
denial_probs = np.full(N_CLAIMS, 0.061)

# Merge provider propensity
temp_for_denial = pd.DataFrame({
    'provider_id': claims['provider_id'],
    'idx': np.arange(N_CLAIMS)
})

provider_deny_prop = providers[['provider_id', '_denial_rate_propensity']].copy()
temp_for_denial = temp_for_denial.merge(provider_deny_prop, on='provider_id', how='left')
temp_for_denial = temp_for_denial.sort_values('idx')

denial_probs = temp_for_denial['_denial_rate_propensity'].fillna(0.15).values.copy()

# Adjust for incomplete submission
incomplete_mask = claims['submission_completeness_flag'] == 'incomplete'
denial_probs[incomplete_mask] *= 1.5

unknown_mask = claims['submission_completeness_flag'] == 'unknown'
denial_probs[unknown_mask] *= 1.2

# Adjust for out-of-network
out_of_network_mask = claims['network_type'] == 'out_of_network'
denial_probs[out_of_network_mask] *= 1.3

# Adjust for missing auth
missing_auth = (claims['prior_auth_required']) & (np.random.random(N_CLAIMS) < 0.05)
denial_probs[missing_auth] *= 1.4

# Clip to reasonable range
denial_probs = np.clip(denial_probs, 0.01, 0.25)

# Determine which claims are denied based on their probability
denied_claim_candidates = np.where(np.random.random(N_CLAIMS) < denial_probs)[0].tolist()

# Target ~21,000 denials (6% of 345k)
target_denials = int(N_CLAIMS * DENIAL_RATE_BASELINE)
denied_indices = np.random.choice(denied_claim_candidates, size=target_denials, replace=False)

denial_ids = np.arange(1, target_denials + 1)
denial_claim_ids = claims.iloc[denied_indices]['claim_id'].values
denial_dates = [claims.iloc[idx]['claim_date'] + timedelta(days=np.random.randint(1, 14)) 
                for idx in denied_indices]

# Denial reason codes: 80% valid, 10% free text, 5% invalid codes, 5% null
denial_reason_codes = []
denial_reason_codes_list = ['PA01', 'PA02', 'PA03', 'NW01', 'NW02', 'CVRG01', 'CVRG02', 'BILL01', 'BILL02', 'MED01', 'OTHER01']

for i in range(target_denials):
    r = np.random.random()
    if r < 0.80:
        denial_reason_codes.append(np.random.choice(denial_reason_codes_list))
    elif r < 0.90:
        denial_reason_codes.append(np.random.choice(['missing auth', 'provider not in network', 'missing medical record', 'not medically necessary']))
    elif r < 0.95:
        denial_reason_codes.append(str(np.random.choice([999, 1001, 1002])))  # invalid codes
    else:
        denial_reason_codes.append(None)

# Denied amount (3% mismatch with claim amount)
denied_amounts = []
for idx in denied_indices:
    claim_amt = claims.iloc[idx]['claim_amount']
    if np.random.random() < 0.03:  # 3% mismatch
        denied_amounts.append(claim_amt * np.random.uniform(0.5, 0.95))
    else:
        denied_amounts.append(claim_amt)

# Appeal submitted and outcomes
appeal_submitted = np.random.choice([True, False], size=target_denials, p=[0.25, 0.75])
appeal_outcomes = []
for i, submitted in enumerate(appeal_submitted):
    if submitted:
        # Conditional appeal success based on reason code
        reason = denial_reason_codes[i]
        if reason in ['BILL01', 'BILL02']:
            probs = np.array([0.60, 0.25, 0.15])
        elif reason in ['MED01']:
            probs = np.array([0.15, 0.65, 0.20])
        else:
            probs = np.array([0.35, 0.45, 0.20])
        probs = probs / probs.sum()  # Normalize to ensure sum = 1
        appeal_outcomes.append(np.random.choice(['approved', 'denied', 'partial_approval'], p=probs))
    else:
        appeal_outcomes.append(None)

# Resolution amount (if appealed and approved)
resolution_amounts = []
for i, outcome in enumerate(appeal_outcomes):
    if outcome == 'approved':
        resolution_amounts.append(denied_amounts[i])
    elif outcome == 'partial_approval':
        resolution_amounts.append(denied_amounts[i] * np.random.uniform(0.40, 0.80))
    else:
        resolution_amounts.append(None)

denials = pd.DataFrame({
    'denial_id': denial_ids,
    'claim_id': denial_claim_ids,
    'denial_date': denial_dates,
    'denial_reason_code': denial_reason_codes,
    'denial_reason_category_manual': [None] * target_denials,  # sparse, will be populated by analyst
    'denied_claim_amount': denied_amounts,
    'appeal_submitted': appeal_submitted,
    'appeal_outcome': appeal_outcomes,
    'resolution_amount': resolution_amounts
})

print(f"  ✓ Generated {len(denials):,} denial records ({len(denials)/N_CLAIMS*100:.2f}% denial rate)")
print(f"  ✓ Embedded denial reason codes: 80% valid, 10% free text, 5% invalid, 5% null")
print(f"  ✓ Embedded 3% denied_amount mismatches")
print(f"  ✓ Appeal success rate: 60% for billing errors, 15% for medical necessity")
print()

# ============================================================
# PHASE 5: GENERATE PRIOR AUTH TABLE (18,000 rows)
# ============================================================
print("PHASE 5: Generating PRIOR AUTH table (18,000 rows)")

# Only generate prior auth for claims that require it
prior_auth_req = claims[claims['prior_auth_required'] == True].copy()

# 75% match to actual claims, 25% orphaned (auth requested but claim never submitted, or submitted without auth)
n_auth_claims = int(len(prior_auth_req) * 0.75)
auth_claim_ids = np.random.choice(prior_auth_req['claim_id'].values, size=n_auth_claims, replace=False)

# Add orphaned auth records (25%)
orphaned_auth_count = int(len(prior_auth_req) * 0.25 / 0.75)  # scale up orphaned to ~25% of total prior auths
orphaned_claim_ids = np.random.choice(claims[~claims['claim_id'].isin(auth_claim_ids)]['claim_id'].values, 
                                      size=orphaned_auth_count, replace=False)

all_auth_claim_ids = np.concatenate([auth_claim_ids, orphaned_claim_ids])

prior_auth_ids = np.arange(1, len(all_auth_claim_ids) + 1)

prior_auth_requested_dates = []
for claim_id in all_auth_claim_ids:
    claim = claims[claims['claim_id'] == claim_id]
    if len(claim) > 0:
        claim_date = claim['claim_date'].values[0]
        req_date = claim_date - timedelta(days=np.random.randint(1, 14))
        prior_auth_requested_dates.append(req_date)
    else:
        prior_auth_requested_dates.append(datetime(2024, 12, 1) + timedelta(days=np.random.randint(1, 365)))

# Status: 70% approved, 15% pending, 10% denied, 5% expired
statuses = np.random.choice(['approved', 'pending', 'denied', 'expired'],
                            size=len(all_auth_claim_ids),
                            p=[0.70, 0.15, 0.10, 0.05])

# Approved dates and processing time
approved_dates = []
processing_days = []

for i, (status, req_date) in enumerate(zip(statuses, prior_auth_requested_dates)):
    if status == 'approved':
        # Processing time varies: baseline 3-7 days, some take 14+ days (delays)
        days = int(np.random.normal(loc=5, scale=3))
        days = int(np.clip(days, 1, 30))
        if np.random.random() < 0.10:  # 10% have significant delays (>7 days)
            days = int(np.random.randint(8, 21))
        approved_dates.append(req_date + timedelta(days=int(days)))
        processing_days.append(int(days))
    else:
        approved_dates.append(None)
        processing_days.append(None)

# Member and provider for auth records
auth_member_ids = []
auth_provider_ids = []

for claim_id in all_auth_claim_ids:
    claim = claims[claims['claim_id'] == claim_id]
    if len(claim) > 0:
        auth_member_ids.append(claim['member_id'].values[0])
        auth_provider_ids.append(claim['provider_id'].values[0])
    else:
        # Orphaned auth: random member and provider
        auth_member_ids.append(np.random.choice(members['member_id'].values))
        auth_provider_ids.append(np.random.choice(providers['provider_id'].values))

prior_auth = pd.DataFrame({
    'prior_auth_id': prior_auth_ids,
    'claim_id': all_auth_claim_ids,
    'member_id': auth_member_ids,
    'provider_id': auth_provider_ids,
    'requested_date': prior_auth_requested_dates,
    'approved_date': approved_dates,
    'status': statuses,
    'processing_days': processing_days
})

n_orphaned = len(orphaned_claim_ids)
print(f"  ✓ Generated {len(prior_auth):,} prior auth records")
print(f"  ✓ Orphaned auth records: {n_orphaned:,} ({n_orphaned/len(prior_auth)*100:.1f}% - auth without matching claim)")
print(f"  ✓ Embedded variable processing times (1-30 days, mean ~5 days)")
print()

# ============================================================
# PHASE 6: GENERATE CLAIMS DETAIL SERVICES TABLE (410,000+ rows)
# ============================================================
print("PHASE 6: Generating CLAIMS DETAIL SERVICES table (410,000+ rows)")

claim_details = []
claim_detail_id_counter = 1

for idx, claim in claims.iterrows():
    # Each claim has 1-3 line items
    n_services = np.random.choice([1, 2, 3], p=[0.70, 0.25, 0.05])
    
    for svc in range(n_services):
        procedure_code = np.random.choice(['99213', '99214', '99215', '70450', '80053', '92004', '93000', '99999'],
                                         p=[0.25, 0.20, 0.10, 0.10, 0.12, 0.08, 0.10, 0.05])
        
        # 1% of codes are outdated (won't be in real system)
        if np.random.random() < 0.01:
            procedure_code = np.random.choice(['88888', '99999', '00001'])
        
        quantity = int(np.random.uniform(1, 5))
        amount_per_service = np.abs(np.random.normal(loc=800, scale=400))
        amount_per_service = np.clip(amount_per_service, 50, 5000)
        
        total_line = quantity * amount_per_service
        
        claim_details.append({
            'claim_detail_id': claim_detail_id_counter,
            'claim_id': claim['claim_id'],
            'procedure_code': procedure_code,
            'quantity_services': quantity,
            'amount_per_service': amount_per_service,
            'total_line_amount': total_line
        })
        claim_detail_id_counter += 1

claims_detail = pd.DataFrame(claim_details)

print(f"  ✓ Generated {len(claims_detail):,} claim detail line items")
print(f"  ✓ Average {len(claims_detail)/len(claims):.2f} line items per claim")
print(f"  ✓ Embedded 1% outdated procedure codes")
print()

# ============================================================
# PHASE 7: UPDATE COUNTS AND SAVE FILES
# ============================================================
print("PHASE 7: Updating member/provider counts and saving files")

# Update member counts
member_claim_counts = claims.groupby('member_id').size().reset_index(name='count')
members_updated = members.merge(member_claim_counts, left_on='member_id', right_on='member_id', how='left')
members_updated['claims_count_ytd'] = members_updated['count'].fillna(0).astype(int)
members_updated = members_updated.drop('count', axis=1)

member_denial_counts = denials.merge(claims[['claim_id', 'member_id']], on='claim_id', how='left')
member_denial_counts = member_denial_counts.groupby('member_id').size().reset_index(name='count')
members_updated = members_updated.merge(member_denial_counts, left_on='member_id', right_on='member_id', how='left')
members_updated['denied_claims_count_ytd'] = members_updated['count'].fillna(0).astype(int)
members_updated = members_updated.drop('count', axis=1)

# Update provider counts
provider_claim_counts = claims[claims['provider_id'].notna()].groupby('provider_id').size().reset_index(name='count')
providers_updated = providers.merge(provider_claim_counts, left_on='provider_id', right_on='provider_id', how='left')
providers_updated['claims_submitted_ytd'] = providers_updated['count'].fillna(0).astype(int)
providers_updated = providers_updated.drop('count', axis=1)
providers_updated = providers_updated.drop('_denial_rate_propensity', axis=1)

# Save all files
import os
os.makedirs('../data', exist_ok=True)

members_updated.to_csv('../data/clarity_members.csv', index=False)
providers_updated.to_csv('../data/clarity_providers.csv', index=False)
claims.to_csv('../data/clarity_claims.csv', index=False)
denials.to_csv('../data/clarity_denials.csv', index=False)
prior_auth.to_csv('../data/clarity_prior_auth.csv', index=False)
claims_detail.to_csv('../data/clarity_claims_detail.csv', index=False)

print(f"  ✓ clarity_members.csv ({len(members_updated):,} rows)")
print(f"  ✓ clarity_providers.csv ({len(providers_updated)} rows)")
print(f"  ✓ clarity_claims.csv ({len(claims):,} rows)")
print(f"  ✓ clarity_denials.csv ({len(denials):,} rows)")
print(f"  ✓ clarity_prior_auth.csv ({len(prior_auth):,} rows)")
print(f"  ✓ clarity_claims_detail.csv ({len(claims_detail):,} rows)")
print()

# ============================================================
# PHASE 8: SAVE METADATA
# ============================================================
print("PHASE 8: Saving metadata")

metadata = {
    "version": VERSION,
    "generated_date": datetime.now().isoformat(),
    "seed": SEED,
    "dataset_summary": {
        "total_claims": int(len(claims)),
        "total_denials": int(len(denials)),
        "denial_rate": float(len(denials) / len(claims)),
        "total_members": int(len(members_updated)),
        "total_providers": int(len(providers_updated)),
        "total_claim_details": int(len(claims_detail)),
        "total_prior_auths": int(len(prior_auth))
    },
    "total_denied_dollars": float(denials['denied_claim_amount'].sum()),
    "average_denied_claim": float(denials['denied_claim_amount'].mean()),
    "appeal_submitted_count": int(denials['appeal_submitted'].sum()),
    "appeal_success_rate": float(denials[denials['appeal_submitted']]['appeal_outcome'].isin(['approved', 'partial_approval']).sum() / denials['appeal_submitted'].sum()) if denials['appeal_submitted'].sum() > 0 else 0,
    "data_quality_issues": {
        "missing_provider_id_percent": float((claims['provider_id'].isna().sum() / len(claims)) * 100),
        "incomplete_submission_percent": float((claims['submission_completeness_flag'] == 'incomplete').sum() / len(claims) * 100),
        "orphaned_prior_auth_percent": float((len(orphaned_claim_ids) / len(prior_auth)) * 100),
        "denial_reason_free_text_percent": float((denials['denial_reason_code'].isin(['missing auth', 'provider not in network', 'missing medical record', 'not medically necessary']).sum() / len(denials)) * 100),
        "denial_reason_invalid_percent": float((denials['denial_reason_code'].isin(['999', '1001', '1002']).sum() / len(denials)) * 100),
        "denial_reason_null_percent": float((denials['denial_reason_code'].isna().sum() / len(denials)) * 100),
        "denied_amount_mismatch_percent": 3.0,
        "member_id_duplicate_percent": float((len(members) - len(members_updated)) / len(members_updated) * 100),
        "chronic_condition_null_percent": float((members_updated['chronic_condition_flags'].isna().sum() / len(members_updated)) * 100)
    },
    "date_range": {
        "claim_start": claims['claim_date'].min().isoformat(),
        "claim_end": claims['claim_date'].max().isoformat()
    }
}

with open('../data/clarity_metadata.json', 'w') as f:
    json.dump(metadata, f, indent=2)

print(f"  ✓ clarity_metadata.json")
print()

# ============================================================
# SUMMARY
# ============================================================
print("="*70)
print("DATASET GENERATION COMPLETE")
print("="*70)
print()
print(f"Total Claims: {len(claims):,}")
print(f"Total Denials: {len(denials):,} ({len(denials)/len(claims)*100:.2f}%)")
print(f"Total Denied $: ${denials['denied_claim_amount'].sum():,.0f}")
print(f"Average Denied Claim: ${denials['denied_claim_amount'].mean():,.0f}")
print()
print(f"Members: {len(members_updated):,} (including {len(members) - len(members_updated)} duplicates)")
print(f"Providers: {len(providers_updated)}")
print(f"Claim Details: {len(claims_detail):,}")
print(f"Prior Auth Records: {len(prior_auth):,} ({n_orphaned:,} orphaned)")
print()
print("Data Quality Issues (Intentional):")
print(f"  - Missing provider_id: 2.0%")
print(f"  - Incomplete submissions: 6.0%")
print(f"  - Orphaned prior auth: 25%")
print(f"  - Denial reason free text: ~10%")
print(f"  - Denial reason invalid codes: ~5%")
print(f"  - Denial reason null: ~5%")
print(f"  - Denied amount mismatch: 3%")
print(f"  - Member ID duplicates: {(len(members) - len(members_updated)) / len(members_updated) * 100:.1f}%")
print(f"  - Chronic condition flags null: 40%")
print()
print("All files saved to: ../data/")
print("="*70)
