
from pathlib import Path
import duckdb

# --------------------------------------------------
# FINANCIAL INCLUSION ANALYTICS WAREHOUSE
# Load original CSV files into DuckDB raw layer
# --------------------------------------------------

ROOT = Path(__file__).resolve().parents[1]

RAW_DIR = ROOT / "data" / "raw"
DB_DIR = ROOT / "database"

DB_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DB_DIR / "financial_inclusion.duckdb"

# Source CSV -> DuckDB table
DATASETS = {
    "loan_portfolio_raw.csv": "raw_loan_portfolio",
    "installment_schedule_raw.csv": "raw_installment_schedule",
    "repayment_transactions_raw.csv": "raw_repayment_transactions",
    "branch_master.csv": "raw_branch_master",
    "seeded_issues.csv": "raw_seeded_issues",
}


def main():

    con = duckdb.connect(str(DB_PATH))

    try:
        print("\nLoading raw datasets into DuckDB...\n")

        for filename, table_name in DATASETS.items():

            file_path = RAW_DIR / filename

            if not file_path.exists():
                raise FileNotFoundError(
                    f"Required dataset not found: {file_path}"
                )

            # Load source CSV without modifying the original file
            con.execute(
                f"""
                CREATE OR REPLACE TABLE {table_name} AS
                SELECT *
                FROM read_csv_auto(
                    ?,
                    header = true,
                    sample_size = -1
                )
                """,
                [str(file_path)]
            )

            row_count = con.execute(
                f"SELECT COUNT(*) FROM {table_name}"
            ).fetchone()[0]

            print(
                f"{table_name:<35} {row_count:>10,} rows"
            )

        print("\nChecking primary dataset counts...")

        loan_count = con.execute(
            "SELECT COUNT(*) FROM raw_loan_portfolio"
        ).fetchone()[0]

        unique_loans = con.execute(
            "SELECT COUNT(DISTINCT loan_id) "
            "FROM raw_loan_portfolio"
        ).fetchone()[0]

        branch_count = con.execute(
            "SELECT COUNT(*) FROM raw_branch_master"
        ).fetchone()[0]

        assert loan_count == 50100, "Loan row count mismatch"
        assert unique_loans == 50000, "Unique loan count mismatch"
        assert branch_count == 32, "Branch count mismatch"

        con.execute("CHECKPOINT")

        print("\nRAW DATA LOAD SUCCESSFUL")
        print(f"Database: {DB_PATH}")
        print(f"Loan rows: {loan_count:,}")
        print(f"Unique loans: {unique_loans:,}")
        print(f"Branches: {branch_count}")

    finally:
        con.close()


if __name__ == "__main__":
    main()
