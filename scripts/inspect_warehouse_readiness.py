from pathlib import Path
import duckdb

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "database" / "financial_inclusion.duckdb"

con = duckdb.connect(str(DB_PATH), read_only=True)

queries = {
    "Instalment payment status": """
        SELECT
            is_paid_by_snapshot,
            COUNT(*) AS instalment_count,
            ROUND(SUM(amount_due), 2) AS total_amount_due
        FROM clean_installment_schedule
        GROUP BY is_paid_by_snapshot
        ORDER BY is_paid_by_snapshot
    """,

    "Repayment transaction totals": """
        SELECT
            COUNT(*) AS transaction_count,
            COUNT(DISTINCT loan_id) AS loans_with_payments,
            ROUND(SUM(amount_inr), 2) AS total_repayments_inr
        FROM clean_repayment_transactions
    """,

    "Loan portfolio snapshot": """
        SELECT
            COUNT(*) AS loan_count,
            ROUND(SUM(outstanding_principal), 2) AS total_outstanding,
            COUNT(*) FILTER (WHERE days_past_due >= 30) AS loans_dpd_30,
            COUNT(*) FILTER (WHERE days_past_due >= 90) AS loans_dpd_90
        FROM clean_loan_portfolio
    """,

    "Transaction counts per loan": """
        SELECT
            COUNT(*) AS loans_with_multiple_transactions
        FROM (
            SELECT loan_id
            FROM clean_repayment_transactions
            GROUP BY loan_id
            HAVING COUNT(*) > 1
        ) t
    """,

    "Installment and transaction counts": """
        SELECT
            (SELECT COUNT(*)
             FROM clean_installment_schedule
             WHERE is_paid_by_snapshot = TRUE) AS paid_instalments,
            (SELECT COUNT(*)
             FROM clean_repayment_transactions) AS repayment_transactions
    """
}

try:
    for title, query in queries.items():
        print(f"\n--- {title} ---")
        print(con.execute(query).fetchdf().to_string(index=False))
finally:
    con.close()