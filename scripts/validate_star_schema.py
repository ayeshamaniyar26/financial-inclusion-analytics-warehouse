
from pathlib import Path
import duckdb

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "database" / "financial_inclusion.duckdb"

con = duckdb.connect(str(DB_PATH), read_only=True)

expected = {
    "dim_date": None,
    "dim_branch": 32,
    "dim_loan_product": 4,
    "dim_borrower_segment": 4,
    "dim_loan": 50000,
    "fact_loan_snapshot": 50000,
    "fact_installment": 488444,
    "fact_repayment_transaction": 428618,
}

try:
    print("\nSTAR SCHEMA VALIDATION\n")

    all_passed = True

    for table, expected_count in expected.items():
        actual = con.execute(
            f"SELECT COUNT(*) FROM {table}"
        ).fetchone()[0]

        if expected_count is None:
            passed = actual > 0
            expectation = "non-empty"
        else:
            passed = actual == expected_count
            expectation = f"expected {expected_count:,}"

        print(
            f"{table:<32} {actual:>10,} "
            f"{'PASS' if passed else 'FAIL'} ({expectation})"
        )

        if not passed:
            all_passed = False

    print("\nFACT TABLE KEY CHECKS\n")

    checks = {
        "Loan snapshot unique loans": """
            SELECT COUNT(*) - COUNT(DISTINCT loan_id)
            FROM fact_loan_snapshot
        """,
        "Installment grain duplicates": """
            SELECT COUNT(*) - COUNT(DISTINCT
                (loan_id, installment_number))
            FROM fact_installment
        """,
        "Transaction ID duplicates": """
            SELECT COUNT(*) - COUNT(DISTINCT transaction_id)
            FROM fact_repayment_transaction
        """,
        "Missing loan dimension keys": """
            SELECT COUNT(*)
            FROM fact_repayment_transaction
            WHERE loan_key IS NULL
        """,
        "Missing payment date keys": """
            SELECT COUNT(*)
            FROM fact_repayment_transaction
            WHERE payment_date_key IS NULL
        """
    }

    for name, query in checks.items():
        result = con.execute(query).fetchone()[0]
        passed = result == 0

        print(f"{name:<36} {result:>8} "
              f"{'PASS' if passed else 'FAIL'}")

        if not passed:
            all_passed = False

    print(
        "\nFINAL RESULT:",
        "ALL CHECKS PASSED" if all_passed else "VALIDATION FAILED"
    )

finally:
    con.close()
