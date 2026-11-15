
from pathlib import Path

import duckdb
import pandas as pd


ROOT_DIR = Path(__file__).resolve().parent.parent
DB_PATH = ROOT_DIR / "database" / "financial_inclusion.duckdb"


def get_connection():
    """Open the existing warehouse in read-only mode."""
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Warehouse database not found: {DB_PATH}")

    return duckdb.connect(str(DB_PATH), read_only=True)


def run_query(sql, params=None):
    """Execute a parameterized query and return a DataFrame."""
    con = get_connection()
    try:
        return con.execute(sql, params or []).df()
    finally:
        con.close()


def get_filter_options():
    """Return actual filter values from the warehouse dimensions."""
    return {
        "states": run_query(
            "SELECT DISTINCT state FROM dim_branch ORDER BY state"
        )["state"].tolist(),

        "branches": run_query(
            """
            SELECT branch_id, branch_name, state
            FROM dim_branch
            ORDER BY state, branch_name
            """
        ),

        "products": run_query(
            "SELECT loan_product FROM dim_loan_product ORDER BY loan_product"
        )["loan_product"].tolist(),

        "segments": run_query(
            """
            SELECT borrower_segment
            FROM dim_borrower_segment
            ORDER BY borrower_segment
            """
        )["borrower_segment"].tolist(),
    }


def build_filters(
    state=None,
    branch=None,
    product=None,
    segment=None,
    date_from=None,
    date_to=None,
    date_column=None,
):
    """Build safe, parameterized filters for a fact-table query."""
    conditions = []
    params = []

    if state and state != "All States":
        conditions.append("b.state = ?")
        params.append(state)

    if branch and branch != "All Branches":
        conditions.append("b.branch_id = ?")
        params.append(branch)

    if product and product != "All Products":
        conditions.append("p.loan_product = ?")
        params.append(product)

    if segment and segment != "All Segments":
        conditions.append("s.borrower_segment = ?")
        params.append(segment)

    if date_column and date_from:
        conditions.append(f"{date_column} >= ?")
        params.append(pd.Timestamp(date_from).date())

    if date_column and date_to:
        conditions.append(f"{date_column} <= ?")
        params.append(pd.Timestamp(date_to).date())

    where_sql = (
        "WHERE " + " AND ".join(conditions)
        if conditions
        else ""
    )

    return where_sql, params


def get_portfolio_health(
    state=None,
    branch=None,
    product=None,
    segment=None,
):
    """Snapshot KPIs, filtered at one row per loan."""
    where_sql, params = build_filters(
        state=state,
        branch=branch,
        product=product,
        segment=segment,
    )

    sql = f"""
        SELECT
            COUNT(*) AS total_loans,
            COALESCE(SUM(f.loan_amount), 0) AS total_disbursed_amount_inr,
            COALESCE(SUM(f.outstanding_principal), 0)
                AS total_outstanding_principal_inr,

            COALESCE(SUM(
                CASE WHEN f.days_past_due >= 30
                THEN f.outstanding_principal ELSE 0 END
            ), 0) AS par30_outstanding_inr,

            COALESCE(SUM(
                CASE WHEN f.days_past_due >= 90
                THEN f.outstanding_principal ELSE 0 END
            ), 0) AS par90_outstanding_inr,

            ROUND(
                100.0 * SUM(
                    CASE WHEN f.days_past_due >= 30
                    THEN f.outstanding_principal ELSE 0 END
                ) / NULLIF(SUM(f.outstanding_principal), 0),
                2
            ) AS par30_pct,

            ROUND(
                100.0 * SUM(
                    CASE WHEN f.days_past_due >= 90
                    THEN f.outstanding_principal ELSE 0 END
                ) / NULLIF(SUM(f.outstanding_principal), 0),
                2
            ) AS par90_pct,

            COUNT(*) FILTER (WHERE f.days_past_due >= 30)
                AS loans_dpd_30_or_more,

            COUNT(*) FILTER (WHERE f.days_past_due >= 90)
                AS loans_dpd_90_or_more

        FROM fact_loan_snapshot f
        JOIN dim_branch b ON f.branch_key = b.branch_key
        JOIN dim_loan_product p ON f.product_key = p.product_key
        JOIN dim_borrower_segment s ON f.segment_key = s.segment_key

        {where_sql}
    """

    return run_query(sql, params)


def get_collection_efficiency(
    state=None,
    branch=None,
    product=None,
    segment=None,
    date_from=None,
    date_to=None,
):
    """Schedule-based collection efficiency at instalment grain."""
    where_sql, params = build_filters(
        state=state,
        branch=branch,
        product=product,
        segment=segment,
        date_from=date_from,
        date_to=date_to,
        date_column="d.full_date",
    )

    sql = f"""
        SELECT
            b.state,
            b.branch_id,
            b.branch_name,
            SUM(i.amount_due) AS total_amount_due_inr,
            SUM(i.scheduled_amount_paid_proxy)
                AS scheduled_amount_paid_inr,

            ROUND(
                100.0 * SUM(i.scheduled_amount_paid_proxy)
                / NULLIF(SUM(i.amount_due), 0),
                2
            ) AS collection_efficiency_pct,

            COUNT(*) AS instalments_due,

            COUNT(*) FILTER (
                WHERE i.is_paid_by_snapshot
            ) AS instalments_paid

        FROM fact_installment i
        JOIN dim_branch b ON i.branch_key = b.branch_key
        JOIN dim_loan_product p ON i.product_key = p.product_key
        JOIN dim_borrower_segment s ON i.segment_key = s.segment_key
        JOIN dim_date d ON i.due_date_key = d.date_key

        {where_sql}

        GROUP BY b.state, b.branch_id, b.branch_name
        ORDER BY b.state, b.branch_name
    """

    return run_query(sql, params)


def get_vintage_curves(
    state=None,
    branch=None,
    product=None,
    segment=None,
    date_from=None,
    date_to=None,
):
    """Cumulative repayment vintage at loan-installment grain."""
    where_sql, params = build_filters(
        state=state,
        branch=branch,
        product=product,
        segment=segment,
        date_from=date_from,
        date_to=date_to,
        date_column="l.vintage_month",
    )

    sql = f"""
        WITH monthly AS (
            SELECT
                l.vintage_month,
                i.installment_number AS vintage_age_month,
                SUM(i.amount_due) AS amount_due,
                SUM(i.scheduled_amount_paid_proxy) AS amount_paid

            FROM fact_installment i
            JOIN dim_loan l ON i.loan_key = l.loan_key
            JOIN dim_branch b ON i.branch_key = b.branch_key
            JOIN dim_loan_product p ON i.product_key = p.product_key
            JOIN dim_borrower_segment s ON i.segment_key = s.segment_key

            {where_sql}

            GROUP BY l.vintage_month, i.installment_number
        ),

        cumulative AS (
            SELECT
                vintage_month,
                vintage_age_month,

                SUM(amount_due) OVER (
                    PARTITION BY vintage_month
                    ORDER BY vintage_age_month
                    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                ) AS cumulative_amount_due_inr,

                SUM(amount_paid) OVER (
                    PARTITION BY vintage_month
                    ORDER BY vintage_age_month
                    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                ) AS cumulative_amount_paid_proxy_inr

            FROM monthly
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

        FROM cumulative
        ORDER BY vintage_month, vintage_age_month
    """

    return run_query(sql, params)


def get_digital_collections(
    state=None,
    branch=None,
    product=None,
    segment=None,
    date_from=None,
    date_to=None,
):
    """Monthly actual repayment transaction and digital-payment analytics."""
    where_sql, params = build_filters(
        state=state,
        branch=branch,
        product=product,
        segment=segment,
        date_from=date_from,
        date_to=date_to,
        date_column="f.payment_date",
    )

    sql = f"""
        SELECT
            DATE_TRUNC('month', f.payment_date)::DATE AS payment_month,

            COUNT(*) AS total_transactions,
            SUM(f.amount_inr) AS total_collections_inr,

            COUNT(*) FILTER (
                WHERE f.is_digital
            ) AS digital_transactions,

            SUM(
                CASE WHEN f.is_digital
                THEN f.amount_inr ELSE 0 END
            ) AS digital_collections_inr,

            ROUND(
                100.0 * COUNT(*) FILTER (WHERE f.is_digital)
                / NULLIF(COUNT(*), 0),
                2
            ) AS digital_share_count_pct,

            ROUND(
                100.0 * SUM(
                    CASE WHEN f.is_digital
                    THEN f.amount_inr ELSE 0 END
                ) / NULLIF(SUM(f.amount_inr), 0),
                2
            ) AS digital_share_value_pct

        FROM fact_repayment_transaction f
        JOIN dim_branch b ON f.branch_key = b.branch_key
        JOIN dim_loan_product p ON f.product_key = p.product_key
        JOIN dim_borrower_segment s ON f.segment_key = s.segment_key

        {where_sql}

        GROUP BY 1
        ORDER BY 1
    """

    result = run_query(sql, params)

    if not result.empty:
        # Keep the monthly sequence explicit and deterministic before
        # calculating changes. The first selected month has no prior
        # comparison month and therefore remains NULL.
        result["payment_month"] = pd.to_datetime(result["payment_month"])
        result = (
            result.sort_values("payment_month")
            .reset_index(drop=True)
        )

        digital_value = pd.to_numeric(
            result["digital_collections_inr"], errors="coerce"
        )
        previous_month = digital_value.shift(1)
        previous_year = digital_value.shift(12)

        result["digital_value_mom_growth_pct"] = (
            (digital_value - previous_month)
            .div(previous_month.where(previous_month.ne(0)))
            .mul(100)
            .round(2)
        )

        result["digital_value_yoy_growth_pct"] = (
            (digital_value - previous_year)
            .div(previous_year.where(previous_year.ne(0)))
            .mul(100)
            .round(2)
        )

    return result


def get_channel_summary(
    state=None,
    branch=None,
    product=None,
    segment=None,
    date_from=None,
    date_to=None,
):
    """Payment-channel metrics using normalized INR transaction amounts."""
    where_sql, params = build_filters(
        state=state,
        branch=branch,
        product=product,
        segment=segment,
        date_from=date_from,
        date_to=date_to,
        date_column="f.payment_date",
    )

    sql = f"""
        SELECT
            f.channel,
            COUNT(*) AS transaction_count,
            SUM(f.amount_inr) AS total_collections_inr,
            AVG(f.amount_inr) AS average_payment_size_inr,
            MIN(f.amount_inr) AS minimum_payment_inr,
            MAX(f.amount_inr) AS maximum_payment_inr

        FROM fact_repayment_transaction f
        JOIN dim_branch b ON f.branch_key = b.branch_key
        JOIN dim_loan_product p ON f.product_key = p.product_key
        JOIN dim_borrower_segment s ON f.segment_key = s.segment_key

        {where_sql}

        GROUP BY f.channel
        ORDER BY f.channel
    """

    return run_query(sql, params)


def get_data_quality_issues():
    """Retrieve the three deliberately seeded issues."""
    return run_query("""
        SELECT
            issue_id,
            issue_type,
            source,
            description,
            affected_records
        FROM clean_seeded_issues
        ORDER BY issue_id
    """)
