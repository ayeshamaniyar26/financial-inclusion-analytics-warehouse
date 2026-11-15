
-- ============================================================
-- TASK 10: FINANCIAL INCLUSION ANALYTICS WAREHOUSE
-- KPI VIEWS
-- Snapshot date: 31 December 2025
-- ============================================================


-- ------------------------------------------------------------
-- 1. PORTFOLIO HEALTH
-- PAR30 and PAR90 are measured by outstanding principal value.
-- ------------------------------------------------------------

CREATE OR REPLACE VIEW vw_portfolio_health AS
SELECT
    COUNT(*) AS total_loans,

    SUM(loan_amount) AS total_disbursed_amount_inr,

    SUM(outstanding_principal) AS total_outstanding_principal_inr,

    SUM(
        CASE WHEN is_par30
             THEN outstanding_principal ELSE 0 END
    ) AS par30_outstanding_inr,

    SUM(
        CASE WHEN is_par90
             THEN outstanding_principal ELSE 0 END
    ) AS par90_outstanding_inr,

    ROUND(
        100.0 * SUM(
            CASE WHEN is_par30
                 THEN outstanding_principal ELSE 0 END
        ) / NULLIF(SUM(outstanding_principal), 0),
        2
    ) AS par30_pct,

    ROUND(
        100.0 * SUM(
            CASE WHEN is_par90
                 THEN outstanding_principal ELSE 0 END
        ) / NULLIF(SUM(outstanding_principal), 0),
        2
    ) AS par90_pct,

    SUM(CASE WHEN is_par30 THEN 1 ELSE 0 END)
        AS loans_dpd_30_or_more,

    SUM(CASE WHEN is_par90 THEN 1 ELSE 0 END)
        AS loans_dpd_90_or_more

FROM fact_loan_snapshot;


-- ------------------------------------------------------------
-- 2. COLLECTION EFFICIENCY BY STATE AND BRANCH
-- Schedule-based realization as of the snapshot.
-- ------------------------------------------------------------

CREATE OR REPLACE VIEW vw_collection_efficiency_by_branch AS
SELECT
    b.state,
    b.branch_id,
    b.branch_name,

    COUNT(*) AS instalments_due,

    SUM(f.amount_due) AS total_amount_due_inr,

    SUM(f.scheduled_amount_paid_proxy)
        AS scheduled_amount_paid_inr,

    ROUND(
        100.0 * SUM(f.scheduled_amount_paid_proxy)
        / NULLIF(SUM(f.amount_due), 0),
        2
    ) AS collection_efficiency_pct,

    SUM(f.paid_installment_count) AS instalments_paid

FROM fact_installment f
JOIN dim_branch b
    ON f.branch_key = b.branch_key

GROUP BY
    b.state,
    b.branch_id,
    b.branch_name;


-- ------------------------------------------------------------
-- 3. COLLECTION EFFICIENCY BY STATE
-- ------------------------------------------------------------

CREATE OR REPLACE VIEW vw_collection_efficiency_by_state AS
SELECT
    b.state,

    COUNT(*) AS instalments_due,

    SUM(f.amount_due) AS total_amount_due_inr,

    SUM(f.scheduled_amount_paid_proxy)
        AS scheduled_amount_paid_inr,

    ROUND(
        100.0 * SUM(f.scheduled_amount_paid_proxy)
        / NULLIF(SUM(f.amount_due), 0),
        2
    ) AS collection_efficiency_pct,

    SUM(f.paid_installment_count) AS instalments_paid

FROM fact_installment f
JOIN dim_branch b
    ON f.branch_key = b.branch_key

GROUP BY b.state;


-- ------------------------------------------------------------
-- 4. REPAYMENT VINTAGE CURVES
-- Cohort = month of loan disbursement.
-- Age = instalment number.
-- Values are cumulative schedule-based amounts.
-- ------------------------------------------------------------

CREATE OR REPLACE VIEW vw_vintage_curves AS
WITH cohort_age AS (
    SELECT
        l.vintage_month,
        f.installment_number AS vintage_age_month,

        SUM(f.amount_due) AS amount_due_inr,

        SUM(f.scheduled_amount_paid_proxy)
            AS amount_paid_proxy_inr

    FROM fact_installment f
    JOIN dim_loan l
        ON f.loan_key = l.loan_key

    GROUP BY
        l.vintage_month,
        f.installment_number
),
cumulative AS (
    SELECT
        vintage_month,
        vintage_age_month,

        SUM(amount_due_inr) OVER (
            PARTITION BY vintage_month
            ORDER BY vintage_age_month
            ROWS BETWEEN UNBOUNDED PRECEDING
                     AND CURRENT ROW
        ) AS cumulative_amount_due_inr,

        SUM(amount_paid_proxy_inr) OVER (
            PARTITION BY vintage_month
            ORDER BY vintage_age_month
            ROWS BETWEEN UNBOUNDED PRECEDING
                     AND CURRENT ROW
        ) AS cumulative_amount_paid_proxy_inr

    FROM cohort_age
)
SELECT
    vintage_month,
    vintage_age_month,
    cumulative_amount_due_inr,
    cumulative_amount_paid_proxy_inr,

    ROUND(
        100.0 * cumulative_amount_paid_proxy_inr
        / NULLIF(cumulative_amount_due_inr, 0),
        2
    ) AS cumulative_collection_pct

FROM cumulative;


-- ------------------------------------------------------------
-- 5. MONTHLY DIGITAL COLLECTIONS
-- Includes digital share by value and transaction count.
-- Also includes MoM and YoY growth in digital value.
-- ------------------------------------------------------------

CREATE OR REPLACE VIEW vw_digital_collections_monthly AS
WITH month_calendar AS (
    SELECT DISTINCT
        DATE_TRUNC('month', full_date)::DATE AS payment_month
    FROM dim_date
),
monthly_actuals AS (
    SELECT
        DATE_TRUNC('month', payment_date)::DATE AS payment_month,

        COUNT(*) AS total_transactions,

        SUM(amount_inr) AS total_collections_inr,

        SUM(CASE WHEN is_digital THEN 1 ELSE 0 END)
            AS digital_transactions,

        SUM(
            CASE WHEN is_digital THEN amount_inr ELSE 0 END
        ) AS digital_collections_inr

    FROM fact_repayment_transaction
    GROUP BY 1
),
monthly AS (
    SELECT
        c.payment_month,

        COALESCE(a.total_transactions, 0)
            AS total_transactions,

        COALESCE(a.total_collections_inr, 0)
            AS total_collections_inr,

        COALESCE(a.digital_transactions, 0)
            AS digital_transactions,

        COALESCE(a.digital_collections_inr, 0)
            AS digital_collections_inr

    FROM month_calendar c
    LEFT JOIN monthly_actuals a
        ON c.payment_month = a.payment_month
),
with_previous AS (
    SELECT
        *,

        LAG(digital_collections_inr, 1) OVER (
            ORDER BY payment_month
        ) AS previous_month_digital_inr,

        LAG(digital_collections_inr, 12) OVER (
            ORDER BY payment_month
        ) AS previous_year_digital_inr

    FROM monthly
)
SELECT
    payment_month,

    total_transactions,
    total_collections_inr,

    digital_transactions,
    digital_collections_inr,

    ROUND(
        100.0 * digital_transactions
        / NULLIF(total_transactions, 0),
        2
    ) AS digital_share_count_pct,

    ROUND(
        100.0 * digital_collections_inr
        / NULLIF(total_collections_inr, 0),
        2
    ) AS digital_share_value_pct,

    ROUND(
        100.0 * (
            digital_collections_inr - previous_month_digital_inr
        ) / NULLIF(previous_month_digital_inr, 0),
        2
    ) AS digital_value_mom_growth_pct,

    ROUND(
        100.0 * (
            digital_collections_inr - previous_year_digital_inr
        ) / NULLIF(previous_year_digital_inr, 0),
        2
    ) AS digital_value_yoy_growth_pct

FROM with_previous;


-- ------------------------------------------------------------
-- 6. AVERAGE PAYMENT SIZE BY CHANNEL
-- Uses normalized INR values, not original mixed units.
-- ------------------------------------------------------------

CREATE OR REPLACE VIEW vw_average_payment_size_by_channel AS
SELECT
    channel,

    COUNT(*) AS transaction_count,

    SUM(amount_inr) AS total_collections_inr,

    AVG(amount_inr) AS average_payment_size_inr,

    MIN(amount_inr) AS minimum_payment_inr,

    MAX(amount_inr) AS maximum_payment_inr

FROM fact_repayment_transaction

GROUP BY channel;


-- ============================================================
-- END OF KPI VIEWS
-- ============================================================
