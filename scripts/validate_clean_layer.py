from pathlib import Path
import duckdb

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "database" / "financial_inclusion.duckdb"

con = duckdb.connect(str(DB_PATH), read_only=True)

try:
    print("\nCLEAN LAYER VALIDATION\n")

    checks = {
        "Unknown unit rows": """
            SELECT COUNT(*)
            FROM clean_repayment_transactions
            WHERE unit_normalization_status <> 'NORMALIZED'
        """,
        "Null normalized amounts": """
            SELECT COUNT(*)
            FROM clean_repayment_transactions
            WHERE amount_inr IS NULL
        """,
        "Non-positive normalized amounts": """
            SELECT COUNT(*)
            FROM clean_repayment_transactions
            WHERE amount_inr <= 0
        """,
        "Duplicate loan IDs": """
            SELECT COUNT(*) - COUNT(DISTINCT loan_id)
            FROM clean_loan_portfolio
        """,
        "Duplicate transaction IDs": """
            SELECT COUNT(*) - COUNT(DISTINCT transaction_id)
            FROM clean_repayment_transactions
        """,
        "Orphan repayment loan IDs": """
            SELECT COUNT(*)
            FROM clean_repayment_transactions r
            LEFT JOIN clean_loan_portfolio l
                ON r.loan_id = l.loan_id
            WHERE l.loan_id IS NULL
        """
    }

    all_passed = True

    for name, query in checks.items():
        result = con.execute(query).fetchone()[0]
        status = "PASS" if result == 0 else "FAIL"

        print(f"{name:<35} {result:>8}  {status}")

        if result != 0:
            all_passed = False

    print("\nVALIDATION RESULT:",
          "ALL CHECKS PASSED" if all_passed else "CHECKS FAILED")

finally:
    con.close()