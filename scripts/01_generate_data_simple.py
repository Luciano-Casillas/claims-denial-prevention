"""
Clarity Health Plans - Fast Dataset Generator (Simplified)
Generates 200k claims with realistic denial patterns - optimized for speed
"""

import pandas as pd
import numpy as np
import json
from datetime import datetime, timedelta

N_CLAIMS = 200_000
N_MEMBERS = 100_000
N_PROVIDERS = 350
DENIAL_RATE = 0.061
SEED = 42

np.random.seed(SEED)

print("="*70)
print("CLARITY HEALTH PLANS - SIMPLIFIED DATASET GENERATOR")
print("="*70)
print(f"Generating {N_CLAIMS:,} claims...")
print()

# ============================================================
# MEMBERS
# ============================================================
print("Generating members...")
members = pd.DataFrame({
    'member_id': np.arange(1, N_MEMBERS + 1),
    'member_name': [f'MBR_{i:06d}' for i in range(1, N_MEMBERS + 1)],
    'age_group': np.random.choice(['<18', '18-30', '31-45', '46-65', '65+'], N_MEMBERS, p=[0.08, 0.18, 0.22, 0.28, 0.24]),
    'gender': np.random.choice(['M', 'F', 'unknown'], N_MEMBERS, p=[0.48, 0.48, 0.04]),
    'plan_type': np.random.choice(['bronze', 'silver', 'gold', 'platinum', 'medicaid'], N_MEMBERS, p=[0.15, 0.25, 0.30, 0.20, 0.10]),
    'geographic_region': np.random.choice(['northeast', 'midwest', 'south', 'west'], N_MEMBERS, p=[0.22, 0.24, 0.31, 0.23]),
    'income_bracket': np.random.choice(['low', 'medium', 'high', 'unknown'], N_MEMBERS, p=[0.20, 0.35, 0.30, 0.15]),
    'chronic_condition_flags': np.random.choice([None, 'diabetes', 'heart_disease', 'mental_health', 'respiratory', 'none'], N_MEMBERS, p=[0.40, 0.15, 0.10, 0.10, 0.08, 0.17]),
    'enrollment_date': [datetime(2019, 1, 1) + timedelta(days=int(x)) for x in np.random.uniform(0, 365*5, N_MEMBERS)],
})

print(f"  ✓ {len(members):,} members")

# ============================================================
# PROVIDERS
# ============================================================
print("Generating providers...")
providers = pd.DataFrame({
    'provider_id': np.arange(1, N_PROVIDERS + 1),
    'provider_name': [f'PRV_{i:04d}' for i in range(1, N_PROVIDERS + 1)],
    'provider_type': np.random.choice(['individual_md', 'group_practice', 'hospital', 'facility', 'urgent_care'], N_PROVIDERS, p=[0.35, 0.25, 0.15, 0.15, 0.10]),
    'specialty': np.random.choice(['primary_care', 'cardiology', 'orthopedics', 'psychiatry', 'emergency', 'imaging', 'lab', 'pharmacy'], N_PROVIDERS, p=[0.25, 0.15, 0.12, 0.10, 0.10, 0.13, 0.10, 0.05]),
    'network_status': np.random.choice(['in_network', 'out_of_network', 'preferred', 'pending_contract'], N_PROVIDERS, p=[0.60, 0.20, 0.15, 0.05]),
    'geographic_region': np.random.choice(['northeast', 'midwest', 'south', 'west'], N_PROVIDERS, p=[0.22, 0.24, 0.31, 0.23]),
    'contract_start_date': [datetime(2018, 1, 1) + timedelta(days=int(x)) for x in np.random.uniform(0, 365*6, N_PROVIDERS)],
    'contract_status': np.random.choice(['active', 'inactive', 'terminated', 'under_review'], N_PROVIDERS, p=[0.75, 0.10, 0.10, 0.05]),
})

# Embed denial rate propensity
denial_propensity = np.full(N_PROVIDERS, 0.061)
denial_propensity[providers['network_status'] == 'out_of_network'] += np.random.uniform(0.04, 0.06, (providers['network_status'] == 'out_of_network').sum())
denial_propensity[providers['network_status'] == 'preferred'] -= np.random.uniform(0.01, 0.02, (providers['network_status'] == 'preferred').sum())
denial_propensity[providers['provider_type'] == 'hospital'] += np.random.uniform(0.02, 0.04, (providers['provider_type'] == 'hospital').sum())
denial_propensity[providers['contract_status'] == 'under_review'] += np.random.uniform(0.05, 0.08, (providers['contract_status'] == 'under_review').sum())
providers['_denial_propensity'] = np.clip(denial_propensity, 0.02, 0.20)
providers['claims_submitted_ytd'] = 0
providers['last_update_date'] = datetime.now()

print(f"  ✓ {len(providers)} providers")

# ============================================================
# CLAIMS
# ============================================================
print("Generating claims...")
claims = pd.DataFrame({
    'claim_id': np.arange(1, N_CLAIMS + 1),
    'member_id': np.random.choice(members['member_id'].values, N_CLAIMS),
    'provider_id': np.random.choice(providers['provider_id'].values, N_CLAIMS),
    'claim_date': [datetime(2025, 1, 1) + timedelta(days=int(x)) for x in np.random.uniform(0, 365, N_CLAIMS)],
    'claim_amount': np.clip(np.abs(np.random.normal(2500, 4000, N_CLAIMS)), 50, 50000),
    'claim_status': np.random.choice(['submitted', 'processing', 'approved', 'denied', 'appeal_pending'], N_CLAIMS, p=[0.02, 0.05, 0.87, 0.04, 0.02]),
    'submission_completeness_flag': np.random.choice(['complete', 'incomplete', 'unknown'], N_CLAIMS, p=[0.92, 0.06, 0.02]),
    'claim_category': np.random.choice(['office_visit', 'emergency', 'inpatient', 'pharmacy', 'lab', 'imaging', 'procedure'], N_CLAIMS, p=[0.25, 0.10, 0.08, 0.15, 0.12, 0.15, 0.15]),
})

# Add network type based on provider
prov_network = providers[['provider_id', 'network_status']].copy()
claims = claims.merge(prov_network, on='provider_id', how='left')
claims['network_type'] = np.where(claims['network_status'].isin(['in_network', 'preferred']), 'in_network', 'out_of_network')
claims = claims.drop('network_status', axis=1)

# Add service dates
claims['service_start_date'] = claims['claim_date']
claims['service_end_date'] = claims['claim_date'] + pd.to_timedelta(np.random.randint(0, 10, N_CLAIMS), unit='D')

# Add prior auth requirement
claims['prior_auth_required'] = np.random.choice([True, False], N_CLAIMS, p=[0.40, 0.60])

# Add 2% missing provider_id
missing_indices = np.random.choice(N_CLAIMS, int(N_CLAIMS * 0.02), replace=False)
claims.loc[missing_indices, 'provider_id'] = np.nan

print(f"  ✓ {len(claims):,} claims ({len(claims[claims['claim_status'] == 'denied']):,} denied)")

# ============================================================
# DENIALS
# ============================================================
print("Generating denials...")
# Get claims marked as denied
denied_claims = claims[claims['claim_status'] == 'denied'].copy()

# Merge with provider propensity
denied_claims = denied_claims.merge(providers[['provider_id', '_denial_propensity']], on='provider_id', how='left')

denials = pd.DataFrame({
    'denial_id': np.arange(1, len(denied_claims) + 1),
    'claim_id': denied_claims['claim_id'].values,
    'denial_date': denied_claims['claim_date'].values + pd.to_timedelta(np.random.randint(1, 14, len(denied_claims)), unit='D'),
    'denial_reason_code': np.random.choice(['PA01', 'PA02', 'NW01', 'CVRG01', 'BILL01', 'MED01', 'missing auth', 'provider not network', '999', None], len(denied_claims), p=[0.20, 0.15, 0.12, 0.15, 0.12, 0.10, 0.08, 0.05, 0.02, 0.01]),
    'denied_claim_amount': np.where(np.random.random(len(denied_claims)) < 0.03, denied_claims['claim_amount'].values * np.random.uniform(0.5, 0.95, len(denied_claims)), denied_claims['claim_amount'].values),
})

denials['denial_reason_category_manual'] = None
denials['appeal_submitted'] = np.random.choice([True, False], len(denials), p=[0.25, 0.75])
denials['appeal_outcome'] = np.where(denials['appeal_submitted'], np.random.choice(['approved', 'denied', 'partial_approval'], len(denials), p=[0.35, 0.45, 0.20]), None)
denials['resolution_amount'] = np.where(denials['appeal_outcome'] == 'approved', denials['denied_claim_amount'], np.where(denials['appeal_outcome'] == 'partial_approval', denials['denied_claim_amount'] * np.random.uniform(0.40, 0.80, len(denials)), None))

print(f"  ✓ {len(denials):,} denial records ({len(denials)/len(claims)*100:.2f}% denial rate)")

# ============================================================
# PRIOR AUTH
# ============================================================
print("Generating prior auth records...")
auth_req_claims = claims[claims['prior_auth_required']].copy()
n_auth = int(len(auth_req_claims) * 0.75)  # 75% match
auth_claim_ids = np.random.choice(auth_req_claims['claim_id'].values, n_auth, replace=False)

# Add some orphaned records
orphaned_count = int(len(auth_req_claims) * 0.25)
orphaned_ids = np.random.choice(claims[~claims['claim_id'].isin(auth_claim_ids)]['claim_id'].values, orphaned_count, replace=False)
all_auth_ids = np.concatenate([auth_claim_ids, orphaned_ids])

prior_auth = pd.DataFrame({
    'prior_auth_id': np.arange(1, len(all_auth_ids) + 1),
    'claim_id': all_auth_ids,
    'member_id': np.random.choice(members['member_id'].values, len(all_auth_ids)),
    'provider_id': np.random.choice(providers['provider_id'].values, len(all_auth_ids)),
    'requested_date': [datetime(2025, 1, 1) + timedelta(days=int(x)) for x in np.random.uniform(0, 365, len(all_auth_ids))],
    'status': np.random.choice(['approved', 'pending', 'denied', 'expired'], len(all_auth_ids), p=[0.70, 0.15, 0.10, 0.05]),
})

# Processing days only for approved
processing_days = np.random.normal(5, 3, len(prior_auth))
processing_days = np.clip(processing_days, 1, 30)
processing_days = np.where(prior_auth['status'] == 'approved', processing_days, np.nan)

prior_auth['approved_date'] = np.where(prior_auth['status'] == 'approved',
                                       prior_auth['requested_date'] + pd.to_timedelta(processing_days, unit='D'),
                                       None)
prior_auth['processing_days'] = processing_days

print(f"  ✓ {len(prior_auth):,} prior auth records")

# ============================================================
# CLAIMS DETAIL
# ============================================================
print("Generating claim detail line items...")
detail_rows = []
for idx, claim in claims.iterrows():
    n_services = np.random.choice([1, 2, 3], p=[0.70, 0.25, 0.05])
    for svc in range(n_services):
        detail_rows.append({
            'claim_detail_id': len(detail_rows) + 1,
            'claim_id': claim['claim_id'],
            'procedure_code': np.random.choice(['99213', '70450', '80053', '92004', '93000'], p=[0.40, 0.20, 0.20, 0.10, 0.10]),
            'quantity_services': int(np.random.uniform(1, 5)),
            'amount_per_service': np.clip(np.random.normal(800, 400), 50, 5000),
        })

claims_detail = pd.DataFrame(detail_rows)
claims_detail['total_line_amount'] = claims_detail['quantity_services'] * claims_detail['amount_per_service']

print(f"  ✓ {len(claims_detail):,} line items")

# ============================================================
# UPDATE COUNTS
# ============================================================
print("Updating member and provider counts...")
members['claims_count_ytd'] = members['member_id'].map(claims.groupby('member_id').size()).fillna(0).astype(int)
members['denied_claims_count_ytd'] = members['member_id'].map(denials.merge(claims[['claim_id', 'member_id']], on='claim_id', how='left').groupby('member_id').size()).fillna(0).astype(int)

providers['claims_submitted_ytd'] = providers['provider_id'].map(claims[claims['provider_id'].notna()].groupby('provider_id').size()).fillna(0).astype(int)
providers = providers.drop('_denial_propensity', axis=1)

# ============================================================
# SAVE FILES
# ============================================================
print("Saving files...")
import os
os.makedirs('../data', exist_ok=True)

members.to_csv('../data/clarity_members.csv', index=False)
providers.to_csv('../data/clarity_providers.csv', index=False)
claims.to_csv('../data/clarity_claims.csv', index=False)
denials.to_csv('../data/clarity_denials.csv', index=False)
prior_auth.to_csv('../data/clarity_prior_auth.csv', index=False)
claims_detail.to_csv('../data/clarity_claims_detail.csv', index=False)

# ============================================================
# METADATA
# ============================================================
metadata = {
    "version": "1.0",
    "generated_date": datetime.now().isoformat(),
    "seed": SEED,
    "dataset_summary": {
        "total_claims": int(len(claims)),
        "total_denials": int(len(denials)),
        "denial_rate": float(len(denials) / len(claims)),
        "total_denied_dollars": float(denials['denied_claim_amount'].sum()),
        "average_denied_claim": float(denials['denied_claim_amount'].mean()),
        "total_members": int(len(members)),
        "total_providers": int(len(providers)),
        "total_claim_details": int(len(claims_detail)),
        "total_prior_auths": int(len(prior_auth))
    }
}

with open('../data/clarity_metadata.json', 'w') as f:
    json.dump(metadata, f, indent=2)

print(f"  ✓ clarity_members.csv")
print(f"  ✓ clarity_providers.csv")
print(f"  ✓ clarity_claims.csv")
print(f"  ✓ clarity_denials.csv")
print(f"  ✓ clarity_prior_auth.csv")
print(f"  ✓ clarity_claims_detail.csv")
print(f"  ✓ clarity_metadata.json")
print()

# ============================================================
# SUMMARY
# ============================================================
print("="*70)
print("GENERATION COMPLETE")
print("="*70)
print(f"Total Claims: {len(claims):,}")
print(f"Total Denials: {len(denials):,} ({len(denials)/len(claims)*100:.2f}%)")
print(f"Total Denied $: ${denials['denied_claim_amount'].sum():,.0f}")
print(f"Average Denied Claim: ${denials['denied_claim_amount'].mean():,.0f}")
print(f"Appeal Rate: {(denials['appeal_submitted'].sum()/len(denials)*100):.1f}%")
print(f"Appeal Success Rate: {(denials[denials['appeal_submitted']]['appeal_outcome'].isin(['approved', 'partial_approval']).sum() / denials['appeal_submitted'].sum() * 100):.1f}%")
print()
print(f"Members: {len(members):,}")
print(f"Providers: {len(providers)}")
print()
print("="*70)
