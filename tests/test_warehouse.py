
from pathlib import Path

import duckdb
import pytest


# ------------------------------------------------------------
# DATABASE CONNECTION
# ------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "database" / "financial_inclusion.duckdb"


@pytest.fixture(scope="module")
def con():
    """Open the existing warehouse in read-only mode."""
    connection = duckdb.connect(str(DB_PATH), read_only=True)
    yield connection
    connection.close()


def scalar(con, query):
    """Return the first value from a SQL query."""
    return con.execute(query).fetchone()[0]


def assert_zero(con, query, message):
    """Pass when a data-quality issue count is zero."""
    result = scalar(con, query)
    assert result == 0, f"{message}. Found: {result}"


# ============================================================
# A. RAW DATA AND SEEDED ISSUE TESTS
# ============================================================

def test_raw_loan_portfolio_has_expected_rows(con):
    assert scalar(
        con, "SELECT COUNT(*) FROM raw_loan_portfolio"
    ) == 50100


def test_raw_loan_duplicates_are_detectable(con):
    duplicates = scalar(
        con,
        """
        SELECT COUNT(*) - COUNT(DISTINCT loan_id)
        FROM raw_loan_portfolio
        """
    )
    assert duplicates == 100


def test_raw_transaction_unit_issue_is_present(con):
    count = scalar(
        con,
        """
        SELECT COUNT(*)
        FROM raw_repayment_transactions
        WHERE UPPER(TRIM(amount_unit)) = 'THOUSANDS_INR'
        """
    )
    assert count > 0


def test_raw_missing_branch_month_is_detectable(con):
    count = scalar(
        con,
        """
        SELECT COUNT(*)
        FROM raw_repayment_transactions
        WHERE branch_id = 'BR0101'
          AND EXTRACT(YEAR FROM payment_date) = 2025
          AND EXTRACT(MONTH FROM payment_date) = 4
        """
    )
    assert count == 0


def test_raw_data_contains_expected_amount_units(con):
    units = {
        row[0]
        for row in con.execute(
            """
            SELECT DISTINCT UPPER(TRIM(amount_unit))
            FROM raw_repayment_transactions
            """
        ).fetchall()
    }

    assert "INR" in units
    assert "THOUSANDS_INR" in units


# ============================================================
# B. CLEAN LAYER TESTS
# ============================================================

def test_clean_loan_portfolio_has_50000_rows(con):
    assert scalar(
        con, "SELECT COUNT(*) FROM clean_loan_portfolio"
    ) == 50000


def test_clean_loan_ids_are_unique(con):
    assert_zero(
        con,
        """
        SELECT COUNT(*) - COUNT(DISTINCT loan_id)
        FROM clean_loan_portfolio
        """,
        "Duplicate loan IDs remain in clean portfolio",
    )


def test_clean_schedule_has_expected_rows(con):
    assert scalar(
        con, "SELECT COUNT(*) FROM clean_installment_schedule"
    ) == 488444


def test_clean_schedule_grain_is_unique(con):
    assert_zero(
        con,
        """
        SELECT COUNT(*) - COUNT(
            DISTINCT (loan_id, installment_number)
        )
        FROM clean_installment_schedule
        """,
        "Duplicate loan-installment combinations",
    )


def test_clean_transactions_have_expected_rows(con):
    assert scalar(
        con, "SELECT COUNT(*) FROM clean_repayment_transactions"
    ) == 428618


def test_clean_transaction_ids_are_unique(con):
    assert_zero(
        con,
        """
        SELECT COUNT(*) - COUNT(DISTINCT transaction_id)
        FROM clean_repayment_transactions
        """,
        "Duplicate transaction IDs remain",
    )


def test_clean_transactions_have_no_null_normalized_amounts(con):
    assert_zero(
        con,
        """
        SELECT COUNT(*)
        FROM clean_repayment_transactions
        WHERE amount_inr IS NULL
        """,
        "Null normalized repayment amounts",
    )


def test_clean_transactions_have_positive_amounts(con):
    assert_zero(
        con,
        """
        SELECT COUNT(*)
        FROM clean_repayment_transactions
        WHERE amount_inr <= 0
        """,
        "Non-positive normalized repayment amounts",
    )


def test_clean_transactions_have_no_unknown_units(con):
    assert_zero(
        con,
        """
        SELECT COUNT(*)
        FROM clean_repayment_transactions
        WHERE unit_normalization_status <> 'NORMALIZED'
        """,
        "Unknown amount units remain",
    )


def test_inr_amounts_are_normalized_correctly(con):
    assert_zero(
        con,
        """
        SELECT COUNT(*)
        FROM clean_repayment_transactions
        WHERE UPPER(TRIM(amount_unit)) = 'INR'
          AND ABS(amount_inr - amount) > 0.0001
        """,
        "Incorrect INR normalization",
    )


def test_thousands_inr_amounts_are_normalized_correctly(con):
    assert_zero(
        con,
        """
        SELECT COUNT(*)
        FROM clean_repayment_transactions
        WHERE UPPER(TRIM(amount_unit)) = 'THOUSANDS_INR'
          AND ABS(amount_inr - amount * 1000.0) > 0.0001
        """,
        "Incorrect THOUSANDS_INR normalization",
    )


def test_clean_transactions_have_no_orphan_loans(con):
    assert_zero(
        con,
        """
        SELECT COUNT(*)
        FROM clean_repayment_transactions r
        LEFT JOIN clean_loan_portfolio l
            ON r.loan_id = l.loan_id
        WHERE l.loan_id IS NULL
        """,
        "Orphan repayment loan IDs",
    )


# ============================================================
# C. DIMENSION TABLE TESTS
# ============================================================

def test_branch_dimension_has_32_rows(con):
    assert scalar(con, "SELECT COUNT(*) FROM dim_branch") == 32


def test_branch_dimension_keys_are_unique(con):
    assert_zero(
        con,
        """
        SELECT COUNT(*) - COUNT(DISTINCT branch_key)
        FROM dim_branch
        """,
        "Duplicate branch dimension keys",
    )


def test_product_dimension_has_four_products(con):
    assert scalar(
        con, "SELECT COUNT(*) FROM dim_loan_product"
    ) == 4


def test_borrower_segment_dimension_has_four_segments(con):
    assert scalar(
        con, "SELECT COUNT(*) FROM dim_borrower_segment"
    ) == 4


def test_loan_dimension_has_50000_unique_loans(con):
    assert scalar(
        con, "SELECT COUNT(*) FROM dim_loan"
    ) == 50000

    assert_zero(
        con,
        """
        SELECT COUNT(*) - COUNT(DISTINCT loan_key)
        FROM dim_loan
        """,
        "Duplicate loan dimension keys",
    )


def test_date_dimension_keys_are_unique(con):
    assert_zero(
        con,
        """
        SELECT COUNT(*) - COUNT(DISTINCT date_key)
        FROM dim_date
        """,
        "Duplicate date dimension keys",
    )


# ============================================================
# D. FACT TABLE AND REFERENTIAL INTEGRITY TESTS
# ============================================================

def test_loan_snapshot_has_50000_rows(con):
    assert scalar(
        con, "SELECT COUNT(*) FROM fact_loan_snapshot"
    ) == 50000


def test_loan_snapshot_has_one_row_per_loan(con):
    assert_zero(
        con,
        """
        SELECT COUNT(*) - COUNT(DISTINCT loan_id)
        FROM fact_loan_snapshot
        """,
        "Loan snapshot does not have one row per loan",
    )


def test_installment_fact_matches_clean_schedule(con):
    fact_count = scalar(
        con, "SELECT COUNT(*) FROM fact_installment"
    )
    clean_count = scalar(
        con, "SELECT COUNT(*) FROM clean_installment_schedule"
    )
    assert fact_count == clean_count


def test_installment_fact_has_unique_grain(con):
    assert_zero(
        con,
        """
        SELECT COUNT(*) - COUNT(
            DISTINCT (loan_id, installment_number)
        )
        FROM fact_installment
        """,
        "Duplicate instalment fact grain",
    )


def test_transaction_fact_matches_clean_transactions(con):
    fact_count = scalar(
        con, "SELECT COUNT(*) FROM fact_repayment_transaction"
    )
    clean_count = scalar(
        con, "SELECT COUNT(*) FROM clean_repayment_transactions"
    )
    assert fact_count == clean_count


def test_transaction_fact_ids_are_unique(con):
    assert_zero(
        con,
        """
        SELECT COUNT(*) - COUNT(DISTINCT transaction_id)
        FROM fact_repayment_transaction
        """,
        "Duplicate transaction fact IDs",
    )


def test_transaction_fact_has_valid_loan_keys(con):
    assert_zero(
        con,
        """
        SELECT COUNT(*)
        FROM fact_repayment_transaction f
        LEFT JOIN dim_loan d
            ON f.loan_key = d.loan_key
        WHERE d.loan_key IS NULL
        """,
        "Invalid loan dimension references",
    )


def test_transaction_fact_has_valid_branch_keys(con):
    assert_zero(
        con,
        """
        SELECT COUNT(*)
        FROM fact_repayment_transaction f
        LEFT JOIN dim_branch d
            ON f.branch_key = d.branch_key
        WHERE d.branch_key IS NULL
        """,
        "Invalid branch dimension references",
    )


def test_transaction_fact_has_valid_payment_date_keys(con):
    assert_zero(
        con,
        """
        SELECT COUNT(*)
        FROM fact_repayment_transaction f
        LEFT JOIN dim_date d
            ON f.payment_date_key = d.date_key
        WHERE d.date_key IS NULL
        """,
        "Invalid payment date dimension references",
    )


# ============================================================
# E. BUSINESS RULE TESTS
# ============================================================

def test_par30_flag_matches_dpd_rule(con):
    assert_zero(
        con,
        """
        SELECT COUNT(*)
        FROM fact_loan_snapshot
        WHERE is_par30 <> (days_past_due >= 30)
        """,
        "PAR30 flag does not match the DPD rule",
    )


def test_par90_flag_matches_dpd_rule(con):
    assert_zero(
        con,
        """
        SELECT COUNT(*)
        FROM fact_loan_snapshot
        WHERE is_par90 <> (days_past_due >= 90)
        """,
        "PAR90 flag does not match the DPD rule",
    )


def test_digital_flag_matches_channel(con):
    assert_zero(
        con,
        """
        SELECT COUNT(*)
        FROM fact_repayment_transaction
        WHERE is_digital <>
            (channel IN ('UPI', 'Bank Transfer'))
        """,
        "Digital flag does not match channel classification",
    )


def test_digital_share_increases_over_time(con):
    result = con.execute(
        """
        WITH monthly AS (
            SELECT
                DATE_TRUNC('month', payment_date) AS month,
                AVG(
                    CASE WHEN is_digital THEN 1.0 ELSE 0.0 END
                ) AS digital_share
            FROM fact_repayment_transaction
            GROUP BY 1
        ),
        ranked AS (
            SELECT
                month,
                digital_share,
                ROW_NUMBER() OVER (ORDER BY month) AS first_rank,
                ROW_NUMBER() OVER (ORDER BY month DESC) AS last_rank
            FROM monthly
        ),
        comparison AS (
            SELECT
                AVG(
                    CASE WHEN first_rank <= 3
                         THEN digital_share END
                ) AS first_three_months,
                AVG(
                    CASE WHEN last_rank <= 3
                         THEN digital_share END
                ) AS last_three_months
            FROM ranked
        )
        SELECT
            first_three_months,
            last_three_months
        FROM comparison
        """
    ).fetchone()

    first_share, last_share = result

    assert first_share is not None
    assert last_share is not None
    assert last_share > first_share, (
        "Digital transaction count share did not increase "
        "between the first and last three months"
    )
