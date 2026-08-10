"""
Clarity Health Plans - Data Analysis & SQL Query Execution
Runs SQL queries against generated CSV files and produces findings report
"""

import pandas as pd
import sqlite3
from datetime import datetime

# Load all CSV files into memory
print("Loading CSV files...")
members = pd.read_csv('../data/clarity_members.csv')
providers = pd.read_csv('../data/clarity_providers.csv')
claims = pd.read_csv('../data/clarity_claims.csv')
denials = pd.read_csv('../data/clarity_denials.csv')
prior_auth = pd.read_csv('../data/clarity_prior_auth.csv')
claims_detail = pd.read_csv('../data/clarity_claims_detail.csv')

print(f"Loaded {len(members):,} members")
print(f"Loaded {len(providers)} providers")
print(f"Loaded {len(claims):,} claims")
print(f"Loaded {len(denials):,} denials")
print(f"Loaded {len(prior_auth):,} prior auth records")
print(f"Loaded {len(claims_detail):,} claim details")
print()

# Create SQLite in-memory database
print("Creating SQLite database...")
conn = sqlite3.connect(':memory:')

members.to_sql('clarity_members', conn, index=False, if_exists='replace')
providers.to_sql('clarity_providers', conn, index=False, if_exists='replace')
claims.to_sql('clarity_claims', conn, index=False, if_exists='replace')
denials.to_sql('clarity_denials', conn, index=False, if_exists='replace')
prior_auth.to_sql('clarity_prior_auth', conn, index=False, if_exists='replace')
claims_detail.to_sql('clarity_claims_detail', conn, index=False, if_exists='replace')

cursor = conn.cursor()

# ============================================================
# EXECUTE KEY QUERIES AND CAPTURE FINDINGS
# ============================================================

findings = {}

print("="*70)
print("CLARITY HEALTH PLANS - DATA ANALYSIS FINDINGS")
print("="*70)
print()

# QUERY 1: Baseline metrics
print("QUERY 1: BASELINE DENIAL METRICS")
print("-" * 70)
query1 = """
SELECT
    COUNT(*) as total_claims,
    SUM(CASE WHEN claim_status = 'denied' THEN 1 ELSE 0 END) as denied_count,
    ROUND(100.0 * SUM(CASE WHEN claim_status = 'denied' THEN 1 ELSE 0 END) / COUNT(*), 2) as denial_rate_pct,
    ROUND(SUM(claim_amount) / 1000000, 2) as total_submitted_millions,
    ROUND(SUM(CASE WHEN claim_status = 'denied' THEN claim_amount ELSE 0 END) / 1000000, 2) as total_denied_millions,
    ROUND(AVG(CASE WHEN claim_status = 'denied' THEN claim_amount ELSE NULL END), 0) as avg_denied_claim_amount
FROM clarity_claims
"""
df1 = pd.read_sql_query(query1, conn)
print(df1.to_string(index=False))
print()
findings['baseline'] = df1.to_dict('records')[0]

# QUERY 2: Top 10 providers by denied amount
print("QUERY 2: TOP 10 PROVIDERS BY DENIED CLAIMS $")
print("-" * 70)
query2 = """
SELECT
    p.provider_id,
    p.provider_name,
    p.specialty,
    p.network_status,
    COUNT(d.denial_id) as denial_count,
    ROUND(100.0 * COUNT(d.denial_id) / COUNT(c.claim_id), 2) as denial_rate_pct,
    ROUND(SUM(CASE WHEN c.claim_status = 'denied' THEN c.claim_amount ELSE 0 END) / 1000000, 2) as denied_millions
FROM clarity_claims c
LEFT JOIN clarity_providers p ON c.provider_id = p.provider_id
LEFT JOIN clarity_denials d ON c.claim_id = d.claim_id AND c.claim_status = 'denied'
WHERE c.provider_id IS NOT NULL
GROUP BY p.provider_id, p.provider_name, p.specialty, p.network_status
ORDER BY denied_millions DESC
LIMIT 10
"""
df2 = pd.read_sql_query(query2, conn)
print(df2.to_string(index=False))
print()
findings['top_10_providers'] = df2.to_dict('records')

# QUERY 3: Denial rate by specialty
print("QUERY 3: DENIAL RATE BY PROVIDER SPECIALTY")
print("-" * 70)
query3 = """
SELECT
    p.specialty,
    COUNT(c.claim_id) as total_claims,
    SUM(CASE WHEN c.claim_status = 'denied' THEN 1 ELSE 0 END) as denial_count,
    ROUND(100.0 * SUM(CASE WHEN c.claim_status = 'denied' THEN 1 ELSE 0 END) / COUNT(c.claim_id), 2) as denial_rate_pct,
    ROUND(SUM(CASE WHEN c.claim_status = 'denied' THEN c.claim_amount ELSE 0 END) / 1000000, 2) as denied_millions
FROM clarity_claims c
LEFT JOIN clarity_providers p ON c.provider_id = p.provider_id
WHERE c.provider_id IS NOT NULL
GROUP BY p.specialty
ORDER BY denial_rate_pct DESC
"""
df3 = pd.read_sql_query(query3, conn)
print(df3.to_string(index=False))
print()
findings['denial_by_specialty'] = df3.to_dict('records')

# QUERY 4: Root cause analysis
print("QUERY 4: DENIAL ROOT CAUSE BREAKDOWN")
print("-" * 70)
query4 = """
SELECT
    CASE
        WHEN denial_reason_code IN ('PA01', 'PA02', 'PA03') THEN 'prior_auth_delay'
        WHEN denial_reason_code IN ('CVRG01', 'CVRG02') THEN 'coverage_limit'
        WHEN denial_reason_code IN ('NW01', 'NW02', 'provider not network') THEN 'network_issue'
        WHEN denial_reason_code IN ('BILL01', 'BILL02') THEN 'billing_error'
        WHEN denial_reason_code IN ('MED01') THEN 'medical_necessity'
        WHEN denial_reason_code IN ('missing auth') THEN 'missing_auth_free_text'
        WHEN denial_reason_code IN ('999') THEN 'invalid_code'
        WHEN denial_reason_code IS NULL THEN 'null'
        ELSE 'other'
    END as standardized_reason,
    COUNT(*) as denial_count,
    ROUND(SUM(denied_claim_amount) / 1000000, 2) as denied_millions,
    ROUND(100.0 * SUM(denied_claim_amount) / (SELECT SUM(denied_claim_amount) FROM clarity_denials), 2) as pct_of_denied_dollars
FROM clarity_denials
GROUP BY standardized_reason
ORDER BY denied_millions DESC
"""
df4 = pd.read_sql_query(query4, conn)
print(df4.to_string(index=False))
print()
findings['denial_root_causes'] = df4.to_dict('records')

# QUERY 5: Appeal success rate by reason
print("QUERY 5: APPEAL SUCCESS RATE BY DENIAL REASON")
print("-" * 70)
query5 = """
SELECT
    CASE
        WHEN denial_reason_code IN ('PA01', 'PA02', 'PA03') THEN 'prior_auth_delay'
        WHEN denial_reason_code IN ('CVRG01', 'CVRG02') THEN 'coverage_limit'
        WHEN denial_reason_code IN ('NW01', 'NW02', 'provider not network') THEN 'network_issue'
        WHEN denial_reason_code IN ('BILL01', 'BILL02') THEN 'billing_error'
        WHEN denial_reason_code IN ('MED01') THEN 'medical_necessity'
        ELSE 'other'
    END as denial_category,
    SUM(CASE WHEN appeal_submitted = 1 THEN 1 ELSE 0 END) as appeals_submitted,
    SUM(CASE WHEN appeal_outcome IN ('approved', 'partial_approval') THEN 1 ELSE 0 END) as appeals_won,
    ROUND(100.0 * SUM(CASE WHEN appeal_outcome IN ('approved', 'partial_approval') THEN 1 ELSE 0 END) / 
          NULLIF(SUM(CASE WHEN appeal_submitted = 1 THEN 1 ELSE 0 END), 0), 1) as appeal_success_rate_pct
FROM clarity_denials
GROUP BY denial_category
ORDER BY appeal_success_rate_pct DESC
"""
df5 = pd.read_sql_query(query5, conn)
print(df5.to_string(index=False))
print()
findings['appeal_success'] = df5.to_dict('records')

# QUERY 6: Repeat denial member segments
print("QUERY 6: REPEAT-DENIAL MEMBER SEGMENT (3+ DENIALS)")
print("-" * 70)
query6 = """
SELECT
    COUNT(DISTINCT m.member_id) as member_count,
    ROUND(100.0 * COUNT(DISTINCT m.member_id) / (SELECT COUNT(DISTINCT member_id) FROM clarity_members), 2) as pct_of_total_members,
    ROUND(SUM(CASE WHEN d.denial_id IS NOT NULL THEN d.denied_claim_amount ELSE 0 END) / 1000000, 2) as total_denied_millions
FROM clarity_members m
LEFT JOIN clarity_claims c ON m.member_id = c.member_id
LEFT JOIN clarity_denials d ON c.claim_id = d.claim_id
GROUP BY m.member_id
HAVING COUNT(DISTINCT d.denial_id) >= 3
LIMIT 1
"""
try:
    df6_count = pd.read_sql_query("SELECT COUNT(*) as repeat_denial_members FROM (SELECT m.member_id FROM clarity_members m LEFT JOIN clarity_claims c ON m.member_id = c.member_id LEFT JOIN clarity_denials d ON c.claim_id = d.claim_id GROUP BY m.member_id HAVING COUNT(DISTINCT d.denial_id) >= 3)", conn)
    print(f"Repeat-denial members (3+ denials): {df6_count.iloc[0, 0]}")
    
    df6 = pd.read_sql_query("""
    SELECT
        m.income_bracket,
        m.chronic_condition_flags,
        COUNT(DISTINCT m.member_id) as member_count
    FROM clarity_members m
    LEFT JOIN clarity_claims c ON m.member_id = c.member_id
    LEFT JOIN clarity_denials d ON c.claim_id = d.claim_id
    GROUP BY m.member_id, m.income_bracket, m.chronic_condition_flags
    HAVING COUNT(DISTINCT d.denial_id) >= 3
    """, conn)
    
    if len(df6) > 0:
        segment_summary = df6.groupby(['income_bracket', 'chronic_condition_flags']).size().reset_index(name='count').sort_values('count', ascending=False)
        print(segment_summary.to_string(index=False))
    else:
        print("No members with 3+ denials found")
except Exception as e:
    print(f"Error in repeat denial analysis: {e}")
print()

# QUERY 7: Incomplete submission impact
print("QUERY 7: INCOMPLETE SUBMISSION IMPACT ON DENIAL RATE")
print("-" * 70)
query7 = """
SELECT
    submission_completeness_flag,
    COUNT(*) as total_claims,
    SUM(CASE WHEN claim_status = 'denied' THEN 1 ELSE 0 END) as denial_count,
    ROUND(100.0 * SUM(CASE WHEN claim_status = 'denied' THEN 1 ELSE 0 END) / COUNT(*), 2) as denial_rate_pct,
    ROUND(SUM(CASE WHEN claim_status = 'denied' THEN claim_amount ELSE 0 END) / 1000000, 2) as denied_millions
FROM clarity_claims
GROUP BY submission_completeness_flag
ORDER BY denial_rate_pct DESC
"""
df7 = pd.read_sql_query(query7, conn)
print(df7.to_string(index=False))
print()
findings['incomplete_submissions'] = df7.to_dict('records')

# QUERY 8: Network type impact
print("QUERY 8: NETWORK TYPE IMPACT ON DENIAL RATE")
print("-" * 70)
query8 = """
SELECT
    network_type,
    COUNT(*) as total_claims,
    SUM(CASE WHEN claim_status = 'denied' THEN 1 ELSE 0 END) as denial_count,
    ROUND(100.0 * SUM(CASE WHEN claim_status = 'denied' THEN 1 ELSE 0 END) / COUNT(*), 2) as denial_rate_pct,
    ROUND(SUM(CASE WHEN claim_status = 'denied' THEN claim_amount ELSE 0 END) / 1000000, 2) as denied_millions
FROM clarity_claims
GROUP BY network_type
ORDER BY denial_rate_pct DESC
"""
df8 = pd.read_sql_query(query8, conn)
print(df8.to_string(index=False))
print()
findings['network_impact'] = df8.to_dict('records')

# QUERY 9: Denial by claim category
print("QUERY 9: DENIAL RATE BY CLAIM CATEGORY")
print("-" * 70)
query9 = """
SELECT
    claim_category,
    COUNT(*) as total_claims,
    SUM(CASE WHEN claim_status = 'denied' THEN 1 ELSE 0 END) as denial_count,
    ROUND(100.0 * SUM(CASE WHEN claim_status = 'denied' THEN 1 ELSE 0 END) / COUNT(*), 2) as denial_rate_pct,
    ROUND(SUM(CASE WHEN claim_status = 'denied' THEN claim_amount ELSE 0 END) / 1000000, 2) as denied_millions
FROM clarity_claims
GROUP BY claim_category
ORDER BY denied_millions DESC
"""
df9 = pd.read_sql_query(query9, conn)
print(df9.to_string(index=False))
print()
findings['denial_by_category'] = df9.to_dict('records')

conn.close()

print("="*70)
print("ANALYSIS COMPLETE")
print("="*70)
print()

# Save findings to JSON
import json
findings_json = json.dumps(findings, default=str, indent=2)
with open('../data/findings.json', 'w') as f:
    f.write(findings_json)

print("Findings saved to data/findings.json")
