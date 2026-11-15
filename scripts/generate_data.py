
from pathlib import Path
import numpy as np
import pandas as pd

# ============================================================
# FINANCIAL INCLUSION ANALYTICS WAREHOUSE
# Synthetic data generator
# ============================================================

SEED = 42
N_LOANS = 50_000
START_DATE = pd.Timestamp("2023-11-01")
END_DATE = pd.Timestamp("2025-12-31")
SNAPSHOT_DATE = END_DATE

rng = np.random.default_rng(SEED)

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)


# ------------------------------------------------------------
# 1. BUSINESS ASSUMPTIONS
# ------------------------------------------------------------

# These are simulated assumptions, not real company statistics.

STATE_BRANCHES = {
    "Karnataka": ["Hubballi", "Bengaluru", "Mysuru", "Belagavi"],
    "Maharashtra": ["Pune", "Mumbai", "Nagpur", "Nashik"],
    "Telangana": ["Hyderabad", "Warangal", "Karimnagar", "Nizamabad"],
    "Tamil Nadu": ["Chennai", "Coimbatore", "Madurai", "Salem"],
    "Andhra Pradesh": ["Vijayawada", "Guntur", "Tirupati", "Nellore"],
    "Kerala": ["Kochi", "Thrissur", "Kozhikode", "Kannur"],
    "Gujarat": ["Ahmedabad", "Surat", "Rajkot", "Vadodara"],
    "Rajasthan": ["Jaipur", "Jodhpur", "Udaipur", "Kota"]
}

PRODUCTS = {
    "Micro Enterprise": {
        "amount": (30000, 150000),
        "annual_rate": 0.16,
        "risk_adjustment": -0.01
    },
    "Agriculture": {
        "amount": (20000, 100000),
        "annual_rate": 0.14,
        "risk_adjustment": 0.02
    },
    "Women Group": {
        "amount": (10000, 60000),
        "annual_rate": 0.12,
        "risk_adjustment": -0.03
    },
    "Personal Loan": {
        "amount": (15000, 80000),
        "annual_rate": 0.20,
        "risk_adjustment": 0.04
    }
}

SEGMENTS = ["Low Income", "Small Business", "Agricultural", "Salaried"]

TENURES = [6, 12, 18, 24]

PRODUCT_NAMES = list(PRODUCTS.keys())
STATE_NAMES = list(STATE_BRANCHES.keys())

SEGMENT_RISK = {
    "Low Income": 0.02,
    "Small Business": -0.01,
    "Agricultural": 0.025,
    "Salaried": -0.03
}


# ------------------------------------------------------------
# 2. CREATE BRANCH MASTER
# ------------------------------------------------------------

branch_records = []

for state_index, (state, branches) in enumerate(STATE_BRANCHES.items()):
    for branch_index, branch in enumerate(branches):

        branch_id = f"BR{state_index + 1:02d}{branch_index + 1:02d}"

        branch_records.append({
            "branch_id": branch_id,
            "branch_name": branch,
            "state": state,
            # Different branches have slightly different
            # repayment performance.
            "branch_risk_adjustment": rng.uniform(-0.04, 0.025)
        })

branch_master = pd.DataFrame(branch_records)

branch_master.to_csv(
    RAW_DIR / "branch_master.csv",
    index=False
)

print("Branch master created:", len(branch_master))


# ------------------------------------------------------------
# 3. GENERATE 50,000 UNIQUE LOANS
# ------------------------------------------------------------

print("\nGenerating loan portfolio...")

loan_ids = [
    f"L{i:06d}" for i in range(1, N_LOANS + 1)
]

loan_states = rng.choice(
    STATE_NAMES,
    size=N_LOANS
)

loan_branches = []

for state in loan_states:
    available = branch_master[
        branch_master["state"] == state
    ]["branch_id"].values

    loan_branches.append(rng.choice(available))

loan_branches = np.array(loan_branches)

branch_adjustments = branch_master.set_index(
    "branch_id"
)["branch_risk_adjustment"]

loan_branch_risk = np.array([
    branch_adjustments[b] for b in loan_branches
])

loan_products = rng.choice(
    PRODUCT_NAMES,
    size=N_LOANS,
    p=[0.30, 0.25, 0.25, 0.20]
)

borrower_segments = rng.choice(
    SEGMENTS,
    size=N_LOANS
)

tenures = rng.choice(
    TENURES,
    size=N_LOANS,
    p=[0.15, 0.40, 0.25, 0.20]
)

disbursement_dates = pd.to_datetime(
    rng.integers(
        START_DATE.value // 10**9,
        END_DATE.value // 10**9 + 1,
        size=N_LOANS
    ),
    unit="s"
).normalize()

loan_amounts = np.zeros(N_LOANS)
annual_rates = np.zeros(N_LOANS)
product_risks = np.zeros(N_LOANS)

for product, rules in PRODUCTS.items():

    mask = loan_products == product

    low, high = rules["amount"]

    loan_amounts[mask] = rng.integers(
        low,
        high + 1,
        size=mask.sum()
    )

    annual_rates[mask] = rules["annual_rate"]
    product_risks[mask] = rules["risk_adjustment"]

branch_names = branch_master.set_index(
    "branch_id"
)["branch_name"]

loan_portfolio = pd.DataFrame({
    "loan_id": loan_ids,
    "borrower_id": [f"BOR{i:06d}" for i in range(1, N_LOANS + 1)],
    "state": loan_states,
    "branch_id": loan_branches,
    "branch": [branch_names[b] for b in loan_branches],
    "loan_product": loan_products,
    "borrower_segment": borrower_segments,
    "disbursement_date": disbursement_dates,
    "loan_amount": loan_amounts,
    "annual_interest_rate": annual_rates,
    "tenure_months": tenures,
    "source_unit": "INR"
})

loan_portfolio["total_repayment_expected"] = (
    loan_portfolio["loan_amount"]
    * (
        1
        + loan_portfolio["annual_interest_rate"]
        * loan_portfolio["tenure_months"] / 12
    )
).round(2)

loan_portfolio["monthly_instalment"] = (
    loan_portfolio["total_repayment_expected"]
    / loan_portfolio["tenure_months"]
).round(2)


# ------------------------------------------------------------
# 4. GENERATE MONTHLY INSTALMENT SCHEDULE
# ------------------------------------------------------------

print("Generating monthly instalment schedules...")

schedule_parts = []
transaction_parts = []

base_payment_probability = (
    0.94
    + loan_branch_risk
    - np.array([SEGMENT_RISK[s] for s in borrower_segments])
    - product_risks
)

payment_probability = np.clip(
    base_payment_probability,
    0.65,
    0.99
)

for installment_number in range(1, max(TENURES) + 1):

    active = tenures >= installment_number

    indexes = np.where(active)[0]

    due_dates = (
        disbursement_dates[indexes]
        + pd.DateOffset(months=installment_number)
    )

    within_period = due_dates <= SNAPSHOT_DATE

    indexes = indexes[within_period]
    due_dates = due_dates[within_period]

    if len(indexes) == 0:
        continue

    principal_due = (
        loan_amounts[indexes] / tenures[indexes]
    ).round(2)

    amount_due = (
        loan_portfolio.loc[indexes, "monthly_instalment"].values
    )

    paid_attempt = (
        rng.random(len(indexes))
        < payment_probability[indexes]
    )

    late_days = rng.integers(
        0, 61, size=len(indexes)
    )

    payment_dates = (
        due_dates + pd.to_timedelta(late_days, unit="D")
    )

    paid_by_snapshot = (
        paid_attempt
        & (payment_dates <= SNAPSHOT_DATE)
    )

    schedule = pd.DataFrame({
        "loan_id": np.array(loan_ids)[indexes],
        "branch_id": loan_branches[indexes],
        "state": loan_states[indexes],
        "loan_product": loan_products[indexes],
        "borrower_segment": borrower_segments[indexes],
        "disbursement_date": disbursement_dates[indexes],
        "installment_number": installment_number,
        "due_date": due_dates,
        "amount_due": amount_due,
        "principal_due": principal_due,
        "is_paid_by_snapshot": paid_by_snapshot
    })

    schedule_parts.append(schedule)

    paid_indexes = np.where(paid_by_snapshot)[0]

    if len(paid_indexes) > 0:

        payment_dates_paid = payment_dates[paid_indexes]

        # Digital adoption increases gradually over time.
        months_elapsed = (
            (payment_dates_paid.year - START_DATE.year) * 12
            + payment_dates_paid.month - START_DATE.month
        )

        total_months = (
            (END_DATE.year - START_DATE.year) * 12
            + END_DATE.month - START_DATE.month
        )

        digital_share = (
            0.35 + 0.40 * months_elapsed / total_months
        )

        digital_share = np.clip(digital_share, 0.35, 0.75)

        channel_random = rng.random(len(paid_indexes))

        channels = np.where(
            channel_random < digital_share * 0.65,
            "UPI",
            np.where(
                channel_random < digital_share,
                "Bank Transfer",
                "Cash"
            )
        )

        tx = pd.DataFrame({
            "loan_id": np.array(loan_ids)[indexes[paid_indexes]],
            "branch_id": loan_branches[indexes[paid_indexes]],
            "state": loan_states[indexes[paid_indexes]],
            "payment_date": payment_dates_paid,
            "amount": amount_due[paid_indexes],
            "channel": channels,
            "source_system": rng.choice(
                ["CORE_BANKING", "PARTNER_PORTAL"],
                size=len(paid_indexes),
                p=[0.85, 0.15]
            ),
            "amount_unit": "INR"
        })

        transaction_parts.append(tx)


# ------------------------------------------------------------
# 5. COMBINE SCHEDULES AND TRANSACTIONS
# ------------------------------------------------------------

schedule_df = pd.concat(
    schedule_parts,
    ignore_index=True
)

transactions = pd.concat(
    transaction_parts,
    ignore_index=True
)

transactions.insert(
    0,
    "transaction_id",
    [f"T{i:08d}" for i in range(1, len(transactions) + 1)]
)

print("Scheduled instalments:", len(schedule_df))
print("Generated transactions:", len(transactions))


# ------------------------------------------------------------
# 6. AGGREGATE LOAN-LEVEL REPAYMENT INFORMATION
# ------------------------------------------------------------

print("Calculating loan-level repayment information...")

loan_aggregates = schedule_df.groupby("loan_id").agg(
    instalments_due=("installment_number", "count"),
    instalments_paid=("is_paid_by_snapshot", "sum")
).reset_index()

unpaid = schedule_df[
    ~schedule_df["is_paid_by_snapshot"]
].copy()

unpaid_aggregates = unpaid.groupby("loan_id").agg(
    outstanding_principal=("principal_due", "sum"),
    oldest_unpaid_due_date=("due_date", "min")
).reset_index()

loan_portfolio = loan_portfolio.merge(
    loan_aggregates,
    on="loan_id",
    how="left"
)

loan_portfolio = loan_portfolio.merge(
    unpaid_aggregates,
    on="loan_id",
    how="left"
)

loan_portfolio["instalments_due"] = (
    loan_portfolio["instalments_due"].fillna(0).astype(int)
)

loan_portfolio["instalments_paid"] = (
    loan_portfolio["instalments_paid"].fillna(0).astype(int)
)

loan_portfolio["outstanding_principal"] = (
    loan_portfolio["outstanding_principal"].fillna(0).round(2)
)

loan_portfolio["days_past_due"] = (
    SNAPSHOT_DATE
    - pd.to_datetime(loan_portfolio["oldest_unpaid_due_date"])
).dt.days.fillna(0).clip(lower=0).astype(int)

loan_portfolio["loan_status"] = np.select(
    [
        loan_portfolio["days_past_due"] > 90,
        loan_portfolio["days_past_due"] > 30,
        (
            (loan_portfolio["instalments_due"] > 0)
            & (
                loan_portfolio["instalments_paid"]
                >= loan_portfolio["instalments_due"]
            )
        )
    ],
    [
        "Default Risk",
        "Delinquent",
        "Repaid"
    ],
    default="Active"
)

loan_portfolio = loan_portfolio.drop(
    columns=["oldest_unpaid_due_date"]
)


# ------------------------------------------------------------
# 7. INJECT SEEDED DATA PROBLEMS
# ------------------------------------------------------------

print("\nInjecting deliberate data-quality problems...")

seeded_issues = []

# ISSUE 1: Duplicate loan records
duplicate_sample = loan_portfolio.sample(
    n=100,
    random_state=SEED
)

loans_dirty = pd.concat(
    [loan_portfolio, duplicate_sample],
    ignore_index=True
)

seeded_issues.append({
    "issue_id": "I001",
    "issue_type": "DUPLICATE_LOAN_ROWS",
    "source": "loan_portfolio",
    "description": "100 existing loan rows were duplicated.",
    "affected_records": 100
})


# ISSUE 2: Missing branch-month in repayment transactions
missing_branch = "BR0101"
missing_month = 4
missing_year = 2025

before_count = len(transactions)

transactions_dirty = transactions[
    ~(
        (transactions["branch_id"] == missing_branch)
        & (
            transactions["payment_date"].dt.month == missing_month
        )
        & (
            transactions["payment_date"].dt.year == missing_year
        )
    )
].copy()

removed_count = before_count - len(transactions_dirty)

seeded_issues.append({
    "issue_id": "I002",
    "issue_type": "MISSING_BRANCH_MONTH",
    "source": "repayment_transactions",
    "description": (
        f"Removed all transactions for branch {missing_branch} "
        f"during {missing_year}-{missing_month:02d}."
    ),
    "affected_records": removed_count
})


# ISSUE 3: Some partner transactions are stored in thousands
partner_indexes = transactions_dirty[
    transactions_dirty["source_system"] == "PARTNER_PORTAL"
].index

unit_error_count = min(
    max(1, int(len(transactions_dirty) * 0.01)),
    len(partner_indexes)
)

unit_error_indexes = rng.choice(
    partner_indexes.to_numpy(),
    size=unit_error_count,
    replace=False
)

transactions_dirty.loc[
    unit_error_indexes, "amount"
] /= 1000

transactions_dirty.loc[
    unit_error_indexes, "amount_unit"
] = "THOUSANDS_INR"

seeded_issues.append({
    "issue_id": "I003",
    "issue_type": "INCONSISTENT_CURRENCY_UNIT",
    "source": "repayment_transactions",
    "description": (
        "Some partner portal amounts were divided by 1000 "
        "and stored in thousands of INR."
    ),
    "affected_records": unit_error_count
})


# ------------------------------------------------------------
# 8. SAVE RAW DATA
# ------------------------------------------------------------

print("\nSaving generated datasets...")

loans_dirty.to_csv(
    RAW_DIR / "loan_portfolio_raw.csv",
    index=False
)

transactions_dirty.to_csv(
    RAW_DIR / "repayment_transactions_raw.csv",
    index=False
)

schedule_df.to_csv(
    RAW_DIR / "installment_schedule_raw.csv",
    index=False
)

pd.DataFrame(seeded_issues).to_csv(
    RAW_DIR / "seeded_issues.csv",
    index=False
)


# ------------------------------------------------------------
# 9. GENERATION SUMMARY
# ------------------------------------------------------------

print("\n" + "=" * 55)
print("FINANCIAL INCLUSION DATA GENERATION COMPLETE")
print("=" * 55)

print("Unique loans:", loan_portfolio["loan_id"].nunique())
print("Raw loan rows:", len(loans_dirty))
print("Installment schedule rows:", len(schedule_df))
print("Raw transaction rows:", len(transactions_dirty))
print("Branches:", len(branch_master))
print("States:", len(STATE_NAMES))

print("\nLoan status distribution:")
print(loan_portfolio["loan_status"].value_counts())

print("\nPayment channel distribution:")
print(transactions_dirty["channel"].value_counts())

print("\nSeeded data problems:")
print(pd.DataFrame(seeded_issues).to_string(index=False))

print("\nFiles saved in:", RAW_DIR)
