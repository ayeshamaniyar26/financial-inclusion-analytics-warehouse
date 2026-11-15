import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))



from datetime import date
from pathlib import Path
from html import escape

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from dashboard.queries import (
    get_filter_options,
    get_portfolio_health,
    get_collection_efficiency,
    get_vintage_curves,
    get_digital_collections,
    get_channel_summary,
    get_data_quality_issues,
)

from dashboard.components import (
    inject_css,
    render_header,
    render_section_title,
    render_kpi_card,
    render_filter_summary,
    render_data_quality_notice,
    render_download_button,
    format_inr,
    style_plotly,
)


# =========================================================
# 1. PAGE CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="Financial Inclusion Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_css()

START_DATE = date(2023, 11, 1)
END_DATE = date(2025, 12, 31)

PAGES = [
    "Portfolio Health",
    "Collection Efficiency",
    "Repayment Vintage",
    "Digital Collections",
    "Data Quality Report",
]

if "nav_page" not in st.session_state:
    st.session_state.nav_page = "Portfolio Health"


# =========================================================
# 2. CONSTANTS AND HELPERS
# =========================================================

PURPLE = "#6846C7"
MIDNIGHT = "#29234D"
LAVENDER = "#EEE9FA"
TEAL = "#269B82"
BLUE = "#5486C8"
AMBER = "#E3A64B"
CORAL = "#D97757"
CRITICAL = "#C34D68"


def number(value):
    """Safely convert a value to float."""
    if value is None or pd.isna(value):
        return 0.0

    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0


def percentage(value):
    """Safely format a percentage."""
    if value is None or pd.isna(value):
        return "N/A"

    return f"{number(value):.2f}%"


def filtered_args(filters):
    """Convert All selections to None for SQL queries."""
    return {
        key: None if filters[key] == "All" else filters[key]
        for key in ("state", "branch", "product", "segment")
    }


def no_data(message):
    st.info(message)


def chart_display(fig, height=380):
    fig = style_plotly(fig, height=height)
    st.plotly_chart(fig, use_container_width=True)


def section_caption(text):
    st.markdown(
        f'<div class="section-caption">{escape(text)}</div>',
        unsafe_allow_html=True,
    )


def download_dataframe(df, filename):
    if df is None or df.empty:
        st.info("No records available for download.")
        return

    render_download_button(
        df,
        filename,
        "↓  Download CSV",
    )


def get_date_filters(filters):
    return {
        **filtered_args(filters),
        "date_from": filters["date_from"],
        "date_to": filters["date_to"],
    }


# =========================================================
# 3. SIDEBAR AND FILTERS
# =========================================================

def render_sidebar():

    st.sidebar.markdown(
        """
        <div style="padding:12px 0 22px 0;">
            <div style="
                font-size:23px;
                font-weight:800;
                color:#FFFFFF;
                letter-spacing:-0.7px;">
                FINANCE<span style="color:#C7B5FF;">IQ</span>
            </div>
            <div style="
                color:#D8CFF0;
                font-size:11px;
                margin-top:4px;">
                Financial Inclusion Intelligence
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.sidebar.markdown(
        '<div class="filter-caption">NAVIGATION</div>',
        unsafe_allow_html=True,
    )

    # The radio widget owns nav_page. Streamlit applies its value before
    # rerunning the script, so navigation changes on the first interaction.
    page = st.sidebar.radio(
        "Dashboard pages",
        PAGES,
        key="nav_page",
        label_visibility="collapsed",
    )

    st.sidebar.divider()

    st.sidebar.markdown(
        '<div class="filter-caption">PORTFOLIO FILTERS</div>',
        unsafe_allow_html=True,
    )


    options = get_filter_options()

    state = st.sidebar.selectbox(
        "State",
        ["All"] + options["states"],
        key="state_filter",
    )

    branch_df = options["branches"]

    if state != "All":
        branch_df = branch_df[
            branch_df["state"] == state
        ]

    branch_map = {
        row["branch_id"]: (
            f'{row["branch_name"]} ({row["branch_id"]})'
        )
        for _, row in branch_df.iterrows()
    }

    branch_ids = ["All"] + sorted(branch_map.keys())

    branch = st.sidebar.selectbox(
        "Branch",
        branch_ids,
        format_func=lambda value: (
            "All branches"
            if value == "All"
            else branch_map[value]
        ),
        key=f"branch_filter_{state}",
    )

    product = st.sidebar.selectbox(
        "Loan Product",
        ["All"] + options["products"],
        key="product_filter",
    )

    segment = st.sidebar.selectbox(
        "Borrower Segment",
        ["All"] + options["segments"],
        key="segment_filter",
    )

    st.sidebar.divider()

    st.sidebar.markdown(
        '<div class="filter-caption">ANALYTICS PERIOD</div>',
        unsafe_allow_html=True,
    )

    selected_dates = st.sidebar.date_input(
        "Date range",
        value=(START_DATE, END_DATE),
        min_value=START_DATE,
        max_value=END_DATE,
        format="DD/MM/YYYY",
        key="analytics_date_range",
    )

    # Streamlit returns a single date while the user is selecting
    # the first endpoint of a date range. Keep that date as a
    # temporary one-day range instead of silently resetting to all data.
    if isinstance(selected_dates, (tuple, list)) and len(selected_dates) == 2:
        date_from, date_to = selected_dates
    elif isinstance(selected_dates, (tuple, list)) and len(selected_dates) == 1:
        # Streamlit may return a one-item tuple while the range is being selected.
        date_from = date_to = selected_dates[0]
    elif isinstance(selected_dates, date):
        date_from = date_to = selected_dates
    else:
        date_from, date_to = START_DATE, END_DATE

    if date_from > date_to:
        st.sidebar.error(
            "Start date cannot be after end date."
        )
        date_from, date_to = START_DATE, END_DATE

    st.sidebar.caption(
        "Applies to due-date, vintage-cohort and payment-date analytics. "
        "Portfolio Health remains fixed at 31 Dec 2025."
    )

    st.sidebar.divider()

    st.sidebar.markdown(
        """
        <div style="
            font-size:11px;
            color:#8B879B;
            line-height:1.7;">
            <b style="color:#6846C7;">DATASET</b><br>
            50,000 synthetic loans<br>
            8 states · 32 branches<br>
            Reporting currency: INR<br>
            Snapshot: 31 Dec 2025
        </div>
        """,
        unsafe_allow_html=True,
    )

    return {
        "page": page,
        "state": state,
        "branch": branch,
        "product": product,
        "segment": segment,
        "date_from": date_from,
        "date_to": date_to,
    }


# =========================================================
# 4. PAGE HEADER
# =========================================================

def render_page_heading(title, subtitle):

    st.markdown(
        f"""
        <div style="margin-bottom:22px;">
            <div style="
                color:#29234D;
                font-size:25px;
                font-weight:800;
                letter-spacing:-0.7px;">
                {escape(title)}
            </div>
            <div style="
                color:#77738A;
                font-size:13px;
                margin-top:6px;">
                {escape(subtitle)}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# 5. PORTFOLIO HEALTH
# =========================================================

def show_portfolio_health(filters):

    render_page_heading(
        "Portfolio Health",
        "Monitor loan exposure, outstanding principal "
        "and portfolio risk.",
    )

    df = get_portfolio_health(**filtered_args(filters))

    if df.empty:
        no_data("No portfolio records found.")
        return

    row = df.iloc[0]

    total_loans = int(number(row["total_loans"]))
    disbursed = number(row["total_disbursed_amount_inr"])
    outstanding = number(
        row["total_outstanding_principal_inr"]
    )

    par30 = row["par30_pct"]
    par90 = row["par90_pct"]

    loans_30 = int(number(row["loans_dpd_30_or_more"]))
    loans_90 = int(number(row["loans_dpd_90_or_more"]))

    st.markdown(
        '<div class="section-heading">Portfolio Overview</div>',
        unsafe_allow_html=True,
    )

    # Seven unique KPIs arranged as 4 + 3 cards; no repeated PAR/DPD metrics.
    cards = [
        ("TOTAL LOANS", f"{total_loans:,}", "Loans in fixed snapshot", PURPLE),
        ("TOTAL DISBURSED", format_inr(disbursed, compact=True), "Original disbursed amount", BLUE),
        ("OUTSTANDING PRINCIPAL", format_inr(outstanding, compact=True), "As of 31 Dec 2025", TEAL),
        ("PAR30", percentage(par30), "Outstanding principal · DPD ≥ 30", CRITICAL),
        ("PAR90", percentage(par90), "Outstanding principal · DPD ≥ 90", CORAL),
        ("LOANS WITH DPD ≥ 30", f"{loans_30:,}", "Overdue by at least 30 days", AMBER),
        ("LOANS WITH DPD ≥ 90", f"{loans_90:,}", "Overdue by at least 90 days", CRITICAL),
    ]
    first_row = st.columns(4, gap="medium")
    for col, card in zip(first_row, cards[:4]):
        with col:
            render_kpi_card(*card)

    second_row = st.columns(3, gap="medium")
    for col, card in zip(second_row, cards[4:]):
        with col:
            render_kpi_card(*card)

    st.write("\n")

    # Risk distribution
    render_section_title(
        "Portfolio Risk Distribution",
        "Distribution of loans according to days past due.",
    )

    risk_df = pd.DataFrame({
        "Risk Category": [
            "DPD below 30",
            "DPD 30–89",
            "DPD 90 or more",
        ],
        "Loans": [
            max(total_loans - loans_30, 0),
            max(loans_30 - loans_90, 0),
            loans_90,
        ],
    })

    if total_loans > 0:

        fig = px.pie(
            risk_df,
            names="Risk Category",
            values="Loans",
            hole=0.65,
            color="Risk Category",
            color_discrete_map={
                "DPD below 30": TEAL,
                "DPD 30–89": AMBER,
                "DPD 90 or more": CRITICAL,
            },
        )

        fig.update_traces(
            textposition="inside",
            textinfo="percent",
            hovertemplate=(
                "<b>%{label}</b><br>"
                "Loans: %{value:,}<br>"
                "Share: %{percent}<extra></extra>"
            ),
        )

        fig.add_annotation(
            text=(
                f"<b>{total_loans:,}</b>"
                "<br><sup>Total loans</sup>"
            ),
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=18, color=MIDNIGHT),
        )

        chart_display(fig, 390)

    else:
        no_data("Risk distribution is unavailable.")

    with st.expander("Portfolio KPI definitions", expanded=False):
        st.markdown(
            """
            <div class="method-grid">
              <div class="method-card">
                <div class="method-icon">◈</div>
                <div class="method-card-title">PAR30</div>
                <div class="method-card-copy">Share of outstanding principal attached to loans at least 30 days past due.</div>
                <div class="formula-box">PAR30 = (Outstanding principal with DPD ≥ 30 ÷ Total outstanding principal) × 100</div>
              </div>
              <div class="method-card">
                <div class="method-icon">◉</div>
                <div class="method-card-title">PAR90</div>
                <div class="method-card-copy">Share of outstanding principal attached to loans at least 90 days past due.</div>
                <div class="formula-box">PAR90 = (Outstanding principal with DPD ≥ 90 ÷ Total outstanding principal) × 100</div>
              </div>
              <div class="method-card">
                <div class="method-icon">◷</div>
                <div class="method-card-title">DPD — Days Past Due</div>
                <div class="method-card-copy">The number of days a scheduled loan payment is overdue. DPD is used to classify portfolio delinquency.</div>
              </div>
            </div>
            <div class="snapshot-callout"><b>◷ Fixed reporting snapshot · 31 December 2025</b><span>Portfolio health measures use the single loan snapshot available in this warehouse. The analytics date filter does not change these snapshot KPIs.</span></div>
            """,
            unsafe_allow_html=True,
        )

    download_dataframe(df, "portfolio_health.csv")


# =========================================================
# 6. COLLECTION EFFICIENCY
# =========================================================

def show_collection_efficiency(filters):

    render_page_heading(
        "Collection Efficiency",
        "Compare scheduled collection performance "
        "across states and branches.",
    )

    df = get_collection_efficiency(
        **get_date_filters(filters)
    )

    if df.empty:
        no_data("No collection records found for the selected filters.")
        return

    total_due = number(df["total_amount_due_inr"].sum())
    total_paid = number(
        df["scheduled_amount_paid_inr"].sum()
    )

    total_instalments = int(df["instalments_due"].sum())
    paid_instalments = int(df["instalments_paid"].sum())

    efficiency = (
        total_paid / total_due * 100
        if total_due > 0 else 0
    )

    cols = st.columns(4)

    cards = [
        (
            "COLLECTION EFFICIENCY",
            f"{efficiency:.2f}%",
            "Paid proxy ÷ scheduled due",
            PURPLE,
        ),
        (
            "AMOUNT DUE",
            format_inr(total_due, compact=True),
            "Selected due-date period",
            BLUE,
        ),
        (
            "AMOUNT PAID",
            format_inr(total_paid, compact=True),
            "Schedule-based paid proxy",
            TEAL,
        ),
        (
            "INSTALMENTS PAID",
            f"{paid_instalments:,}",
            f"Out of {total_instalments:,} due",
            AMBER,
        ),
    ]

    for col, card in zip(cols, cards):
        with col:
            render_kpi_card(*card)

    st.write("")

    # Aggregate state data using amounts, not average percentages.
    state_df = (
        df.groupby("state", as_index=False)
        .agg(
            total_amount_due_inr=(
                "total_amount_due_inr", "sum"
            ),
            scheduled_amount_paid_inr=(
                "scheduled_amount_paid_inr", "sum"
            ),
        )
    )

    state_df["collection_efficiency_pct"] = (
        state_df["scheduled_amount_paid_inr"]
        / state_df["total_amount_due_inr"].replace(0, pd.NA)
        * 100
    )

    render_section_title(
        "Collection Efficiency by State",
        "Weighted efficiency calculated from total amounts.",
    )

    state_df = state_df.sort_values(
        "collection_efficiency_pct"
    )

    fig = px.bar(
        state_df,
        x="collection_efficiency_pct",
        y="state",
        orientation="h",
        text="collection_efficiency_pct",
        color="collection_efficiency_pct",
        color_continuous_scale=[
            "#EEE9FA",
            "#B6A1E9",
            PURPLE,
        ],
        labels={
            "state": "State",
            "collection_efficiency_pct": "Efficiency (%)",
        },
    )

    fig.update_traces(
        texttemplate="%{text:.2f}%",
        textposition="outside",
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Efficiency: %{x:.2f}%<extra></extra>"
        ),
    )

    fig.update_layout(coloraxis_showscale=False)

    # State and branch analytics sit side-by-side on wide screens.
    state_chart_col, branch_chart_col = st.columns([0.95, 1.35], gap="large")
    with state_chart_col:
        chart_display(fig, 410)

    # Branch comparison
    with branch_chart_col:
        render_section_title(
            "Branch-level Performance",
            "Compare collection efficiency across individual branches.",
        )

    branch_df = df.sort_values(
        "collection_efficiency_pct",
        ascending=False,
    )

    fig = px.bar(
        branch_df,
        x="branch_name",
        y="collection_efficiency_pct",
        color="state",
        hover_data=[
            "branch_id",
            "total_amount_due_inr",
            "scheduled_amount_paid_inr",
            "instalments_due",
            "instalments_paid",
        ],
        labels={
            "branch_name": "Branch",
            "collection_efficiency_pct": "Efficiency (%)",
        },
    )

    fig.update_layout(xaxis_tickangle=-35)

    with branch_chart_col:
        chart_display(fig, 410)

    with st.expander("Collection Efficiency Methodology", expanded=False):
        st.markdown(
            """
            <div class="method-grid">
              <div class="method-card method-card-wide">
                <div class="method-icon">◷</div>
                <div class="method-card-title">How collection efficiency is calculated</div>
                <div class="formula-box formula-large">Collection Efficiency = (Scheduled Amount Paid Proxy / Scheduled Amount Due) × 100</div>
                <ul class="method-points">
                  <li>Due amount is aggregated from the installment schedule for the selected due-date period.</li>
                  <li>Paid amount comes from the installment schedule's paid-status proxy.</li>
                  <li>State and branch results are calculated from aggregated amounts, not an average of branch percentages.</li>
                </ul>
              </div>
            </div>
            <div class="method-warning"><b>⚠ Measurement limitation</b><span>This is not a fully reconciled cash collection measure. Repayment transactions do not contain an installment-level matching key, so cash transactions cannot be reliably matched to individual scheduled installments.</span></div>
            """,
            unsafe_allow_html=True,
        )

    download_dataframe(
        df,
        "collection_efficiency_by_branch.csv",
    )


# =========================================================
# 7. REPAYMENT VINTAGE
# =========================================================

def show_repayment_vintage(filters):

    render_page_heading(
        "Repayment Vintage Analysis",
        "Understand cumulative collection performance "
        "for different loan disbursement cohorts.",
    )

    df = get_vintage_curves(
        **get_date_filters(filters)
    )

    if df.empty:
        no_data("No vintage records found for these filters.")
        return

    df["vintage_month"] = pd.to_datetime(
        df["vintage_month"]
    )

    df["cohort"] = df["vintage_month"].dt.strftime(
        "%b %Y"
    )

    cohorts = sorted(
        df["cohort"].unique(),
        key=lambda value: pd.to_datetime(value, format="%b %Y"),
    )

    default_cohorts = cohorts[-min(6, len(cohorts)):]

    selected = st.multiselect(
        "Compare vintage cohorts",
        options=cohorts,
        default=default_cohorts,
        key="vintage_cohort_selection",
    )

    chart_df = df[df["cohort"].isin(selected)].copy()

    if chart_df.empty:
        no_data("Select at least one vintage cohort to display.")
        return

    render_section_title(
        "Cumulative Collection Curves",
        "Each line represents loans disbursed in the same month.",
    )

    fig = px.line(
        chart_df,
        x="vintage_age_month",
        y="cumulative_collection_pct",
        color="cohort",
        markers=True,
        labels={
            "vintage_age_month": "Vintage age (installment number)",
            "cumulative_collection_pct": "Cumulative collection (%)",
            "cohort": "Vintage cohort",
        },
    )

    fig.update_traces(
        line=dict(width=2.5),
        hovertemplate=(
            "<b>%{fullData.name}</b><br>"
            "Installment age: %{x}<br>"
            "Cumulative collection: %{y:.2f}%"
            "<extra></extra>"
        ),
    )

    fig.update_yaxes(
        ticksuffix="%",
        rangemode="tozero",
    )

    chart_display(fig, 480)

    render_section_title("Vintage Data")

    st.dataframe(
        chart_df[
            [
                "vintage_month",
                "vintage_age_month",
                "cumulative_amount_due_inr",
                "cumulative_amount_paid_proxy_inr",
                "cumulative_collection_pct",
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )

    download_dataframe(
        chart_df,
        "repayment_vintage_curves.csv",
    )

    with st.expander("Vintage Analysis Methodology", expanded=False):
        st.markdown(
            """
            <div class="method-grid">
              <div class="method-card method-card-wide">
                <div class="method-icon">⌁</div>
                <div class="method-card-title">How vintage curves are built</div>
                <div class="formula-box formula-large">Cumulative Collection % = (Cumulative Scheduled Paid Proxy / Cumulative Scheduled Amount Due) × 100</div>
                <ul class="method-points">
                  <li>A <b>vintage</b> is a group of loans disbursed in the same month.</li>
                  <li><b>Vintage age</b> is represented by the installment sequence.</li>
                  <li>Amounts are accumulated across installment ages within each disbursement-month cohort.</li>
                </ul>
              </div>
            </div>
            <div class="method-warning"><b>⚠ Measurement limitation</b><span>This analysis uses the installment schedule. It must not be interpreted as transaction-level cash reconciliation because transactions do not have an installment-level matching key.</span></div>
            """,
            unsafe_allow_html=True,
        )


# =========================================================
# 8. DIGITAL COLLECTIONS
# =========================================================

def show_digital_collections(filters):

    render_page_heading(
        "Digital Collections",
        "Track the adoption and growth of digital repayment channels.",
    )

    df = get_digital_collections(
        **get_date_filters(filters)
    )

    if df.empty:
        no_data("No digital collection records found.")
        return

    df = df.copy()

    df["payment_month"] = pd.to_datetime(
        df["payment_month"]
    )

    df = df.sort_values("payment_month")

    latest = df.iloc[-1]

    cols = st.columns(4)

    cards = [
        (
            "DIGITAL SHARE BY COUNT",
            percentage(latest["digital_share_count_pct"]),
            "Latest month",
            PURPLE,
        ),
        (
            "DIGITAL SHARE BY VALUE",
            percentage(latest["digital_share_value_pct"]),
            "Normalized INR value share",
            TEAL,
        ),
        (
            "DIGITAL TRANSACTIONS",
            f'{int(number(latest["digital_transactions"])):,}',
            "Latest month",
            BLUE,
        ),
        (
            "DIGITAL COLLECTION VALUE",
            format_inr(
                latest["digital_collections_inr"],
                compact=True,
            ),
            "Latest month",
            AMBER,
        ),
    ]

    for col, card in zip(cols, cards):
        with col:
            render_kpi_card(*card)

    st.write("")

    # Digital adoption
    render_section_title(
        "Digital Adoption Trend",
        "Compare digital payment share by transaction count and value.",
    )

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df["payment_month"],
            y=df["digital_share_count_pct"],
            mode="lines+markers",
            name="Share by count",
            line=dict(color=PURPLE, width=3),
        )
    )

    fig.add_trace(
        go.Scatter(
            x=df["payment_month"],
            y=df["digital_share_value_pct"],
            mode="lines+markers",
            name="Share by value",
            line=dict(color=TEAL, width=3),
        )
    )

    fig.update_yaxes(
        title="Digital share (%)",
        ticksuffix="%",
    )

    digital_trend_col, digital_value_col = st.columns(2, gap="large")
    with digital_trend_col:
        chart_display(fig, 390)

    # Digital collections value
    with digital_value_col:
        render_section_title(
            "Digital Collections Value",
            "Monthly normalized INR value collected through digital channels.",
        )

    fig = px.area(
        df,
        x="payment_month",
        y="digital_collections_inr",
        labels={
            "payment_month": "Payment month",
            "digital_collections_inr": "Digital collections (INR)",
        },
    )

    fig.update_traces(
        line=dict(color=PURPLE, width=2.5),
        fillcolor="rgba(104,70,199,0.13)",
        hovertemplate=(
            "Month: %{x|%b %Y}<br>"
            "Digital value: ₹%{y:,.2f}<extra></extra>"
        ),
    )

    with digital_value_col:
        chart_display(fig, 390)

    # Growth metrics
    render_section_title(
        "Digital Growth",
        "Month-on-month and year-on-year changes in digital collection value.",
    )

    growth_cols = st.columns(2)

    with growth_cols[0]:
        mom = latest["digital_value_mom_growth_pct"]

        render_kpi_card(
            "MONTH-ON-MONTH GROWTH",
            percentage(mom),
            "Compared with previous month",
            BLUE,
        )

    with growth_cols[1]:
        yoy = latest["digital_value_yoy_growth_pct"]

        render_kpi_card(
            "YEAR-ON-YEAR GROWTH",
            percentage(yoy),
            "Compared with same month last year",
            TEAL,
        )

    # Channel analysis
    channel_df = get_channel_summary(
        **get_date_filters(filters)
    )

    if not channel_df.empty:

        render_section_title(
            "Average Payment Size by Channel",
            "Average transaction amount after INR unit normalization.",
        )

        fig = px.bar(
            channel_df,
            x="channel",
            y="average_payment_size_inr",
            color="channel",
            text="average_payment_size_inr",
            color_discrete_sequence=[
                PURPLE,
                TEAL,
                BLUE,
            ],
            labels={
                "channel": "Payment channel",
                "average_payment_size_inr": "Average payment size (INR)",
            },
        )

        fig.update_traces(
            texttemplate="₹%{text:,.0f}",
            textposition="outside",
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Average payment: ₹%{y:,.2f}<extra></extra>"
            ),
        )

        chart_display(fig, 370)

        st.dataframe(
            channel_df,
            use_container_width=True,
            hide_index=True,
        )

        download_dataframe(
            channel_df,
            "average_payment_size_by_channel.csv",
        )

    render_section_title("Monthly Collection Details")

    monthly_display = df.copy()
    # Display YYYY-MM explicitly so the month and growth columns remain
    # compact and visible in the table without horizontal scrolling.
    monthly_display["payment_month"] = pd.to_datetime(
        monthly_display["payment_month"]
    ).dt.strftime("%Y-%m")
    monthly_order = [
        "payment_month",
        "digital_value_mom_growth_pct",
        "digital_value_yoy_growth_pct",
        "digital_share_count_pct",
        "digital_share_value_pct",
        "total_transactions",
        "digital_transactions",
        "total_collections_inr",
        "digital_collections_inr",
    ]
    monthly_display = monthly_display[
        [column for column in monthly_order if column in monthly_display.columns]
    ]
    st.dataframe(
        monthly_display,
        width="stretch",
        hide_index=True,
        column_config={
            "payment_month": st.column_config.TextColumn(
                "Payment month", width="small"
            ),
            "digital_value_mom_growth_pct": st.column_config.NumberColumn(
                "Digital value MoM", format="%.2f%%", width="small"
            ),
            "digital_value_yoy_growth_pct": st.column_config.NumberColumn(
                "Digital value YoY", format="%.2f%%", width="small"
            ),
            "digital_share_count_pct": st.column_config.NumberColumn(
                "Digital share (count)", format="%.2f%%", width="small"
            ),
            "digital_share_value_pct": st.column_config.NumberColumn(
                "Digital share (value)", format="%.2f%%", width="small"
            ),
            "total_transactions": st.column_config.NumberColumn(
                "Transactions", format="%d", width="small"
            ),
            "digital_transactions": st.column_config.NumberColumn(
                "Digital txns", format="%d", width="small"
            ),
            "total_collections_inr": st.column_config.NumberColumn(
                "Total collections (INR)", format="₹%.2f", width="medium"
            ),
            "digital_collections_inr": st.column_config.NumberColumn(
                "Digital collections (INR)", format="₹%.2f", width="medium"
            ),
        },
    )

    download_dataframe(
        df,
        "digital_collections_monthly.csv",
    )

    with st.expander("Digital collection KPI definitions"):

        st.markdown(
            """
            **Digital share by count**

            Digital transactions / Total transactions × 100.

            **Digital share by value**

            Digital transaction value / Total transaction value × 100.

            **MoM growth**

            Change in digital collection value compared with
            the previous month.

            **YoY growth**

            Change in digital collection value compared with
            the same month in the previous year.

            Transaction amounts are normalized to INR before
            these calculations.
            """
        )


# =========================================================
# 9. DATA QUALITY REPORT
# =========================================================

DQ_MAPPING = {

    "I001": {
        "table": (
            "raw_loan_portfolio → clean_loan_portfolio"
        ),
        "detection": [
            "test_raw_loan_duplicates_are_detectable",
        ],
        "resolution": [
            "test_clean_loan_ids_are_unique",
        ],
        "status": "Resolved in clean layer",
        "treatment": (
            "Duplicate loan rows were removed using SELECT DISTINCT. "
            "The clean loan portfolio contains 50,000 unique loan IDs."
        ),
    },

    "I002": {
        "table": (
            "raw_repayment_transactions → "
            "clean_repayment_transactions"
        ),
        "detection": [
            "test_raw_missing_branch_month_is_detectable",
        ],
        "resolution": [],
        "status": "Detected and documented",
        "treatment": (
            "Transactions for BR0101 during April 2025 were missing. "
            "The 769 absent transactions were not imputed because "
            "fabricating financial activity would distort the data."
        ),
    },

    "I003": {
        "table": (
            "raw_repayment_transactions → "
            "clean_repayment_transactions"
        ),
        "detection": [
            "test_raw_transaction_unit_issue_is_present",
            "test_raw_data_contains_expected_amount_units",
        ],
        "resolution": [
            "test_inr_amounts_are_normalized_correctly",
            "test_thousands_inr_amounts_are_normalized_correctly",
            "test_clean_transactions_have_no_unknown_units",
        ],
        "status": "Resolved in clean layer",
        "treatment": (
            "Partner portal amounts stored in THOUSANDS_INR "
            "were multiplied by 1,000 to obtain normalized INR values."
        ),
    },
}


def show_data_quality_report():

    render_page_heading(
        "Data Quality Report",
        "Track seeded data issues, affected records, detection "
        "tests and cleaning treatments.",
    )

    issues = get_data_quality_issues()

    if issues.empty:
        no_data("No issue records found in the issue manifest.")
        return

    total_issues = len(issues)

    total_affected = int(
        issues["affected_records"].sum()
    )

    resolved = sum(
        1
        for issue_id in issues["issue_id"]
        if DQ_MAPPING.get(issue_id, {}).get("resolution")
    )

    cols = st.columns(3)

    cards = [
        (
            "IDENTIFIED ISSUES",
            str(total_issues),
            "Seeded data-quality issues",
            PURPLE,
        ),
        (
            "AFFECTED RECORDS",
            f"{total_affected:,}",
            "Across all seeded issues",
            CORAL,
        ),
        (
            "RESOLVED IN CLEAN LAYER",
            f"{resolved}/{total_issues}",
            "Missing month is documented, not imputed",
            TEAL,
        ),
    ]

    for col, card in zip(cols, cards):
        with col:
            render_kpi_card(*card)

    st.write("")

    st.markdown(
        """
        <div class="method-warning"><b>⚠ Data-quality interpretation</b><span>The seeded issue manifest records the original defects. Resolution status describes the cleaning treatment; it does not imply that missing financial transactions were reconstructed.</span></div>
        """,
        unsafe_allow_html=True,
    )

    # Detailed issue cards
    render_section_title(
        "Issue Investigation",
        "Expand each issue to inspect its affected tables and tests.",
    )

    for _, issue in issues.iterrows():

        issue_id = issue["issue_id"]
        mapping = DQ_MAPPING.get(issue_id, {})

        status = mapping.get(
            "status",
            "Review required",
        )

        with st.expander(
            f'{issue_id}  ·  {issue["issue_type"].replace("_", " ").title()}  ·  {int(issue["affected_records"]):,} records',
            expanded=False,
        ):
            status_class = (
                "status-resolved"
                if status == "Resolved in clean layer"
                else "status-documented"
            )
            st.markdown(
                f"""
                <div class="issue-detail-card">
                  <div class="issue-detail-top">
                    <span class="issue-id">{escape(str(issue_id))}</span>
                    <span class="{status_class}">{escape(status)}</span>
                  </div>
                  <div class="issue-detail-grid">
                    <div><span class="issue-field-label">ISSUE DESCRIPTION</span><p>{escape(str(issue["description"]))}</p></div>
                    <div><span class="issue-field-label">SOURCE</span><p>{escape(str(issue["source"]))}</p></div>
                    <div><span class="issue-field-label">AFFECTED TABLES</span><p class="issue-table-path">{escape(str(mapping.get("table", issue["source"])))}</p></div>
                    <div><span class="issue-field-label">AFFECTED RECORD COUNT</span><p class="issue-record-count">{int(issue["affected_records"]):,}</p></div>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.markdown("**Detection tests**")

            detection_tests = mapping.get(
                "detection", []
            )

            for test in detection_tests:
                st.code(test, language="text")

            st.markdown("**Resolution validation tests**")

            resolution_tests = mapping.get(
                "resolution", []
            )

            if resolution_tests:
                for test in resolution_tests:
                    st.code(test, language="text")
            else:
                st.caption(
                    "No resolution test: this missing-data issue "
                    "is intentionally preserved and documented."
                )

            st.markdown("**Cleaning treatment**")
            st.write(
                mapping.get(
                    "treatment",
                    "No treatment information available.",
                )
            )

    # Issue register
    render_section_title(
        "Data Quality Issue Register",
        "Downloadable summary of the seeded data-quality issues.",
    )

    report = issues.copy()

    report["affected_table"] = report["issue_id"].map(
        lambda issue_id: DQ_MAPPING.get(
            issue_id, {}
        ).get("table", "Not mapped")
    )

    report["status"] = report["issue_id"].map(
        lambda issue_id: DQ_MAPPING.get(
            issue_id, {}
        ).get("status", "Review required")
    )

    st.dataframe(
        report,
        use_container_width=True,
        hide_index=True,
    )

    download_dataframe(
        report,
        "data_quality_report.csv",
    )


# =========================================================
# 10. MAIN APPLICATION
# =========================================================

def main():

    filters = render_sidebar()

    render_header()

    render_filter_summary(
        filters["state"],
        filters["branch"],
        filters["product"],
        filters["segment"],
    )

    page = filters["page"]

    if page == "Portfolio Health":
        show_portfolio_health(filters)

    elif page == "Collection Efficiency":
        show_collection_efficiency(filters)

    elif page == "Repayment Vintage":
        show_repayment_vintage(filters)

    elif page == "Digital Collections":
        show_digital_collections(filters)

    elif page == "Data Quality Report":
        show_data_quality_report()

    st.divider()

    st.markdown(
        """
        <div style="
            display:flex;
            justify-content:space-between;
            flex-wrap:wrap;
            gap:10px;
            color:#8B879B;
            font-size:11px;
            padding:5px 0 12px 0;">
            <span>Financial Inclusion Analytics Warehouse</span>
            <span>INR · Synthetic Dataset · Snapshot: 31 Dec 2025</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    render_data_quality_notice()


if __name__ == "__main__":
    main()
