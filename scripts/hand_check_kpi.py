
from pathlib import Path
import duckdb

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "database" / "financial_inclusion.duckdb"

con = duckdb.connect(str(DB_PATH), read_only=True)

try:
    # Independently calculate PAR30 from the loan snapshot fact.
    numerator, denominator = con.execute("""
        SELECT
            SUM(
                CASE
                    WHEN days_past_due >= 30
                    THEN outstanding_principal
                    ELSE 0
                END
            ),
            SUM(outstanding_principal)
        FROM fact_loan_snapshot
    """).fetchone()

    manual_par30 = numerator / denominator * 100

    # Retrieve the KPI view result separately.
    view_par30 = con.execute("""
        SELECT par30_pct
        FROM vw_portfolio_health
    """).fetchone()[0]

    print("\nINDEPENDENT PAR30 VERIFICATION")
    print("--------------------------------")
    print(f"PAR30 numerator:   INR {numerator:,.2f}")
    print(f"Portfolio balance: INR {denominator:,.2f}")
    print(f"Manual PAR30:      {manual_par30:.2f}%")
    print(f"KPI view PAR30:    {view_par30:.2f}%")
    print(f"Difference:        {abs(manual_par30 - view_par30):.6f}")

    assert abs(manual_par30 - view_par30) < 0.01

    print("\nPASS: Independent PAR30 calculation matches KPI view.")

    # Also inspect digital adoption directly from monthly results.
    print("\nFIRST THREE MONTHS — DIGITAL ADOPTION")

    print(con.execute("""
        SELECT
            payment_month,
            digital_share_count_pct,
            digital_share_value_pct
        FROM vw_digital_collections_monthly
        ORDER BY payment_month
        LIMIT 3
    """).df().to_string(index=False))

    print("\nLAST THREE MONTHS — DIGITAL ADOPTION")

    print(con.execute("""
        SELECT
            payment_month,
            digital_share_count_pct,
            digital_share_value_pct
        FROM vw_digital_collections_monthly
        ORDER BY payment_month DESC
        LIMIT 3
    """).df().to_string(index=False))

finally:
    con.close()
