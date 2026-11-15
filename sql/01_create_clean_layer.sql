-- 1. Clean loan portfolio
-- The 100 seeded duplicate records are exact duplicate rows.
-- DISTINCT removes those duplicates while preserving all original columns.

CREATE OR REPLACE TABLE clean_loan_portfolio AS
SELECT DISTINCT *
FROM raw_loan_portfolio;


-- 2. Clean installment schedule
-- Grain: one row per loan_id + installment_number.
-- Profiling found no duplicate loan-installment combinations.

CREATE OR REPLACE TABLE clean_installment_schedule AS
SELECT *
FROM raw_installment_schedule;


-- 3. Clean repayment transactions
-- Grain: one row per transaction_id.
-- Keep original amount and amount_unit for auditability.
-- Convert THOUSANDS_INR to INR in the additional amount_inr column.

CREATE OR REPLACE TABLE clean_repayment_transactions AS
SELECT
    transaction_id,
    loan_id,
    branch_id,
    state,
    payment_date,
    amount,
    amount_unit,
    CASE
        WHEN UPPER(TRIM(amount_unit)) = 'THOUSANDS_INR'
            THEN amount * 1000.0
        WHEN UPPER(TRIM(amount_unit)) = 'INR'
            THEN amount
        ELSE NULL
    END AS amount_inr,
    channel,
    source_system,
    CASE
        WHEN UPPER(TRIM(amount_unit)) IN ('INR', 'THOUSANDS_INR')
            THEN 'NORMALIZED'
        ELSE 'UNKNOWN_UNIT'
    END AS unit_normalization_status
FROM raw_repayment_transactions;


-- 4. Clean branch master
-- Remove exact duplicate rows, if any.

CREATE OR REPLACE TABLE clean_branch_master AS
SELECT DISTINCT *
FROM raw_branch_master;


-- 5. Preserve seeded issue manifest as an auditable reference.

CREATE OR REPLACE TABLE clean_seeded_issues AS
SELECT *
FROM raw_seeded_issues;