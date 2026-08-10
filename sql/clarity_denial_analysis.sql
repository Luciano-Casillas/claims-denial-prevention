-- ============================================================
-- CLARITY HEALTH PLANS - CLAIMS DENIAL ANALYSIS
-- ============================================================
-- Queries to discover and answer business questions:
-- Q1: Which providers create the denial crisis?
-- Q2: What's causing denials?
-- Q3: Can we predict denial risk?
-- Q4: Which members repeat deny?
-- Q5: Top 3 denial drivers & recovery opportunity?
-- Q6: Network patterns predicting denial risk?
--
-- Tables:
--   clarity_claims (200k rows)
--   clarity_denials (7.8k rows)
--   clarity_providers (350 rows)
--   clarity_members (100k rows)
--   clarity_prior_auth (80k rows)
--   clarity_claims_detail (270k rows)
-- ============================================================


-- ============================================================
-- SECTION 1: DATA QUALITY AUDIT & BASELINE METRICS
-- ============================================================

-- Q: What's the baseline denial rate and financial impact?
SELECT
    COUNT(*) as total_claims,
    SUM(CASE WHEN claim_status = 'denied' THEN 1 ELSE 0 END) as denied_count,
    ROUND(100.0 * SUM(CASE WHEN claim_status = 'denied' THEN 1 ELSE 0 END) / COUNT(*), 2) as denial_rate_pct,
    ROUND(SUM(claim_amount) / 1000000, 2) as total_submitted_millions,
    ROUND(SUM(CASE WHEN claim_status = 'denied' THEN claim_amount ELSE 0 END) / 1000000, 2) as total_denied_millions,
    ROUND(AVG(CASE WHEN claim_status = 'denied' THEN claim_amount ELSE NULL END), 0) as avg_denied_claim_amount
FROM clarity_claims;

-- Q: How much data quality issues are we dealing with?
SELECT
    COUNT(*) as total_claims,
    SUM(CASE WHEN provider_id IS NULL THEN 1 ELSE 0 END) as missing_provider_id_count,
    ROUND(100.0 * SUM(CASE WHEN provider_id IS NULL THEN 1 ELSE 0 END) / COUNT(*), 2) as missing_provider_id_pct,
    SUM(CASE WHEN submission_completeness_flag = 'incomplete' THEN 1 ELSE 0 END) as incomplete_submissions,
    ROUND(100.0 * SUM(CASE WHEN submission_completeness_flag = 'incomplete' THEN 1 ELSE 0 END) / COUNT(*), 2) as incomplete_submission_pct
FROM clarity_claims;

-- Q: How many denials have data quality issues in the denial codes?
SELECT
    COUNT(*) as total_denials,
    SUM(CASE WHEN denial_reason_code IS NULL THEN 1 ELSE 0 END) as null_reason_codes,
    SUM(CASE WHEN denial_reason_code IN ('missing auth', 'provider not network') THEN 1 ELSE 0 END) as free_text_codes,
    SUM(CASE WHEN denial_reason_code IN ('999') THEN 1 ELSE 0 END) as invalid_codes,
    SUM(CASE WHEN CAST(denied_claim_amount AS NUMERIC) != CAST(claimed_amount AS NUMERIC) THEN 1 ELSE 0 END) as denied_amount_mismatches
FROM (
    SELECT d.*, c.claim_amount as claimed_amount
    FROM clarity_denials d
    LEFT JOIN clarity_claims c ON d.claim_id = c.claim_id
);


-- ============================================================
-- SECTION 2: PROVIDER SEGMENTATION & RANKINGS
-- ============================================================

-- Q1: Which providers create the denial crisis? (Top 20 by denied $)
SELECT
    p.provider_id,
    p.provider_name,
    p.provider_type,
    p.specialty,
    p.network_status,
    p.geographic_region,
    COUNT(d.denial_id) as denial_count,
    ROUND(100.0 * COUNT(d.denial_id) / COUNT(c.claim_id), 2) as denial_rate_pct,
    ROUND(SUM(CASE WHEN c.claim_status = 'denied' THEN c.claim_amount ELSE 0 END) / 1000000, 2) as denied_amount_millions,
    COUNT(c.claim_id) as total_claims_from_provider
FROM clarity_claims c
LEFT JOIN clarity_providers p ON c.provider_id = p.provider_id
LEFT JOIN clarity_denials d ON c.claim_id = d.claim_id AND c.claim_status = 'denied'
WHERE c.provider_id IS NOT NULL
GROUP BY p.provider_id, p.provider_name, p.provider_type, p.specialty, p.network_status, p.geographic_region
ORDER BY denied_amount_millions DESC
LIMIT 20;

-- Q: Provider denial rate by specialty (which specialties deny most?)
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
ORDER BY denial_rate_pct DESC;

-- Q: Provider denial rate by network status
SELECT
    p.network_status,
    COUNT(c.claim_id) as total_claims,
    SUM(CASE WHEN c.claim_status = 'denied' THEN 1 ELSE 0 END) as denial_count,
    ROUND(100.0 * SUM(CASE WHEN c.claim_status = 'denied' THEN 1 ELSE 0 END) / COUNT(c.claim_id), 2) as denial_rate_pct,
    ROUND(SUM(CASE WHEN c.claim_status = 'denied' THEN c.claim_amount ELSE 0 END) / 1000000, 2) as denied_millions
FROM clarity_claims c
LEFT JOIN clarity_providers p ON c.provider_id = p.provider_id
WHERE c.provider_id IS NOT NULL
GROUP BY p.network_status
ORDER BY denial_rate_pct DESC;


-- ============================================================
-- SECTION 3: DENIAL ROOT CAUSE ANALYSIS
-- ============================================================

-- Q2: What's causing denials? (root cause breakdown)
SELECT
    COALESCE(denial_reason_code, 'NULL_CODE') as reason_code,
    CASE
        WHEN denial_reason_code IN ('PA01', 'PA02', 'PA03') THEN 'prior_auth_delay'
        WHEN denial_reason_code IN ('CVRG01', 'CVRG02') THEN 'coverage_limit'
        WHEN denial_reason_code IN ('NW01', 'NW02', 'provider not network') THEN 'network_issue'
        WHEN denial_reason_code IN ('BILL01', 'BILL02') THEN 'billing_error'
        WHEN denial_reason_code IN ('MED01') THEN 'medical_necessity'
        WHEN denial_reason_code IN ('missing auth', 'provider not network') THEN 'other_free_text'
        WHEN denial_reason_code IN ('999') THEN 'invalid_code'
        WHEN denial_reason_code IS NULL THEN 'null'
        ELSE 'other'
    END as standardized_reason,
    COUNT(*) as denial_count,
    ROUND(SUM(denied_claim_amount) / 1000000, 2) as denied_millions,
    ROUND(100.0 * SUM(denied_claim_amount) / (SELECT SUM(denied_claim_amount) FROM clarity_denials), 2) as pct_of_denied_dollars,
    ROUND(AVG(denied_claim_amount), 0) as avg_denied_amount
FROM clarity_denials
GROUP BY denial_reason_code
ORDER BY denied_millions DESC;

-- Q: Appeal success rate by denial reason
SELECT
    CASE
        WHEN denial_reason_code IN ('PA01', 'PA02', 'PA03') THEN 'prior_auth_delay'
        WHEN denial_reason_code IN ('CVRG01', 'CVRG02') THEN 'coverage_limit'
        WHEN denial_reason_code IN ('NW01', 'NW02', 'provider not network') THEN 'network_issue'
        WHEN denial_reason_code IN ('BILL01', 'BILL02') THEN 'billing_error'
        WHEN denial_reason_code IN ('MED01') THEN 'medical_necessity'
        ELSE 'other'
    END as standardized_reason,
    COUNT(*) as total_appeals,
    SUM(CASE WHEN appeal_submitted = TRUE THEN 1 ELSE 0 END) as appeals_submitted,
    ROUND(100.0 * SUM(CASE WHEN appeal_submitted = TRUE THEN 1 ELSE 0 END) / COUNT(*), 1) as appeal_rate_pct,
    SUM(CASE WHEN appeal_outcome IN ('approved', 'partial_approval') THEN 1 ELSE 0 END) as appeals_won,
    ROUND(100.0 * SUM(CASE WHEN appeal_outcome IN ('approved', 'partial_approval') THEN 1 ELSE 0 END) / 
          NULLIF(SUM(CASE WHEN appeal_submitted = TRUE THEN 1 ELSE 0 END), 0), 1) as appeal_success_rate_pct
FROM clarity_denials
GROUP BY standardized_reason
ORDER BY appeals_won DESC;


-- ============================================================
-- SECTION 4: MEMBER SEGMENT & REPEAT DENIAL ANALYSIS
-- ============================================================

-- Q4: Which members repeat deny? (Repeat denial members)
SELECT
    m.member_id,
    m.income_bracket,
    m.chronic_condition_flags,
    m.age_group,
    m.plan_type,
    COUNT(DISTINCT c.claim_id) as total_claims,
    COUNT(DISTINCT d.denial_id) as total_denials,
    ROUND(100.0 * COUNT(DISTINCT d.denial_id) / COUNT(DISTINCT c.claim_id), 1) as denial_rate_pct,
    ROUND(SUM(CASE WHEN d.denial_id IS NOT NULL THEN d.denied_claim_amount ELSE 0 END) / 1000000, 2) as total_denied_millions
FROM clarity_members m
LEFT JOIN clarity_claims c ON m.member_id = c.member_id
LEFT JOIN clarity_denials d ON c.claim_id = d.claim_id
GROUP BY m.member_id, m.income_bracket, m.chronic_condition_flags, m.age_group, m.plan_type
HAVING COUNT(DISTINCT d.denial_id) >= 3
ORDER BY total_denials DESC
LIMIT 100;

-- Q: How many members fall into repeat denial category?
SELECT
    SUM(CASE WHEN denial_count = 0 THEN member_count ELSE 0 END) as members_0_denials,
    SUM(CASE WHEN denial_count BETWEEN 1 AND 2 THEN member_count ELSE 0 END) as members_1_to_2_denials,
    SUM(CASE WHEN denial_count >= 3 THEN member_count ELSE 0 END) as members_3_plus_denials,
    SUM(member_count) as total_members_with_claims
FROM (
    SELECT
        m.member_id,
        COUNT(DISTINCT d.denial_id) as denial_count,
        1 as member_count
    FROM clarity_members m
    LEFT JOIN clarity_claims c ON m.member_id = c.member_id
    LEFT JOIN clarity_denials d ON c.claim_id = d.claim_id
    GROUP BY m.member_id
) denial_counts;

-- Q: Repeat denial member segment characteristics
SELECT
    income_bracket,
    chronic_condition_flags,
    COUNT(DISTINCT member_id) as member_count,
    ROUND(100.0 * COUNT(DISTINCT member_id) / SUM(COUNT(DISTINCT member_id)) OVER(), 1) as pct_of_repeat_denial_members
FROM (
    SELECT
        m.member_id,
        m.income_bracket,
        m.chronic_condition_flags
    FROM clarity_members m
    LEFT JOIN clarity_claims c ON m.member_id = c.member_id
    LEFT JOIN clarity_denials d ON c.claim_id = d.claim_id
    GROUP BY m.member_id, m.income_bracket, m.chronic_condition_flags
    HAVING COUNT(DISTINCT d.denial_id) >= 3
) repeat_denial_members
GROUP BY income_bracket, chronic_condition_flags
ORDER BY member_count DESC;


-- ============================================================
-- SECTION 5: PRIOR AUTH & PROCESSING TIME ANALYSIS
-- ============================================================

-- Q: Prior auth processing time impact on denials
SELECT
    CASE
        WHEN pa.processing_days IS NULL THEN 'no_auth'
        WHEN pa.processing_days <= 3 THEN '1_to_3_days'
        WHEN pa.processing_days <= 7 THEN '4_to_7_days'
        WHEN pa.processing_days > 7 THEN '8_plus_days'
    END as auth_processing_bucket,
    COUNT(DISTINCT c.claim_id) as claims_count,
    SUM(CASE WHEN c.claim_status = 'denied' THEN 1 ELSE 0 END) as denial_count,
    ROUND(100.0 * SUM(CASE WHEN c.claim_status = 'denied' THEN 1 ELSE 0 END) / COUNT(DISTINCT c.claim_id), 2) as denial_rate_pct
FROM clarity_claims c
LEFT JOIN clarity_prior_auth pa ON c.claim_id = pa.claim_id
WHERE c.prior_auth_required = TRUE
GROUP BY auth_processing_bucket
ORDER BY denial_rate_pct DESC;

-- Q: Orphaned prior auth records (prior auths without matching claims)
SELECT
    COUNT(*) as total_orphaned_auth_records,
    ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM clarity_prior_auth), 1) as pct_of_all_auth
FROM clarity_prior_auth pa
WHERE pa.claim_id NOT IN (SELECT claim_id FROM clarity_claims);


-- ============================================================
-- SECTION 6: FINANCIAL IMPACT & RECOVERY OPPORTUNITY
-- ============================================================

-- Q5: Top denial drivers ranked by financial impact
SELECT
    CASE
        WHEN denial_reason_code IN ('PA01', 'PA02', 'PA03') THEN 'prior_auth_delay'
        WHEN denial_reason_code IN ('CVRG01', 'CVRG02') THEN 'coverage_limit'
        WHEN denial_reason_code IN ('NW01', 'NW02', 'provider not network') THEN 'network_issue'
        WHEN denial_reason_code IN ('BILL01', 'BILL02') THEN 'billing_error'
        WHEN denial_reason_code IN ('MED01') THEN 'medical_necessity'
        ELSE 'other'
    END as denial_category,
    COUNT(*) as denial_count,
    ROUND(SUM(denied_claim_amount) / 1000000, 2) as denied_millions,
    ROUND(AVG(denied_claim_amount), 0) as avg_denied_claim,
    ROUND(100.0 * SUM(denied_claim_amount) / (SELECT SUM(denied_claim_amount) FROM clarity_denials), 2) as pct_of_total_denied_dollars
FROM clarity_denials
GROUP BY denial_category
ORDER BY denied_millions DESC
LIMIT 5;

-- Q: Total denied claims by claim category
SELECT
    c.claim_category,
    COUNT(DISTINCT c.claim_id) as total_claims,
    SUM(CASE WHEN c.claim_status = 'denied' THEN 1 ELSE 0 END) as denial_count,
    ROUND(100.0 * SUM(CASE WHEN c.claim_status = 'denied' THEN 1 ELSE 0 END) / COUNT(DISTINCT c.claim_id), 2) as denial_rate_pct,
    ROUND(SUM(CASE WHEN c.claim_status = 'denied' THEN c.claim_amount ELSE 0 END) / 1000000, 2) as denied_millions
FROM clarity_claims c
LEFT JOIN clarity_denials d ON c.claim_id = d.claim_id
GROUP BY c.claim_category
ORDER BY denied_millions DESC;


-- ============================================================
-- SECTION 7: SUBMISSION QUALITY & INCOMPLETE SUBMISSION IMPACT
-- ============================================================

-- Q: Incomplete submission impact on denial rate
SELECT
    c.submission_completeness_flag,
    COUNT(*) as total_claims,
    SUM(CASE WHEN c.claim_status = 'denied' THEN 1 ELSE 0 END) as denial_count,
    ROUND(100.0 * SUM(CASE WHEN c.claim_status = 'denied' THEN 1 ELSE 0 END) / COUNT(*), 2) as denial_rate_pct,
    ROUND(SUM(CASE WHEN c.claim_status = 'denied' THEN c.claim_amount ELSE 0 END) / 1000000, 2) as denied_millions
FROM clarity_claims c
GROUP BY c.submission_completeness_flag
ORDER BY denial_rate_pct DESC;

-- Q: Which providers submit incomplete claims most often?
SELECT
    p.provider_id,
    p.provider_name,
    p.specialty,
    COUNT(*) as total_claims,
    SUM(CASE WHEN c.submission_completeness_flag = 'incomplete' THEN 1 ELSE 0 END) as incomplete_count,
    ROUND(100.0 * SUM(CASE WHEN c.submission_completeness_flag = 'incomplete' THEN 1 ELSE 0 END) / COUNT(*), 1) as incomplete_pct,
    SUM(CASE WHEN c.claim_status = 'denied' THEN 1 ELSE 0 END) as denial_count,
    ROUND(100.0 * SUM(CASE WHEN c.claim_status = 'denied' THEN 1 ELSE 0 END) / COUNT(*), 1) as denial_rate_pct
FROM clarity_claims c
LEFT JOIN clarity_providers p ON c.provider_id = p.provider_id
WHERE c.provider_id IS NOT NULL
GROUP BY p.provider_id, p.provider_name, p.specialty
HAVING SUM(CASE WHEN c.submission_completeness_flag = 'incomplete' THEN 1 ELSE 0 END) >= 10
ORDER BY incomplete_pct DESC
LIMIT 15;


-- ============================================================
-- SECTION 8: NETWORK & GEOGRAPHIC PATTERNS
-- ============================================================

-- Q6: Network type denial rate analysis
SELECT
    c.network_type,
    COUNT(*) as total_claims,
    SUM(CASE WHEN c.claim_status = 'denied' THEN 1 ELSE 0 END) as denial_count,
    ROUND(100.0 * SUM(CASE WHEN c.claim_status = 'denied' THEN 1 ELSE 0 END) / COUNT(*), 2) as denial_rate_pct,
    ROUND(SUM(CASE WHEN c.claim_status = 'denied' THEN c.claim_amount ELSE 0 END) / 1000000, 2) as denied_millions
FROM clarity_claims c
GROUP BY c.network_type
ORDER BY denial_rate_pct DESC;

-- Q: Geographic region denial rate
SELECT
    COALESCE(p.geographic_region, 'unknown') as region,
    COUNT(c.claim_id) as total_claims,
    SUM(CASE WHEN c.claim_status = 'denied' THEN 1 ELSE 0 END) as denial_count,
    ROUND(100.0 * SUM(CASE WHEN c.claim_status = 'denied' THEN 1 ELSE 0 END) / COUNT(c.claim_id), 2) as denial_rate_pct,
    ROUND(SUM(CASE WHEN c.claim_status = 'denied' THEN c.claim_amount ELSE 0 END) / 1000000, 2) as denied_millions
FROM clarity_claims c
LEFT JOIN clarity_providers p ON c.provider_id = p.provider_id
WHERE c.provider_id IS NOT NULL
GROUP BY region
ORDER BY denial_rate_pct DESC;


-- ============================================================
-- SECTION 9: MODEL INPUT FEATURES (For Q3 - Denial Risk Prediction)
-- ============================================================

-- Q3: Feature engineering baseline (what signals predict denial?)
SELECT
    c.network_type,
    c.submission_completeness_flag,
    c.prior_auth_required,
    c.claim_category,
    COALESCE(p.provider_type, 'unknown') as provider_type,
    COALESCE(p.specialty, 'unknown') as specialty,
    COUNT(c.claim_id) as claim_count,
    SUM(CASE WHEN c.claim_status = 'denied' THEN 1 ELSE 0 END) as denial_count,
    ROUND(100.0 * SUM(CASE WHEN c.claim_status = 'denied' THEN 1 ELSE 0 END) / COUNT(c.claim_id), 2) as denial_rate_pct
FROM clarity_claims c
LEFT JOIN clarity_providers p ON c.provider_id = p.provider_id
GROUP BY
    c.network_type,
    c.submission_completeness_flag,
    c.prior_auth_required,
    c.claim_category,
    provider_type,
    specialty
ORDER BY denial_rate_pct DESC
LIMIT 30;

-- ============================================================
-- END OF ANALYSIS
-- ============================================================
