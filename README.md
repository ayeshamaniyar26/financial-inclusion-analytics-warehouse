
# Financial Inclusion Analytics Warehouse

## Task 10 – Financial Inclusion Analytics

## 1. Project Overview

The **Financial Inclusion Analytics Warehouse** is a data analytics solution designed to help financial institutions monitor loan portfolios, evaluate repayment and collection performance, analyse borrower and loan trends, and identify data-quality issues.

The project transforms raw financial data into a structured analytical warehouse and provides an interactive dashboard using Streamlit and Plotly.

The dashboard enables users to explore financial performance through key performance indicators (KPIs), visualisations, filters and data-quality reports.

The primary goal is to convert raw financial data into meaningful business insights that support better lending, collection and portfolio-risk decisions.

---

## 2. Problem Statement

Financial institutions generate large volumes of loan, repayment and transaction data. Analysing this information directly from raw datasets can be difficult because of duplicate records, missing transactions, inconsistent values and different transaction-value units.

Without a structured analytics system, it becomes challenging to:

- Monitor overall loan portfolio health.
- Identify loans with delayed repayments.
- Evaluate collection efficiency.
- Compare repayment performance across loan cohorts.
- Analyse branch, state, product and borrower-segment performance.
- Identify and monitor data-quality problems.

The objective of this project is to develop a Financial Inclusion Analytics Warehouse that cleans and organises financial data, calculates important business KPIs and presents the results through an interactive dashboard.

---

## 3. Project Objectives

- Generate and process realistic synthetic financial datasets.
- Identify and handle data-quality issues.
- Perform data cleaning, validation and standardisation.
- Design a data warehouse using dimensional modelling.
- Implement a Star Schema with fact and dimension tables.
- Develop SQL queries for analytical calculations.
- Calculate important financial and portfolio KPIs.
- Analyse collection efficiency and vintage performance.
- Develop an interactive dashboard using Streamlit and Plotly.
- Provide data-quality reports for monitoring identified issues.
- Validate the implementation using automated tests.

---

## 4. Technologies Used

| Technology | Purpose |
|---|---|
| Python | Data processing and application development |
| Pandas | Data manipulation and cleaning |
| NumPy | Numerical operations and synthetic data generation |
| DuckDB | Analytical database and data warehouse |
| SQL | Data transformation and analytical queries |
| Streamlit | Interactive dashboard development |
| Plotly | Interactive charts and data visualisation |
| Pytest | Automated testing and validation |

---

## 5. Dataset Description

The project uses synthetically generated financial data to simulate a loan portfolio.

### Dataset Overview

- **50,000 loan records**
- **8 states**
- **32 branches**
- Loan and borrower information
- Loan portfolio snapshot data
- Installment and repayment schedules
- Transaction records

### Data Period

- Start date: 1 January 2024
- End date: 31 December 2025
- Portfolio snapshot date: 31 December 2025

The synthetic dataset is generated using a fixed random seed to support reproducibility.

Synthetic data allows the project to demonstrate realistic financial analytics and data-quality scenarios without exposing actual customer financial information.

---

## 6. Data Engineering and Cleaning

The raw datasets contain three deliberately introduced data-quality issues to simulate real-world financial data challenges.

### 6.1 Seeded Data-Quality Issues

| No. | Data-quality issue | Records affected | Treatment |
|---|---|---:|---|
| 1 | Duplicate loan records | 100 | Identified and handled during cleaning |
| 2 | Missing transactions for branch BR0101 in April 2025 | 769 | Preserved and documented as a data-quality issue |
| 3 | Transaction values stored in THOUSANDS_INR | 4,286 | Normalised into INR by multiplying by 1,000 |

### 6.2 Issue Details

**Issue 1: Duplicate Loan Records**

A total of 100 duplicate loan records were deliberately introduced into the raw loan dataset.

These records were identified during data validation and handled during the cleaning process to prevent duplicate counting and incorrect portfolio calculations.

**Issue 2: Missing Transactions**

A total of 769 transaction records are missing for branch BR0101 in April 2025.

The issue is documented in the data-quality report. Missing transactions are not artificially generated or assumed to represent confirmed zero-value payments.

**Issue 3: Transaction Unit Inconsistency**

A total of 4,286 transaction records contain values represented in THOUSANDS_INR instead of INR.

These values are converted into standard INR by multiplying the original values by 1,000.

This ensures consistent transaction-value calculations and avoids incorrect financial reporting.

### 6.3 Data Cleaning Approach

The data preparation process focuses on:

- Identifying duplicate records.
- Handling missing and inconsistent values.
- Standardising transaction units.
- Validating cleaned datasets.
- Maintaining visibility of unresolved data-quality issues.
- Preparing consistent datasets for warehouse loading.

The project distinguishes between issues that can be corrected and issues that must remain documented for business users.

---

## 7. Data Warehouse Design

A dimensional modelling approach is used to organise financial data for efficient analytical querying.

The warehouse follows a **Star Schema** design.

### 7.1 Dimension Tables

| Dimension Table | Description |
|---|---|
| dim_date | Date-related attributes used for time-based analysis |
| dim_branch | Branch and geographical information |
| dim_product | Loan product information |
| dim_segment | Borrower segment information |
| dim_loan | Loan and borrower-related attributes |

### 7.2 Fact Tables

| Fact Table | Description |
|---|---|
| fact_snapshot | Loan portfolio snapshot information |
| fact_installment | Scheduled installment information |
| fact_transaction | Payment and transaction information |

### 7.3 Warehouse Design Approach

- Fact tables store measurable business events and financial values.
- Dimension tables provide descriptive attributes for analytical filtering.
- Relationships between fact and dimension tables support multidimensional analysis.
- The Star Schema simplifies analytical queries and dashboard reporting.

This design supports analysis across dates, branches, products, loan records and borrower segments.

---

## 8. Dashboard Features

The project provides an interactive dashboard developed using Streamlit and Plotly.

### 8.1 Portfolio Health

Provides an overview of the loan portfolio through important financial KPIs.

The dashboard displays:

- Total number of loans.
- Total disbursed amount.
- Outstanding principal.
- PAR30 outstanding.
- PAR90 outstanding.
- PAR30 percentage.
- PAR90 percentage.
- Number of loans with DPD greater than or equal to 30 days.
- Number of loans with DPD greater than or equal to 90 days.

Portfolio Health uses the fixed snapshot date of 31 December 2025.

### 8.2 Collection Efficiency

Analyses collection performance using scheduled installment amounts and payment information.

It helps evaluate repayment performance across selected:

- Dates.
- States and branches.
- Loan products.
- Borrower segments.

The analysis uses a schedule-based payment proxy rather than complete transaction-to-installment reconciliation.

### 8.3 Vintage Analysis

Groups loans into origination cohorts to understand how portfolio performance and repayment behaviour evolve over time.

It helps:

- Compare different loan origination cohorts.
- Understand repayment trends.
- Evaluate portfolio performance over time.
- Identify differences in the performance of loan cohorts.

### 8.4 Digital Collections

Provides insights into transaction and collection patterns.

It supports analysis of:

- Transaction activity.
- Monthly collection trends.
- Payment channel-related patterns.
- Normalised transaction values.
- Month-over-month trends where applicable.

### 8.5 Data Quality Report

Provides visibility into identified data-quality issues.

The report includes:

- Issue type.
- Affected table.
- Number of affected records.
- Description of the issue.
- Detection information.
- Resolution or treatment information.

This helps users understand the reliability and limitations of the underlying data.

### 8.6 Interactive Filters

The dashboard provides interactive filters for:

- State.
- Branch.
- Product.
- Borrower segment.
- Analytics date range.

These filters allow users to explore financial performance from different business perspectives.

The analytics date range applies to relevant due-date, vintage-cohort and payment-date analytics. Portfolio Health remains fixed at 31 December 2025.

---

## 9. Key Business KPIs and Calculation Methodology

The dashboard calculates important financial and operational metrics to evaluate loan portfolio health, repayment performance and collection efficiency.

### 9.1 Portfolio Health KPIs

| KPI | Description | Calculation |
|---|---|---|
| Total Loans | Total number of loans in the portfolio | Count of distinct loan IDs |
| Total Disbursed Amount | Total amount disbursed to borrowers | Sum of disbursed loan amounts |
| Outstanding Principal | Remaining principal amount across loans | Sum of outstanding principal |
| PAR30 Outstanding | Outstanding principal for loans with DPD >= 30 | Sum of outstanding principal where DPD >= 30 |
| PAR90 Outstanding | Outstanding principal for loans with DPD >= 90 | Sum of outstanding principal where DPD >= 90 |
| PAR30 % | Percentage of outstanding portfolio at least 30 days past due | (PAR30 Outstanding / Total Outstanding Principal) * 100 |
| PAR90 % | Percentage of outstanding portfolio at least 90 days past due | (PAR90 Outstanding / Total Outstanding Principal) * 100 |
| Loans with DPD >= 30 | Number of loans at least 30 days past due | Count of distinct loans where DPD >= 30 |
| Loans with DPD >= 90 | Number of loans at least 90 days past due | Count of distinct loans where DPD >= 90 |

**DPD:** Days Past Due.

**Portfolio at Risk (PAR):** Measures the outstanding principal associated with loans that have crossed a specified overdue threshold.

### 9.2 Collection Efficiency

Collection Efficiency measures the proportion of eligible scheduled installment amounts considered paid.

**Formula:**

Collection Efficiency (%) = (Eligible Paid Amount / Eligible Scheduled Amount) * 100

The calculation uses a schedule-based payment proxy.

Individual transactions are not fully matched to individual installments. Therefore, the metric should not be interpreted as a fully cash-reconciled accounting figure.

### 9.3 Vintage Analysis

Vintage analysis groups loans according to their origination period and evaluates repayment performance over time.

It helps compare repayment behaviour between different loan origination cohorts.

### 9.4 Digital Collections

Digital Collections analyses transaction activity and payment trends over time.

It supports analysis of transaction values, payment channels and monthly collection patterns using normalised transaction amounts.

---

## 10. Key Results

The project demonstrates the following outcomes:

- Processing of a synthetic dataset containing 50,000 loans.
- Coverage of 8 states and 32 branches.
- Identification and handling of 100 duplicate loan records.
- Detection and documentation of 769 missing transactions.
- Normalisation of 4,286 transaction records.
- Implementation of a dimensional warehouse using a Star Schema.
- Development of SQL-based financial analytics.
- Calculation and visualisation of portfolio health indicators.
- Implementation of PAR30 and PAR90 metrics.
- Collection efficiency and vintage analysis.
- Digital collection trend analysis.
- Interactive dashboard-based exploration of financial data.
- Data-quality reporting and issue documentation.
- Automated validation using Pytest.

**Testing:** The project previously achieved 36 passing automated tests, including validation of important data-processing and analytical logic. The final code should be tested again before submission.

---

## 11. Assumptions and Limitations

The following assumptions and limitations should be considered when interpreting the dashboard results.

1. **Synthetic Data:** The project uses generated data and does not represent an actual financial institution's customer portfolio.

2. **Fixed Portfolio Snapshot:** Portfolio Health KPIs are calculated using the snapshot date of 31 December 2025. They do not change with the analytics date-range filter.

3. **Collection Efficiency:** Collection efficiency and vintage analysis use a schedule-based payment proxy.

4. **Cash Reconciliation:** Individual transactions are not fully matched to individual installments. Therefore, collection metrics should not be interpreted as fully cash-reconciled accounting figures.

5. **Missing Transactions:** Missing transaction records are documented rather than assumed to represent zero payments.

6. **Transaction Normalisation:** Values recorded in THOUSANDS_INR are converted into INR by multiplying them by 1,000.

7. **Analytical Interpretation:** KPIs and trends are based on the available synthetic data and the assumptions used during data preparation.

These assumptions are important when interpreting results and making business decisions.

---

## 12. Project Structure

The main project components are organised as follows:

```text
Financial-Inclusion-Analytics-Warehouse/
│
├── dashboard/
│   ├── app.py
│   ├── components.py
│   ├── queries.py
│   └── styles.css
│
├── scripts/
│   ├── generate_data.py
│   └── ...
│
├── sql/
│   └── ...
│
├── tests/
│   └── ...
│
├── data/
│   └── ...
│
├── requirements.txt
├── README.md
└── .gitignore
```

The exact contents of the folders may vary according to the final project implementation.

---

## 13. How to Run the Project

### 13.1 Prerequisites

- Python 3.10 or a compatible version.
- pip package manager.
- Git.

### 13.2 Clone the Repository

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd <YOUR_REPOSITORY_NAME>
```

### 13.3 Create a Virtual Environment

For Windows PowerShell:

```powershell
python -m venv .venv
```

### 13.4 Activate the Environment

```powershell
.\.venv\Scripts\Activate.ps1
```

### 13.5 Install Dependencies

```powershell
python -m pip install -r requirements.txt
```

### 13.6 Generate the Dataset

```powershell
python scripts/generate_data.py
```

Run the remaining data preparation, cleaning and warehouse creation scripts in the order specified by the project implementation.

If the required processed data and database are already included, follow the project's existing setup instructions instead of regenerating them.

### 13.7 Launch the Dashboard

```powershell
python -m streamlit run dashboard/app.py
```

The dashboard will be available at:

```text
http://localhost:8501
```

### 13.8 Run Automated Tests

```powershell
python -m pytest -v
```

---

## 14. Conclusion

The Financial Inclusion Analytics Warehouse demonstrates how raw financial data can be transformed into a structured analytical system using data engineering, dimensional modelling, SQL and interactive visualisation.

The project combines data cleaning, warehouse development, business KPI calculation, data-quality monitoring and dashboard development into one integrated solution.

It provides a foundation for understanding loan portfolio health, repayment behaviour, collection performance and data reliability.

The project also demonstrates practical applications of Python, DuckDB, SQL, Streamlit and data analytics in the financial inclusion domain.

---

## 15. Project Information

| Detail | Description |
|---|---|
| Project Name | Financial Inclusion Analytics Warehouse |
| Task Number | 10 |
| Domain | Financial Inclusion and Financial Analytics |
| Programming Language | Python |
| Database | DuckDB |
| Dashboard | Streamlit |
| Visualisation | Plotly |
| Data Processing | Pandas and NumPy |
| Query Language | SQL |
| Testing Framework | Pytest |
| Data Type | Synthetic Financial Data |
| Portfolio Snapshot Date | 31 December 2025 |

