
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
REPORT = ROOT / "documentation" / "raw_data_profile.txt"

# Load raw datasets without modifying them
loans = pd.read_csv(RAW / "loan_portfolio_raw.csv")
schedule = pd.read_csv(RAW / "installment_schedule_raw.csv")
payments = pd.read_csv(RAW / "repayment_transactions_raw.csv")
branches = pd.read_csv(RAW / "branch_master.csv")
seeded = pd.read_csv(RAW / "seeded_issues.csv")

results = []

def check(name, actual, expected=None):
    line = f"{name}: {actual}"
    if expected is not None:
        line += f" | Expected: {expected}"
    results.append(line)
    print(line)

def section(name):
    results.append("\n" + "=" * 65)
    results.append(name)
    results.append("=" * 65)
    print("\n" + "=" * 65)
    print(name)
    print("=" * 65)

# --------------------------------------------------
# 1. DATASET SIZES
# --------------------------------------------------
section("1. DATASET SIZES")

check("Loan portfolio rows", len(loans), 50100)
check("Unique loan IDs", loans["loan_id"].nunique(), 50000)
check("Instalment schedule rows", len(schedule))
check("Repayment transaction rows", len(payments))
check("Branch master rows", len(branches), 32)

# --------------------------------------------------
# 2. LOAN PORTFOLIO VALIDATION
# --------------------------------------------------
section("2. LOAN PORTFOLIO")

check("Duplicate loan IDs",
      loans["loan_id"].duplicated().sum(), 100)

check("Duplicate complete rows",
      loans.duplicated().sum())

check("Missing values by column",
      loans.isnull().sum().to_dict())

check("Number of states", loans["state"].nunique(), 8)
check("Number of branches", loans["branch_id"].nunique(), 32)

check("Loan products", loans["loan_product"].nunique())
check("Borrower segments", loans["borrower_segment"].nunique())

check("Loan amount minimum", loans["loan_amount"].min())
check("Loan amount maximum", loans["loan_amount"].max())

check("Invalid loan amounts",
      (loans["loan_amount"] <= 0).sum())

check("Invalid tenure",
      (loans["tenure_months"] <= 0).sum())

check("Negative outstanding principal",
      (loans["outstanding_principal"] < 0).sum())

check("Negative DPD",
      (loans["days_past_due"] < 0).sum())

check("Paid instalments exceeding due instalments",
      (loans["instalments_paid"] > loans["instalments_due"]).sum())

# --------------------------------------------------
# 3. INSTALMENT SCHEDULE VALIDATION
# --------------------------------------------------
section("3. INSTALMENT SCHEDULE")

loan_ids = set(loans["loan_id"].dropna().unique())

check("Schedule loan IDs missing from portfolio",
      (~schedule["loan_id"].isin(loan_ids)).sum())

check("Duplicate loan-installment combinations",
      schedule.duplicated(
          subset=["loan_id", "installment_number"]
      ).sum())

check("Missing schedule values",
      schedule.isnull().sum().to_dict())

check("Non-positive instalment amounts",
      (schedule["amount_due"] <= 0).sum())

check("Non-positive principal amounts",
      (schedule["principal_due"] <= 0).sum())

check("Principal exceeding instalment amount",
      (schedule["principal_due"] > schedule["amount_due"]).sum())

schedule["due_date"] = pd.to_datetime(
    schedule["due_date"], errors="coerce"
)

check("Invalid schedule due dates",
      schedule["due_date"].isna().sum())

if schedule["due_date"].notna().any():
    check("Earliest instalment due date",
          schedule["due_date"].min())
    check("Latest instalment due date",
          schedule["due_date"].max())

# --------------------------------------------------
# 4. REPAYMENT TRANSACTION VALIDATION
# --------------------------------------------------
section("4. REPAYMENT TRANSACTIONS")

check("Duplicate transaction IDs",
      payments["transaction_id"].duplicated().sum())

check("Payment loan IDs missing from portfolio",
      (~payments["loan_id"].isin(loan_ids)).sum())

check("Missing transaction values",
      payments.isnull().sum().to_dict())

check("Non-positive payment amounts",
      (payments["amount"] <= 0).sum())

payments["payment_date"] = pd.to_datetime(
    payments["payment_date"], errors="coerce"
)

check("Invalid payment dates",
      payments["payment_date"].isna().sum())

if payments["payment_date"].notna().any():
    earliest = payments["payment_date"].min()
    latest = payments["payment_date"].max()

    check("First payment date", earliest)
    check("Last payment date", latest)
    check("Coverage in days", (latest - earliest).days)

    check("At least two years of dates",
          (latest - earliest).days >= 730)

check("Payment channels",
      payments["channel"].value_counts().to_dict())

check("Source systems",
      payments["source_system"].value_counts().to_dict())

# --------------------------------------------------
# 5. SEEDED DATA QUALITY ISSUES
# --------------------------------------------------
section("5. SEEDED DATA QUALITY ISSUES")

duplicate_count = loans["loan_id"].duplicated().sum()

check("I001 - Duplicate loan rows detected",
      duplicate_count, 100)

unit_counts = payments["amount_unit"].value_counts().to_dict()
check("I003 - Amount unit distribution", unit_counts)

non_inr = payments[
    payments["amount_unit"].astype(str).str.upper() != "INR"
]

check("I003 - Non-INR unit records",
      len(non_inr), 4063)

partner_non_inr = non_inr[
    non_inr["source_system"].astype(str).str.contains(
        "PARTNER", case=False, na=False
    )
]

check("I003 - Partner portal non-INR records",
      len(partner_non_inr), 4063)

# Check missing branch-month
payments["month"] = payments["payment_date"].dt.to_period("M")

missing_month_count = (
    (payments["branch_id"] == "BR0101") &
    (payments["month"] == pd.Period("2025-04", freq="M"))
).sum()

check("I002 - BR0101 transactions in April 2025",
      missing_month_count, 0)

# --------------------------------------------------
# 6. BRANCH MASTER VALIDATION
# --------------------------------------------------
section("6. BRANCH MASTER")

check("Unique branch IDs",
      branches["branch_id"].nunique(), 32)

check("Unique states in branch master",
      branches["state"].nunique(), 8)

check("Duplicate branch IDs",
      branches["branch_id"].duplicated().sum())

check("Missing branch master values",
      branches.isnull().sum().to_dict())

portfolio_branches = set(loans["branch_id"].dropna())
master_branches = set(branches["branch_id"].dropna())

check("Portfolio branches missing from master",
      sorted(portfolio_branches - master_branches))

# --------------------------------------------------
# 7. DIGITAL COLLECTION TREND
# --------------------------------------------------
section("7. DIGITAL COLLECTION TREND")

digital_channels = ["UPI", "BANK_TRANSFER"]

payments["is_digital"] = payments["channel"].isin(
    digital_channels
)

monthly = (
    payments.groupby("month")
    .apply(
        lambda x: pd.Series({
            "total_payments": len(x),
            "digital_count": x["is_digital"].sum(),
            "total_value": x["amount"].sum(),
            "digital_value": x.loc[
                x["is_digital"], "amount"
            ].sum()
        }),
        include_groups=False
    )
    .reset_index()
)

monthly["digital_count_share_pct"] = (
    monthly["digital_count"] /
    monthly["total_payments"] * 100
)

monthly["digital_value_share_pct"] = (
    monthly["digital_value"] /
    monthly["total_value"] * 100
)

if len(monthly) >= 6:
    first = monthly.head(3)["digital_count_share_pct"].mean()
    last = monthly.tail(3)["digital_count_share_pct"].mean()

    check("Digital count share - first 3 months (%)", round(first, 2))
    check("Digital count share - last 3 months (%)", round(last, 2))
    check("Digital share increased",
          last > first)

results.append("\nMonthly digital trend:")
results.append(monthly.to_string(index=False))
print(monthly.to_string(index=False))

# --------------------------------------------------
# 8. SEEDED ISSUE MANIFEST
# --------------------------------------------------
section("8. SEEDED ISSUE MANIFEST")

print(seeded.to_string(index=False))
results.append(seeded.to_string(index=False))

# --------------------------------------------------
# 9. SAVE REPORT
# --------------------------------------------------
REPORT.parent.mkdir(parents=True, exist_ok=True)
REPORT.write_text("\n".join(results), encoding="utf-8")

print("\n" + "=" * 65)
print("PROFILING COMPLETED")
print("Report saved to:", REPORT)
print("=" * 65)
