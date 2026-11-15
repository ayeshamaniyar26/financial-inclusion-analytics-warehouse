
-- ============================================================
-- TASK 10: FINANCIAL INCLUSION ANALYTICS WAREHOUSE
-- STAR SCHEMA CREATION
-- Snapshot date: 31 December 2025
-- ============================================================

-- ------------------------------------------------------------
-- 1. DIMENSION: DATE
-- Covers disbursement, instalment due and payment dates.
-- Date key format: YYYYMMDD
-- ------------------------------------------------------------

CREATE OR REPLACE TABLE dim_date AS
WITH all_dates AS (
    SELECT disbursement_date AS dt
    FROM clean_loan_portfolio

    UNION ALL

    SELECT due_date
    FROM clean_installment_schedule

    UNION ALL

    SELECT payment_date
    FROM clean_repayment_transactions

    UNION ALL

    SELECT DATE '2025-12-31'
),
bounds AS (
    SELECT MIN(dt) AS min_date, MAX(dt) AS max_date
    FROM all_dates
)
SELECT
    CAST(strftime(CAST(g.calendar_date AS DATE), '%Y%m%d') AS INTEGER)
        AS date_key,
    CAST(g.calendar_date AS DATE) AS full_date,
    EXTRACT(DAY FROM g.calendar_date)::INTEGER AS day,
    EXTRACT(MONTH FROM g.calendar_date)::INTEGER AS month,
    EXTRACT(YEAR FROM g.calendar_date)::INTEGER AS year,
    strftime(g.calendar_date, '%B') AS month_name,
    strftime(g.calendar_date, '%Y-%m') AS year_month,
    EXTRACT(QUARTER FROM g.calendar_date)::INTEGER AS quarter,
    strftime(g.calendar_date, '%A') AS day_name
FROM bounds,
     generate_series(
         bounds.min_date,
         bounds.max_date,
         INTERVAL 1 DAY
     ) AS g(calendar_date);


-- ------------------------------------------------------------
-- 2. DIMENSION: BRANCH
-- One row per branch, with state information.
-- ------------------------------------------------------------

CREATE OR REPLACE TABLE dim_branch AS
SELECT
    ROW_NUMBER() OVER (ORDER BY branch_id)::BIGINT AS branch_key,
    branch_id,
    branch_name,
    state,
    branch_risk_adjustment
FROM clean_branch_master;


-- ------------------------------------------------------------
-- 3. DIMENSION: LOAN PRODUCT
-- ------------------------------------------------------------

CREATE OR REPLACE TABLE dim_loan_product AS
SELECT
    ROW_NUMBER() OVER (ORDER BY loan_product)::BIGINT
        AS product_key,
    loan_product
FROM (
    SELECT DISTINCT loan_product
    FROM clean_loan_portfolio
) p;


-- ------------------------------------------------------------
-- 4. DIMENSION: BORROWER SEGMENT
-- ------------------------------------------------------------

CREATE OR REPLACE TABLE dim_borrower_segment AS
SELECT
    ROW_NUMBER() OVER (ORDER BY borrower_segment)::BIGINT
        AS segment_key,
    borrower_segment
FROM (
    SELECT DISTINCT borrower_segment
    FROM clean_loan_portfolio
) s;


-- ------------------------------------------------------------
-- 5. DIMENSION: LOAN
-- One row per unique loan.
-- Descriptive loan attributes and vintage cohort.
-- ------------------------------------------------------------

CREATE OR REPLACE TABLE dim_loan AS
SELECT
    ROW_NUMBER() OVER (ORDER BY loan_id)::BIGINT AS loan_key,
    loan_id,
    borrower_id,
    disbursement_date,
    DATE_TRUNC('month', disbursement_date)::DATE
        AS vintage_month,
    loan_amount,
    annual_interest_rate,
    tenure_months,
    monthly_instalment,
    total_repayment_expected,
    source_unit
FROM clean_loan_portfolio;


-- ------------------------------------------------------------
-- 6. FACT: LOAN SNAPSHOT
-- Grain: one row per loan at 31 December 2025.
-- Used for PAR30 and PAR90.
-- ------------------------------------------------------------

CREATE OR REPLACE TABLE fact_loan_snapshot AS
SELECT
    l.loan_key,
    d.date_key AS snapshot_date_key,
    b.branch_key,
    p.product_key,
    s.segment_key,

    lp.loan_id,
    lp.loan_amount,
    lp.outstanding_principal,
    lp.days_past_due,
    lp.instalments_due,
    lp.instalments_paid,
    lp.loan_status,

    CASE WHEN lp.days_past_due >= 30
         THEN TRUE ELSE FALSE END AS is_par30,

    CASE WHEN lp.days_past_due >= 90
         THEN TRUE ELSE FALSE END AS is_par90

FROM clean_loan_portfolio lp
JOIN dim_loan l
    ON lp.loan_id = l.loan_id
JOIN dim_date d
    ON d.full_date = DATE '2025-12-31'
JOIN dim_branch b
    ON lp.branch_id = b.branch_id
JOIN dim_loan_product p
    ON lp.loan_product = p.loan_product
JOIN dim_borrower_segment s
    ON lp.borrower_segment = s.borrower_segment;


-- ------------------------------------------------------------
-- 7. FACT: INSTALLMENT
-- Grain: one row per scheduled loan instalment.
-- Used for schedule-based collection realization and vintage.
--
-- IMPORTANT:
-- scheduled_amount_paid_proxy is a schedule-based proxy.
-- It is NOT an independently reconciled transaction allocation.
-- ------------------------------------------------------------

CREATE OR REPLACE TABLE fact_installment AS
SELECT
    l.loan_key,
    due.date_key AS due_date_key,
    disb.date_key AS disbursement_date_key,
    b.branch_key,
    p.product_key,
    s.segment_key,

    i.loan_id,
    i.installment_number,
    i.amount_due,
    i.principal_due,
    i.is_paid_by_snapshot,

    CASE
        WHEN i.is_paid_by_snapshot THEN i.amount_due
        ELSE 0
    END AS scheduled_amount_paid_proxy,

    CASE
        WHEN i.is_paid_by_snapshot THEN 1
        ELSE 0
    END AS paid_installment_count

FROM clean_installment_schedule i
JOIN dim_loan l
    ON i.loan_id = l.loan_id
JOIN dim_date due
    ON i.due_date = due.full_date
JOIN dim_date disb
    ON i.disbursement_date = disb.full_date
JOIN dim_branch b
    ON i.branch_id = b.branch_id
JOIN dim_loan_product p
    ON i.loan_product = p.loan_product
JOIN dim_borrower_segment s
    ON i.borrower_segment = s.borrower_segment;


-- ------------------------------------------------------------
-- 8. FACT: REPAYMENT TRANSACTION
-- Grain: one row per recorded repayment transaction.
-- ------------------------------------------------------------

CREATE OR REPLACE TABLE fact_repayment_transaction AS
SELECT
    l.loan_key,
    d.date_key AS payment_date_key,
    b.branch_key,
    p.product_key,
    s.segment_key,

    r.transaction_id,
    r.loan_id,
    r.payment_date,
    r.amount AS original_amount,
    r.amount_unit,
    r.amount_inr,
    r.channel,
    r.source_system,

    CASE
        WHEN r.channel IN ('UPI', 'Bank Transfer')
            THEN TRUE
        ELSE FALSE
    END AS is_digital

FROM clean_repayment_transactions r
JOIN clean_loan_portfolio lp
    ON r.loan_id = lp.loan_id
JOIN dim_loan l
    ON r.loan_id = l.loan_id
JOIN dim_date d
    ON r.payment_date = d.full_date
JOIN dim_branch b
    ON r.branch_id = b.branch_id
JOIN dim_loan_product p
    ON lp.loan_product = p.loan_product
JOIN dim_borrower_segment s
    ON lp.borrower_segment = s.borrower_segment;
