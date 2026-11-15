import streamlit as st
import plotly.graph_objects as go
from pathlib import Path
from html import escape


ROOT_DIR = Path(__file__).resolve().parent


def inject_css():
    """Load the FinSight premium light theme."""
    css_path = ROOT_DIR / "styles.css"
    if css_path.exists():
        css = css_path.read_text(encoding="utf-8-sig")
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def render_header():
    st.markdown(
        """
        <div class="dashboard-header">
            <div class="brand-lockup">
                <div class="brand-mark">✦</div>
                <div>
                    <div class="dashboard-title">FinSight</div>
                    <div class="dashboard-subtitle">Financial Inclusion Analytics</div>
                </div>
            </div>
            <div class="header-right">
                <div class="header-context">PORTFOLIO INTELLIGENCE</div>
                <div class="snapshot-pill"><span>◷</span> SNAPSHOT · 31 DEC 2025</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_section_title(title, caption=None):
    st.markdown(
        f'<div class="section-title-row"><div class="section-heading">{escape(str(title))}</div></div>',
        unsafe_allow_html=True,
    )
    if caption:
        st.markdown(
            f'<div class="section-caption">{escape(str(caption))}</div>',
            unsafe_allow_html=True,
        )


def format_inr(value, compact=False):
    if value is None:
        return "₹0"
    try:
        value = float(value)
    except (TypeError, ValueError):
        return "₹0"
    if compact:
        if abs(value) >= 1_00_00_000:
            return f"₹{value / 1_00_00_000:.2f} Cr"
        if abs(value) >= 1_00_000:
            return f"₹{value / 1_00_000:.2f} L"
        if abs(value) >= 1_000:
            return f"₹{value / 1_000:.1f} K"
    return f"₹{value:,.2f}"


def render_kpi_card(label, value, footnote="", accent="#5929C6"):
    icons = {
        "TOTAL LOANS": "♙",
        "TOTAL DISBURSED": "₹",
        "OUTSTANDING PRINCIPAL": "▣",
        "PAR30": "◈",
        "PAR90": "◉",
        "LOANS DPD ≥ 30 / 90": "⌁",
        "COLLECTION EFFICIENCY": "◷",
        "AMOUNT DUE": "▤",
        "AMOUNT PAID": "↗",
        "INSTALMENTS PAID": "✓",
        "DIGITAL SHARE BY COUNT": "▦",
        "DIGITAL SHARE BY VALUE": "₹",
        "DIGITAL TRANSACTIONS": "⇄",
        "DIGITAL COLLECTION VALUE": "◉",
        "MONTH-ON-MONTH GROWTH": "↗",
        "YEAR-ON-YEAR GROWTH": "⌁",
        "IDENTIFIED ISSUES": "!",
        "AFFECTED RECORDS": "▤",
        "RESOLVED IN CLEAN LAYER": "✓",
    }
    icon = icons.get(str(label).upper(), "✦")
    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-topline">
                <div class="kpi-icon" style="--icon-accent:{accent};">{icon}</div>
                <div class="kpi-label">{escape(str(label))}</div>
            </div>
            <div class="kpi-value">{escape(str(value))}</div>
            <div class="kpi-footnote">{escape(str(footnote))}</div>
            <div class="kpi-accent" style="background:{accent};"></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def style_plotly(fig, height=370, show_legend=True):
    palette = ["#5929C6", "#8155E8", "#B9A0F5", "#3B82F6", "#14B8A6", "#F59E0B", "#F87171"]
    fig.update_layout(
        template="plotly_white",
        height=height,
        colorway=palette,
        font=dict(family="Inter, sans-serif", size=12, color="#24104F"),
        title=dict(font=dict(size=15, color="#24104F"), x=0.02, xanchor="left"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#FFFFFF",
        margin=dict(l=18, r=18, t=48, b=34),
        showlegend=show_legend,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                    font=dict(size=11, color="#64748B")),
        hoverlabel=dict(bgcolor="#24104F", font=dict(color="#FFFFFF", family="Inter"),
                        bordercolor="#24104F"),
    )
    fig.update_xaxes(showgrid=False, linecolor="#EEE8F8", tickfont=dict(color="#64748B"))
    fig.update_yaxes(showgrid=True, gridcolor="#F0ECF7", zeroline=False,
                     tickfont=dict(color="#64748B"))
    return fig


def render_filter_summary(state, branch, product, segment):
    selected = []
    for label, value in [("State", state), ("Branch", branch), ("Product", product), ("Segment", segment)]:
        if value != "All":
            selected.append(f"{label}: {value}")
    summary = "All records" if not selected else "  ·  ".join(selected)
    st.markdown(
        f'<div class="filter-summary"><span class="filter-pulse"></span><b>ACTIVE FILTERS</b><span>{escape(summary)}</span></div>',
        unsafe_allow_html=True,
    )


def render_data_quality_notice():
    st.markdown(
        """
        <div class="dq-warning">
            <div class="dq-warning-icon">!</div>
            <div><b>Data Quality Note</b><span>Three seeded data-quality issues were identified in the raw data. Review their impact, detection tests and cleaning treatment.</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.button(
        "Open Data Quality Report  →",
        key="open_dq_report",
        use_container_width=True,
        on_click=_go_to_data_quality,
    )


def _go_to_data_quality():
    """Set the navigation widget value before Streamlit reruns the app."""
    st.session_state["nav_page"] = "Data Quality Report"


def render_download_button(dataframe, filename, label="Download CSV"):
    if dataframe is None or dataframe.empty:
        st.info("No data is available for download under the current filters.")
        return
    csv_data = dataframe.to_csv(index=False).encode("utf-8")
    st.download_button(label=label, data=csv_data, file_name=filename,
                       mime="text/csv", key=f"download_{filename}")
