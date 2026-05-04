from __future__ import annotations

from html import escape
from typing import Any

import pandas as pd
import streamlit as st

from src.charts import (
    create_all_charts,
    create_comparison_bar_chart,
    create_multi_ticker_price_chart,
    format_dollars_short,
    format_number_short,
)
from src.data_loader import get_price_history, load_all_financial_data, summarize_data_availability
from src.metrics import build_business_quality_score, build_narrative_package, calculate_financial_metrics
from src.portfolio import (
    DEFAULT_PORTFOLIO,
    analyze_portfolio,
    clean_holdings,
    compare_portfolio_scenarios,
    create_allocation_chart,
    create_correlation_heatmap,
    create_drawdown_comparison_chart,
    create_drawdown_chart,
    create_holdings_comparison_chart,
    create_portfolio_cumulative_chart,
    create_portfolio_vs_benchmark_chart,
)
from src.report_builder import format_money, format_percent, latest_metric_value, latest_year, safe_string


def _configure_page() -> None:
    """
    Configure the Streamlit page and inject DBR-style dark UI styling.
    """
    st.set_page_config(
        page_title="DBR Research Terminal",
        page_icon="DBR",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    st.markdown(
        """
        <style>
        .stApp {
            background: #020617;
            color: #e2e8f0;
        }
        .block-container {
            max-width: 1320px;
            padding-top: 1rem;
            padding-bottom: 2.1rem;
        }
        section[data-testid="stSidebar"] {
            background: #020617;
            border-right: 1px solid #1e293b;
        }
        .dbr-sidebar-brand {
            padding: 0.2rem 0 0.75rem 0;
        }
        .dbr-sidebar-kicker {
            color: #94a3b8;
            text-transform: uppercase;
            letter-spacing: 0.12em;
            font-size: 0.72rem;
            margin-bottom: 0.35rem;
        }
        .dbr-sidebar-title {
            color: #e2e8f0;
            font-weight: 700;
            font-size: 1.05rem;
            margin-bottom: 0.3rem;
        }
        .dbr-sidebar-copy {
            color: #94a3b8;
            font-size: 0.84rem;
            line-height: 1.5;
        }
        .dbr-sidebar-note {
            color: #94a3b8;
            font-size: 0.78rem;
            line-height: 1.45;
            padding-top: 0.65rem;
            border-top: 1px solid #1e293b;
            margin-top: 0.7rem;
        }
        .dbr-hero {
            padding: 1.35rem 1.45rem;
            border: 1px solid #1e293b;
            border-radius: 12px;
            background: #0b1220;
            margin-bottom: 1rem;
        }
        .dbr-eyebrow {
            color: #94a3b8;
            text-transform: uppercase;
            letter-spacing: 0.12em;
            font-size: 0.78rem;
            margin-bottom: 0.45rem;
        }
        .dbr-title {
            font-size: 2.05rem;
            font-weight: 700;
            margin: 0;
            color: #e2e8f0;
        }
        .dbr-subtitle {
            color: #94a3b8;
            margin-top: 0.5rem;
            margin-bottom: 0;
        }
        .dbr-hero-copy {
            color: #94a3b8;
            margin-top: 0.55rem;
            max-width: 860px;
            line-height: 1.5;
        }
        .dbr-mode-guide {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
            gap: 0.75rem;
            margin-top: 0.8rem;
        }
        .dbr-mode-box,
        .dbr-action-card {
            background: #0b1220;
            border: 1px solid #1e293b;
            border-radius: 12px;
            padding: 0.8rem 0.9rem;
            min-height: 128px;
        }
        .dbr-mode-box strong,
        .dbr-action-card strong {
            display: block;
            color: #e2e8f0;
            margin-bottom: 0.35rem;
            font-size: 1.02rem;
        }
        .dbr-action-card p,
        .dbr-mode-box p {
            color: #94a3b8;
            margin: 0;
            line-height: 1.55;
        }
        .dbr-tagline {
            color: #94a3b8;
            margin-top: 0.65rem;
            font-size: 0.92rem;
            max-width: 820px;
        }
        .dbr-page-header {
            margin-bottom: 0.6rem;
        }
        .dbr-page-header h2 {
            margin: 0 0 0.28rem 0;
            color: #e2e8f0;
            font-size: 1.65rem;
        }
        .dbr-page-header p {
            margin: 0;
            color: #94a3b8;
            max-width: 780px;
            line-height: 1.45;
        }
        .dbr-profile-card {
            background: #0b1220;
            border: 1px solid #1e293b;
            border-radius: 12px;
            padding: 0.85rem 0.95rem 0.8rem;
            margin-bottom: 0.7rem;
        }
        .dbr-profile-title {
            margin: 0;
            color: #e2e8f0;
            font-size: 1.28rem;
            font-weight: 650;
            line-height: 1.2;
        }
        .dbr-profile-subtitle {
            color: #94a3b8;
            margin: 0.22rem 0 0.65rem 0;
            font-size: 0.84rem;
        }
        .dbr-profile-divider {
            height: 1px;
            background: #1e293b;
            margin: 0 0 0.72rem 0;
        }
        .dbr-toolbar-label {
            margin: 0 0 0.35rem 0;
            color: #94a3b8;
            font-size: 0.74rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
        }
        .dbr-settings-toolbar {
            display: flex;
            align-items: center;
            gap: 0.65rem;
            margin-bottom: 0.55rem;
        }
        .dbr-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 12px;
            margin: 10px 0 16px 0;
        }
        .dbr-card {
            background: #0b1220;
            border: 1px solid #1e293b;
            border-radius: 12px;
            padding: 10px 12px;
            min-height: auto;
            position: relative;
            overflow: hidden;
        }
        .dbr-card::before,
        .dbr-flag::before,
        .dbr-panel::before {
            content: "";
            position: absolute;
            left: 0;
            top: 0;
            bottom: 0;
            width: 2px;
            background: #334155;
        }
        .dbr-card[data-tone="positive"]::before,
        .dbr-flag[data-tone="positive"]::before,
        .dbr-panel[data-tone="positive"]::before {
            background: #22c55e;
        }
        .dbr-card[data-tone="negative"]::before,
        .dbr-flag[data-tone="negative"]::before,
        .dbr-panel[data-tone="negative"]::before {
            background: #ef4444;
        }
        .dbr-card[data-tone="neutral"]::before,
        .dbr-flag[data-tone="neutral"]::before,
        .dbr-panel[data-tone="neutral"]::before {
            background: #3b82f6;
        }
        .dbr-card[data-tone="caution"]::before,
        .dbr-flag[data-tone="caution"]::before,
        .dbr-panel[data-tone="caution"]::before {
            background: #64748b;
        }
        .dbr-card-label {
            color: #94a3b8;
            font-size: 0.77rem;
            margin-bottom: 0.32rem;
            text-transform: uppercase;
            letter-spacing: 0.09em;
        }
        .dbr-card-value {
            color: #e2e8f0;
            font-size: 1.35rem;
            font-weight: 700;
            line-height: 1.2;
        }
        .dbr-card-sub {
            color: #94a3b8;
            font-size: 0.78rem;
            margin-top: 0.2rem;
            line-height: 1.35;
        }
        .dbr-flag {
            background: #0b1220;
            border: 1px solid #1e293b;
            border-radius: 12px;
            padding: 0.65rem 0.75rem;
            min-height: 74px;
            position: relative;
            overflow: hidden;
        }
        .dbr-flag-label {
            color: #94a3b8;
            font-size: 0.74rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            margin-bottom: 0.35rem;
        }
        .dbr-flag-value {
            color: #e2e8f0;
            font-size: 1.02rem;
            font-weight: 700;
        }
        .dbr-flag-sub {
            color: #94a3b8;
            font-size: 0.8rem;
            margin-top: 0.25rem;
        }
        .dbr-section-header {
            margin: 0.15rem 0 0.45rem 0;
        }
        .dbr-section-header h3 {
            margin: 0;
            color: #e2e8f0;
            font-size: 0.98rem;
            font-weight: 600;
        }
        .dbr-section-copy {
            color: #94a3b8;
            font-size: 0.82rem;
            line-height: 1.35;
            margin: 0.18rem 0 0 0;
        }
        .dbr-section-title {
            margin: 0 0 0.55rem 0;
            color: #e2e8f0;
            font-size: 1.02rem;
        }
        .dbr-snapshot {
            background: #0b1220;
            border: 1px solid #1e293b;
            border-radius: 12px;
            padding: 0.56rem 0.72rem;
            margin-top: 0.45rem;
            margin-bottom: 0.45rem;
        }
        .dbr-snapshot h3 {
            margin-top: 0;
            margin-bottom: 0.3rem;
            color: #e2e8f0;
            font-size: 0.94rem;
        }
        .dbr-snapshot ul {
            margin: 0;
            padding-left: 1rem;
            color: #dbe4f0;
        }
        .dbr-snapshot li {
            margin-bottom: 0.18rem;
            font-size: 0.8rem;
            line-height: 1.35;
        }
        .dbr-summary-strip {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
            gap: 10px;
            margin: 10px 0 14px 0;
        }
        .dbr-insight {
            background: #111827;
            border-left: 2px solid #3b82f6;
            border-radius: 8px;
            padding: 10px 12px;
            color: #e2e8f0;
            font-size: 0.82rem;
            line-height: 1.45;
            margin: 8px 0 12px 0;
        }
        .dbr-insight strong {
            color: #94a3b8;
            font-size: 0.74rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            display: block;
            margin-bottom: 0.2rem;
        }
        .dbr-inline-alert {
            background: #1f2937;
            border-left: 2px solid #d97706;
            border-radius: 8px;
            padding: 10px 12px;
            color: #94a3b8;
            font-size: 0.8rem;
            line-height: 1.4;
            margin: 8px 0 12px 0;
        }
        .dbr-score-note {
            color: #94a3b8;
            font-size: 0.82rem;
            margin-top: 0.5rem;
        }
        .dbr-muted-note {
            color: #94a3b8;
            font-size: 0.82rem;
            margin-top: 0.5rem;
        }
        .dbr-valuation-panel {
            background: #0b1220;
            border: 1px solid #1e293b;
            border-radius: 12px;
            padding: 0.7rem 0.78rem 0.55rem;
            margin-top: 0.35rem;
            margin-bottom: 0.65rem;
        }
        .dbr-valuation-panel h3 {
            margin: 0 0 0.55rem 0;
            color: #e2e8f0;
        }
        .dbr-compare-panel {
            margin-bottom: 0.45rem;
        }
        .dbr-bestworst-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
            gap: 0.9rem;
        }
        .dbr-info-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
            gap: 0.8rem;
        }
        .dbr-footer {
            margin-top: 1.5rem;
            padding-top: 0.7rem;
            border-top: 1px solid #1e293b;
            color: #94a3b8;
            font-size: 0.83rem;
        }
        div[data-testid="stMarkdownContainer"] p {
            line-height: 1.4;
        }
        div[data-testid="stTextInput"] input {
            background-color: #0b1220;
            color: #e2e8f0;
            border: 1px solid #1e293b;
            border-radius: 12px;
        }
        div[data-testid="stSelectbox"] > div,
        div[data-testid="stMultiSelect"] > div,
        div[data-testid="stNumberInput"] input {
            background-color: #0b1220;
            border-radius: 12px;
            border: 1px solid #1e293b;
        }
        div[data-testid="stTextInput"] input:focus,
        div[data-testid="stNumberInput"] input:focus {
            border-color: #3b82f6 !important;
            box-shadow: none !important;
        }
        div[data-testid="stButton"] button[kind="primary"] {
            background: #3b82f6;
            color: #e2e8f0;
            border: 1px solid #3b82f6;
        }
        div[data-testid="stButton"] button[kind="secondary"] {
            background: transparent;
            color: #e2e8f0;
            border: 1px solid #334155;
        }
        div[data-testid="stButton"] button:hover {
            box-shadow: none;
            filter: none;
        }
        div[data-testid="stButton"] button[kind="primary"]:hover {
            background: #2563eb;
            border-color: #2563eb;
        }
        div[data-testid="stButton"] button[kind="secondary"]:hover {
            background: #0b1220;
            border-color: #475569;
            border-radius: 12px;
        }
        div[data-testid="stButton"] button {
            border-radius: 12px;
            min-height: 2.65rem;
        }
        div[data-testid="stDataFrame"] {
            border: 1px solid #1e293b;
            border-radius: 12px;
            overflow: hidden;
        }
        div[data-testid="stDataEditor"] {
            border: 1px solid #1e293b;
            border-radius: 12px;
            overflow: hidden;
        }
        button[data-baseweb="tab"] {
            color: #94a3b8 !important;
        }
        button[data-baseweb="tab"][aria-selected="true"] {
            color: #e2e8f0 !important;
            border-bottom-color: #3b82f6 !important;
        }
        [data-testid="stTabs"] [data-baseweb="tab-highlight"] {
            background-color: #3b82f6 !important;
        }
        div[data-testid="stDataFrame"] [data-testid="stTable"] td,
        div[data-testid="stDataFrame"] [data-testid="stTable"] th {
            padding-top: 0.35rem;
            padding-bottom: 0.35rem;
        }
        div[data-testid="stTabs"] {
            margin-top: 0.55rem;
        }
        div[data-testid="stPlotlyChart"] {
            margin-bottom: 0.7rem;
        }
        div[data-testid="stVerticalBlock"] > div:has(> div[data-testid="stPlotlyChart"]) {
            padding-top: 0.1rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _section_spacer(height: float = 0.6) -> None:
    """
    Insert consistent vertical spacing between major sections.
    """
    st.markdown(f"<div style='height: {height}rem;'></div>", unsafe_allow_html=True)


def _render_home_page() -> None:
    """
    Render the public-facing landing page.
    """
    st.markdown(
        """
        <div class="dbr-hero">
            <div class="dbr-eyebrow">Rules-Based Equity Research</div>
            <h1 class="dbr-title">DBR Research Terminal</h1>
            <p class="dbr-subtitle">Interactive public-market research built on transparent rules, financial statements, valuation data, portfolio context, and market behavior.</p>
            <div class="dbr-tagline">Rules-based investment research for equities, comps, and portfolio risk.</div>
            <div class="dbr-hero-copy">
                Use the terminal to research one company in depth, compare multiple businesses side by side, or analyze a portfolio with risk and return diagnostics.
            </div>
            <div class="dbr-mode-guide">
                <div class="dbr-action-card">
                    <strong>Analyze a Company</strong>
                    <p>Research one public company with financial trends, valuation context, quality signals, and market behavior.</p>
                </div>
                <div class="dbr-action-card">
                    <strong>Compare Companies</strong>
                    <p>Compare peers side by side on growth, profitability, valuation, balance sheet strength, and market performance.</p>
                </div>
                <div class="dbr-action-card">
                    <strong>Analyze a Portfolio</strong>
                    <p>Stress test a custom portfolio with weighted returns, risk, correlations, benchmark context, and what-if scenarios.</p>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.info("Choose a page from the sidebar to begin.")


def _render_page_header(title: str, description: str) -> None:
    """
    Render a compact working-page header.
    """
    st.markdown(
        f"""
        <div class="dbr-page-header">
            <h2>{title}</h2>
            <p>{description}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_panel_header(title: str, tone: str = "neutral", copy: str | None = None) -> None:
    """
    Render a compact standalone text section header.
    """
    copy_html = f'<p class="dbr-section-copy">{escape(copy)}</p>' if copy else ""
    st.markdown(
        f'<div class="dbr-section-header"><h3>{escape(title)}</h3>{copy_html}</div>',
        unsafe_allow_html=True,
    )


def _render_sidebar() -> str:
    """
    Render the branded sidebar navigation and return the selected page.
    """
    with st.sidebar:
        st.markdown(
            """
            <div class="dbr-sidebar-brand">
                <div class="dbr-sidebar-kicker">DBR</div>
                <div class="dbr-sidebar-title">Research Terminal</div>
                <div class="dbr-sidebar-copy">Rules-based workflows for company research, peer comps, and portfolio risk.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        page = st.radio(
            "Navigation",
            ["Home", "Company Research", "Peer Comparison", "Portfolio Lab"],
        )
        st.markdown(
            '<div class="dbr-sidebar-note">Data from Yahoo Finance/yfinance. Not investment advice.</div>',
            unsafe_allow_html=True,
        )
    return page


def _open_settings_panel(title: str = "Analysis Settings") -> None:
    """
    Render a compact settings toolbar label.
    """
    st.markdown(f'<div class="dbr-toolbar-label">{escape(title)}</div>', unsafe_allow_html=True)


def _close_settings_panel() -> None:
    """
    Retained for compatibility with existing call sites.
    """
    return None


@st.cache_data(show_spinner=False, ttl=3600)
def _cached_financial_data(
    ticker: str,
    financial_period: str,
    price_timeframe: str,
) -> dict[str, pd.DataFrame]:
    """
    Cache yfinance-backed data pulls at the Streamlit layer.
    """
    return load_all_financial_data(
        ticker,
        period_type=financial_period.lower(),
        price_period=price_timeframe,
    )


@st.cache_data(show_spinner=False, ttl=3600)
def _cached_price_history(ticker: str, price_timeframe: str) -> pd.DataFrame:
    """
    Cache price-only requests for portfolio analysis.
    """
    return get_price_history(ticker, period=price_timeframe)


def _format_market_cap(value: Any) -> str:
    return format_dollars_short(value)


def _format_multiple(value: Any) -> str:
    """
    Format valuation multiples compactly.
    """
    numeric_value = pd.to_numeric(value, errors="coerce")
    if pd.isna(numeric_value):
        return "N/A"
    return f"{float(numeric_value):.2f}x"


def _format_plain_number(value: Any) -> str:
    """
    Format plain numeric values such as beta.
    """
    numeric_value = pd.to_numeric(value, errors="coerce")
    if pd.isna(numeric_value):
        return "N/A"
    return f"{float(numeric_value):.2f}"


def _format_compare_percent(value: Any) -> str:
    """
    Format percentage values for comparison tables.
    """
    numeric_value = pd.to_numeric(value, errors="coerce")
    if pd.isna(numeric_value):
        return "N/A"
    return f"{float(numeric_value):.1%}"


def _format_table_money(value: Any) -> str:
    return format_dollars_short(value)


def _format_table_percent(value: Any) -> str:
    return format_percent(value)


def _format_price_band_position(current_price: Any, anchor_price: Any, direction: str) -> str:
    """
    Show current price as a percentage below the high or above the low.
    """
    current_numeric = pd.to_numeric(current_price, errors="coerce")
    anchor_numeric = pd.to_numeric(anchor_price, errors="coerce")
    if pd.isna(current_numeric) or pd.isna(anchor_numeric) or anchor_numeric == 0:
        return "N/A"

    if direction == "high":
        value = (float(current_numeric) / float(anchor_numeric)) - 1
        return f"{value:.1%} vs high"

    value = (float(current_numeric) / float(anchor_numeric)) - 1
    return f"{value:+.1%} vs low"


def _is_financial_company(company_info_df: pd.DataFrame) -> bool:
    """
    Detect whether the company appears to be in a financial category.
    """
    if not isinstance(company_info_df, pd.DataFrame) or company_info_df.empty:
        return False

    row = company_info_df.iloc[0]
    tokens = " ".join(
        [
            safe_string(row.get("sector") if hasattr(row, "get") else None, ""),
            safe_string(row.get("name") if hasattr(row, "get") else None, ""),
        ]
    ).lower()
    keywords = [
        "financial",
        "bank",
        "capital markets",
        "credit",
        "insurance",
        "lending",
    ]
    return any(keyword in tokens for keyword in keywords)


def _display_company_header(ticker: str, company_info_df: pd.DataFrame, metrics_df: pd.DataFrame) -> None:
    """
    Render the company summary block at the top of the app.
    """
    info_row = company_info_df.iloc[0] if isinstance(company_info_df, pd.DataFrame) and not company_info_df.empty else {}
    company_name = safe_string(info_row.get("name") if hasattr(info_row, "get") else None, ticker.upper())
    sector = safe_string(info_row.get("sector") if hasattr(info_row, "get") else None)
    market_cap = _format_market_cap(info_row.get("market_cap") if hasattr(info_row, "get") else None)
    fiscal_year = latest_year(metrics_df)

    profile_items = [
        ("Ticker", ticker.upper()),
        ("Sector", sector or "N/A"),
        ("Market Cap", market_cap),
        ("Latest Fiscal Year", str(fiscal_year)),
    ]
    info_html = "".join(
        f'<div class="dbr-card" data-tone="neutral"><div class="dbr-card-label">{escape(str(label))}</div><div class="dbr-card-value" style="font-size:1.05rem;">{escape(str(value))}</div></div>'
        for label, value in profile_items
    )
    st.markdown(
        f"""
        <div class="dbr-profile-card">
            <div class="dbr-eyebrow">Company Profile</div>
            <h2 class="dbr-profile-title">{escape(company_name)} ({escape(ticker.upper())})</h2>
            <p class="dbr-profile-subtitle">Latest company profile, market context, and reported financial snapshot.</p>
            <div class="dbr-profile-divider"></div>
            <div class="dbr-info-grid">{info_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _latest_info_row(company_info_df: pd.DataFrame) -> Any:
    """
    Safely return the single company info row or an empty mapping.
    """
    if isinstance(company_info_df, pd.DataFrame) and not company_info_df.empty:
        return company_info_df.iloc[0]
    return {}


def _parse_ticker_list(raw_input: str) -> list[str]:
    """
    Parse a comma-separated ticker input into a clean unique list.
    """
    seen: set[str] = set()
    tickers: list[str] = []
    for part in raw_input.split(","):
        ticker = part.strip().upper()
        if ticker and ticker not in seen:
            seen.add(ticker)
            tickers.append(ticker)
    return tickers


def _render_metric_card_grid(cards: list[tuple[str, str, str, str]]) -> None:
    """
    Render static metric cards in a consistent responsive CSS grid.
    """
    html_parts = ['<div class="dbr-grid">']
    for label, value, sublabel, tone in cards:
        html_parts.append(
            (
                f'<div class="dbr-card" data-tone="{escape(tone)}">'
                f'<div class="dbr-card-label">{escape(str(label))}</div>'
                f'<div class="dbr-card-value">{escape(str(value))}</div>'
                f'<div class="dbr-card-sub">{escape(str(sublabel))}</div>'
                "</div>"
            )
        )
    html_parts.append("</div>")
    full_grid_html = "".join(html_parts)
    st.markdown(full_grid_html, unsafe_allow_html=True)


def _render_summary_strip(items: list[tuple[str, str, str, str]]) -> None:
    """
    Render a compact executive-summary row using the shared card styling.
    """
    html_parts = ['<div class="dbr-summary-strip">']
    for label, value, sublabel, tone in items:
        html_parts.append(
            (
                f'<div class="dbr-card" data-tone="{escape(tone)}">'
                f'<div class="dbr-card-label">{escape(str(label))}</div>'
                f'<div class="dbr-card-value" style="font-size:1.02rem;">{escape(str(value))}</div>'
                f'<div class="dbr-card-sub">{escape(str(sublabel))}</div>'
                "</div>"
            )
        )
    html_parts.append("</div>")
    st.markdown("".join(html_parts), unsafe_allow_html=True)


def _render_dbr_insight(text: str) -> None:
    """
    Render a compact DBR insight bar.
    """
    st.markdown(
        f'<div class="dbr-insight"><strong>DBR Insight</strong>{escape(text)}</div>',
        unsafe_allow_html=True,
    )


def _render_inline_alert(message: str, tone: str = "warning") -> None:
    """
    Render a subtle inline alert panel.
    """
    border_color = "#d97706" if tone == "warning" else "#ef4444"
    st.markdown(
        f'<div class="dbr-inline-alert" style="border-left-color:{border_color};">{escape(message)}</div>',
        unsafe_allow_html=True,
    )


def _render_flag_card(column: Any, label: str, value: str, sublabel: str, tone: str = "neutral") -> None:
    with column:
        st.markdown(
            f"""
            <div class="dbr-flag" data-tone="{escape(tone)}">
                <div class="dbr-flag-label">{escape(str(label))}</div>
                <div class="dbr-flag-value">{escape(str(value))}</div>
                <div class="dbr-flag-sub">{escape(str(sublabel))}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _tone_from_numeric(value: Any, invert: bool = False) -> str:
    """
    Map a numeric value into a subtle card tone.
    """
    numeric_value = pd.to_numeric(value, errors="coerce")
    if pd.isna(numeric_value):
        return "neutral"
    is_positive = float(numeric_value) >= 0
    if invert:
        is_positive = not is_positive
    return "positive" if is_positive else "negative"


def _metric_series(metrics_df: pd.DataFrame, column: str) -> pd.Series:
    """
    Return a clean numeric series for one metric column.
    """
    if not isinstance(metrics_df, pd.DataFrame) or metrics_df.empty or column not in metrics_df.columns:
        return pd.Series(dtype="float64")
    return pd.to_numeric(metrics_df[column], errors="coerce").dropna()


def _latest_and_prior(metrics_df: pd.DataFrame, column: str) -> tuple[Any, Any]:
    """
    Return the latest and prior non-null values for a metric.
    """
    series = _metric_series(metrics_df, column)
    if series.empty:
        return None, None
    latest = series.iloc[-1]
    prior = series.iloc[-2] if len(series) > 1 else None
    return latest, prior


def _delta_percent(latest: Any, prior: Any) -> Any:
    if latest is None or prior is None:
        return None
    if pd.isna(latest) or pd.isna(prior) or prior == 0:
        return None
    return (float(latest) - float(prior)) / abs(float(prior))


def _delta_money(latest: Any, prior: Any) -> Any:
    if latest is None or prior is None:
        return None
    if pd.isna(latest) or pd.isna(prior):
        return None
    return float(latest) - float(prior)


def _signed_percent_text(value: Any) -> str:
    if value is None or pd.isna(value):
        return "Change unavailable"
    return f"Vs prior {'+' if value >= 0 else ''}{value:.1%}"


def _signed_money_text(value: Any) -> str:
    if value is None or pd.isna(value):
        return "Change unavailable"
    sign = "+" if value >= 0 else "-"
    return f"Vs prior {sign}{format_money(abs(float(value)))}"


def _trend_text(metrics_df: pd.DataFrame, column: str, positive_label: str, negative_label: str) -> str:
    latest, prior = _latest_and_prior(metrics_df, column)
    delta = _delta_percent(latest, prior)
    if delta is None:
        return "Trend unavailable"
    return positive_label if delta >= 0 else negative_label


def _display_kpis(metrics_df: pd.DataFrame) -> None:
    """
    Render KPI cards using the latest available values and change context.
    """
    kpi_values = [
        (
            "Revenue",
            format_money(latest_metric_value(metrics_df, "revenue")),
            _signed_percent_text(_delta_percent(*_latest_and_prior(metrics_df, "revenue"))),
            _tone_from_numeric(latest_metric_value(metrics_df, "revenue")),
        ),
        (
            "Revenue Growth",
            format_percent(latest_metric_value(metrics_df, "revenue_growth_pct")),
            _trend_text(metrics_df, "revenue_growth_pct", "Growth improving", "Growth slowing"),
            _tone_from_numeric(latest_metric_value(metrics_df, "revenue_growth_pct")),
        ),
        (
            "EBITDA",
            format_money(latest_metric_value(metrics_df, "ebitda")),
            _signed_money_text(_delta_money(*_latest_and_prior(metrics_df, "ebitda"))),
            _tone_from_numeric(latest_metric_value(metrics_df, "ebitda")),
        ),
        (
            "EBITDA Margin",
            format_percent(latest_metric_value(metrics_df, "ebitda_margin_pct")),
            _trend_text(metrics_df, "ebitda_margin_pct", "Margin improving", "Margin compressing"),
            _tone_from_numeric(latest_metric_value(metrics_df, "ebitda_margin_pct")),
        ),
        (
            "Net Income",
            format_money(latest_metric_value(metrics_df, "net_income")),
            _signed_money_text(_delta_money(*_latest_and_prior(metrics_df, "net_income"))),
            _tone_from_numeric(latest_metric_value(metrics_df, "net_income")),
        ),
        (
            "Free Cash Flow",
            format_money(latest_metric_value(metrics_df, "free_cash_flow")),
            _signed_money_text(_delta_money(*_latest_and_prior(metrics_df, "free_cash_flow"))),
            _tone_from_numeric(latest_metric_value(metrics_df, "free_cash_flow")),
        ),
        (
            "Cash",
            format_money(latest_metric_value(metrics_df, "cash_and_equivalents")),
            _signed_money_text(_delta_money(*_latest_and_prior(metrics_df, "cash_and_equivalents"))),
            "positive",
        ),
        (
            "Debt",
            format_money(latest_metric_value(metrics_df, "total_debt")),
            _signed_money_text(_delta_money(*_latest_and_prior(metrics_df, "total_debt"))),
            "caution" if pd.notna(pd.to_numeric(latest_metric_value(metrics_df, "total_debt"), errors="coerce")) else "neutral",
        ),
    ]

    _render_metric_card_grid(kpi_values)


def _quality_flags(metrics_df: pd.DataFrame) -> list[tuple[str, str, str]]:
    revenue_growth = latest_metric_value(metrics_df, "revenue_growth_pct")
    net_income = latest_metric_value(metrics_df, "net_income")
    free_cash_flow = latest_metric_value(metrics_df, "free_cash_flow")
    net_cash_debt = latest_metric_value(metrics_df, "net_cash_debt")

    revenue_growth_flag = "N/A"
    if revenue_growth is not None and not pd.isna(revenue_growth):
        revenue_growth_flag = "Strong" if revenue_growth > 0.1 else "Weak"

    profitability_flag = "N/A"
    if net_income is not None and not pd.isna(net_income):
        profitability_flag = "Positive" if net_income >= 0 else "Negative"

    fcf_flag = "N/A"
    if free_cash_flow is not None and not pd.isna(free_cash_flow):
        fcf_flag = "Positive" if free_cash_flow >= 0 else "Negative"

    balance_flag = "N/A"
    if net_cash_debt is not None and not pd.isna(net_cash_debt):
        balance_flag = "Net Cash" if net_cash_debt >= 0 else "Net Debt"

    return [
        ("Revenue Growth", revenue_growth_flag, format_percent(revenue_growth), "positive" if revenue_growth_flag == "Strong" else "negative" if revenue_growth_flag == "Weak" else "neutral"),
        ("Profitability", profitability_flag, format_money(net_income), "positive" if profitability_flag == "Positive" else "negative" if profitability_flag == "Negative" else "neutral"),
        ("Free Cash Flow", fcf_flag, format_money(free_cash_flow), "positive" if fcf_flag == "Positive" else "negative" if fcf_flag == "Negative" else "neutral"),
        ("Balance Sheet", balance_flag, format_money(net_cash_debt), "positive" if balance_flag == "Net Cash" else "caution" if balance_flag == "Net Debt" else "neutral"),
    ]


def _display_quality_flags(metrics_df: pd.DataFrame) -> None:
    flag_columns = st.columns(4)
    for column, (label, value, sublabel, tone) in zip(flag_columns, _quality_flags(metrics_df)):
        _render_flag_card(column, label, value, sublabel, tone=tone)


def _executive_snapshot(metrics_df: pd.DataFrame, is_financial_company: bool) -> list[str]:
    """
    Generate a short set of decision-useful bullet insights.
    """
    bullets: list[str] = []

    latest_revenue_growth = latest_metric_value(metrics_df, "revenue_growth_pct")
    if latest_revenue_growth is not None and not pd.isna(latest_revenue_growth):
        if latest_revenue_growth > 0.1:
            bullets.append(f"Revenue growth remains strong at {format_percent(latest_revenue_growth)} in the latest period.")
        elif latest_revenue_growth >= 0:
            bullets.append(f"Revenue is still growing, but at a more modest {format_percent(latest_revenue_growth)} in the latest period.")
        else:
            bullets.append(f"Revenue declined {format_percent(abs(float(latest_revenue_growth)))} in the latest period.")

    latest_net_income = latest_metric_value(metrics_df, "net_income")
    if latest_net_income is not None and not pd.isna(latest_net_income):
        net_income_text = "positive" if latest_net_income >= 0 else "negative"
        bullets.append(f"Latest net income is {net_income_text} at {format_money(latest_net_income)}.")

    latest_ebitda = latest_metric_value(metrics_df, "ebitda")
    if latest_ebitda is not None and not pd.isna(latest_ebitda):
        bullets.append(f"Latest EBITDA is {format_money(latest_ebitda)}.")

    latest_fcf = latest_metric_value(metrics_df, "free_cash_flow")
    if latest_fcf is not None and not pd.isna(latest_fcf):
        fcf_text = "positive" if latest_fcf >= 0 else "negative"
        bullets.append(f"Free cash flow is {fcf_text} at {format_money(latest_fcf)}.")

    latest_net_cash_debt = latest_metric_value(metrics_df, "net_cash_debt")
    if latest_net_cash_debt is not None and not pd.isna(latest_net_cash_debt):
        if latest_net_cash_debt >= 0:
            bullets.append(f"The balance sheet is in a net cash position of {format_money(latest_net_cash_debt)}.")
        else:
            bullets.append(f"The balance sheet is in a net debt position of {format_money(abs(float(latest_net_cash_debt)))}.")

    latest_margin = latest_metric_value(metrics_df, "net_income_margin_pct")
    prior_margin = _latest_and_prior(metrics_df, "net_income_margin_pct")[1]
    if latest_margin is not None and prior_margin is not None and not pd.isna(latest_margin) and not pd.isna(prior_margin):
        margin_delta = float(latest_margin) - float(prior_margin)
        if margin_delta > 0:
            bullets.append(f"Net income margin improved versus the prior period by {margin_delta:.1%}.")
        elif margin_delta < 0:
            bullets.append(f"Net income margin deteriorated versus the prior period by {abs(margin_delta):.1%}.")

    if is_financial_company:
        bullets.append(
            "For financial companies, free cash flow and traditional margin metrics are less useful because lending, deposits, and balance-sheet movements can dominate the statements."
        )

    if not bullets:
        bullets.append("Limited financial statement data was available, so the snapshot is constrained.")

    return bullets[:6]


def _display_executive_snapshot(metrics_df: pd.DataFrame, is_financial_company: bool) -> None:
    concise_bullets: list[str] = []
    latest_revenue_growth = latest_metric_value(metrics_df, "revenue_growth_pct")
    latest_net_income = latest_metric_value(metrics_df, "net_income")
    latest_ebitda = latest_metric_value(metrics_df, "ebitda")
    latest_fcf = latest_metric_value(metrics_df, "free_cash_flow")
    latest_net_cash_debt = latest_metric_value(metrics_df, "net_cash_debt")
    latest_margin = latest_metric_value(metrics_df, "net_income_margin_pct")
    prior_margin = _latest_and_prior(metrics_df, "net_income_margin_pct")[1]

    if latest_revenue_growth is not None and not pd.isna(latest_revenue_growth):
        concise_bullets.append(f"Revenue growth: {format_percent(latest_revenue_growth)}")
    if latest_net_income is not None and not pd.isna(latest_net_income):
        concise_bullets.append(f"Net income: {format_money(latest_net_income)}")
    if latest_ebitda is not None and not pd.isna(latest_ebitda):
        concise_bullets.append(f"EBITDA: {format_money(latest_ebitda)}")
    if latest_fcf is not None and not pd.isna(latest_fcf):
        concise_bullets.append(f"Free cash flow: {format_money(latest_fcf)}")
    if latest_net_cash_debt is not None and not pd.isna(latest_net_cash_debt):
        balance_read = "net cash" if latest_net_cash_debt >= 0 else "net debt"
        concise_bullets.append(f"Balance sheet: {balance_read} {format_money(abs(float(latest_net_cash_debt)))}")
    if latest_margin is not None and prior_margin is not None and not pd.isna(latest_margin) and not pd.isna(prior_margin):
        margin_delta = float(latest_margin) - float(prior_margin)
        trend_word = "improved" if margin_delta >= 0 else "deteriorated"
        concise_bullets.append(f"Margin trend: {trend_word} {abs(margin_delta):.1%}")
    if is_financial_company:
        concise_bullets.append("Financials caveat: FCF and margins can be less comparable")
    if not concise_bullets:
        concise_bullets = _executive_snapshot(metrics_df, is_financial_company)

    bullets_html = "".join(f"<li>{escape(bullet)}</li>" for bullet in concise_bullets[:6])
    st.markdown(
        f"""
        <div class="dbr-snapshot">
            <h3>Executive Snapshot</h3>
            <ul>{bullets_html}</ul>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _display_company_summary_strip(metrics_df: pd.DataFrame, company_info_df: pd.DataFrame) -> None:
    """
    Render a compact executive summary for single-company research.
    """
    quality = build_business_quality_score(metrics_df, company_info_df)
    revenue_growth = latest_metric_value(metrics_df, "revenue_growth_pct")
    net_income = latest_metric_value(metrics_df, "net_income")
    risks = quality.get("risks", [])

    growth_read = "Unavailable"
    growth_tone = "neutral"
    if revenue_growth is not None and not pd.isna(revenue_growth):
        if revenue_growth > 0.12:
            growth_read = "Strong"
            growth_tone = "positive"
        elif revenue_growth >= 0:
            growth_read = "Moderate"
            growth_tone = "neutral"
        else:
            growth_read = "Negative"
            growth_tone = "negative"

    profitability_read = "Unavailable"
    profitability_tone = "neutral"
    if net_income is not None and not pd.isna(net_income):
        profitability_read = "Profitable" if net_income >= 0 else "Loss-making"
        profitability_tone = "positive" if net_income >= 0 else "negative"

    summary_items = [
        ("DBR Verdict", quality.get("label", "Mixed"), f"Score {quality.get('score', 'N/A')}/100", "neutral"),
        ("Growth Read", growth_read, format_percent(revenue_growth), growth_tone),
        ("Profitability", profitability_read, format_money(net_income), profitability_tone),
        ("Key Risk", risks[0] if risks else "No major risk flagged", "Highest-priority watch item", "caution" if risks else "neutral"),
    ]
    _render_summary_strip(summary_items)

    fcf = latest_metric_value(metrics_df, "free_cash_flow")
    net_cash_debt = latest_metric_value(metrics_df, "net_cash_debt")
    watch_item = risks[0] if risks else "valuation discipline and consistency of execution"
    growth_text = (
        "Growth remains strong"
        if revenue_growth is not None and not pd.isna(revenue_growth) and revenue_growth > 0.12
        else "Growth is moderate"
        if revenue_growth is not None and not pd.isna(revenue_growth) and revenue_growth >= 0
        else "Growth is under pressure"
    )
    profitability_text = (
        "profitability is positive"
        if net_income is not None and not pd.isna(net_income) and net_income >= 0
        else "profitability remains pressured"
    )
    cash_flow_text = (
        "free cash flow is positive"
        if fcf is not None and not pd.isna(fcf) and fcf >= 0
        else "free cash flow is constrained"
    )
    balance_text = (
        "the balance sheet is net cash"
        if net_cash_debt is not None and not pd.isna(net_cash_debt) and net_cash_debt >= 0
        else "the balance sheet carries net debt"
        if net_cash_debt is not None and not pd.isna(net_cash_debt)
        else "balance sheet visibility is limited"
    )
    insight = f"{growth_text}, {profitability_text}, and {cash_flow_text}. {balance_text.capitalize()}. The key watch item is {watch_item.lower()}."
    _render_dbr_insight(insight)


def _display_valuation_section(company_info_df: pd.DataFrame) -> None:
    """
    Render valuation cards using yfinance info and fast_info data.
    """
    info_row = _latest_info_row(company_info_df)
    valuation_cards = [
        ("Market Cap", format_money(info_row.get("market_cap") if hasattr(info_row, "get") else None)),
        ("Enterprise Value", format_money(info_row.get("enterprise_value") if hasattr(info_row, "get") else None)),
        ("P/S", _format_multiple(info_row.get("price_to_sales") if hasattr(info_row, "get") else None)),
        ("P/E", _format_plain_number(info_row.get("trailing_pe") if hasattr(info_row, "get") else None)),
        ("Forward P/E", _format_plain_number(info_row.get("forward_pe") if hasattr(info_row, "get") else None)),
        ("EV/Revenue", _format_multiple(info_row.get("ev_to_revenue") if hasattr(info_row, "get") else None)),
        ("EV/EBITDA", _format_multiple(info_row.get("ev_to_ebitda") if hasattr(info_row, "get") else None)),
        (
            "Price vs 52W High",
            _format_price_band_position(
                info_row.get("current_price") if hasattr(info_row, "get") else None,
                info_row.get("fifty_two_week_high") if hasattr(info_row, "get") else None,
                "high",
            ),
        ),
        (
            "Price vs 52W Low",
            _format_price_band_position(
                info_row.get("current_price") if hasattr(info_row, "get") else None,
                info_row.get("fifty_two_week_low") if hasattr(info_row, "get") else None,
                "low",
            ),
        ),
    ]

    _render_panel_header("Valuation")
    _render_metric_card_grid([(label, value, "Latest available", "neutral") for label, value in valuation_cards])


def _score_band_colors(label: str) -> tuple[str, str]:
    """
    Return accent colors for the business quality score band.
    """
    mapping = {
        "Excellent": ("#22c55e", "rgba(34, 197, 94, 0.12)"),
        "Strong": ("#38bdf8", "rgba(56, 189, 248, 0.12)"),
        "Mixed": ("#f59e0b", "rgba(245, 158, 11, 0.12)"),
        "Weak": ("#ef4444", "rgba(239, 68, 68, 0.12)"),
    }
    return mapping.get(label, ("#94a3b8", "rgba(148, 163, 184, 0.12)"))


def _display_business_quality_score(metrics_df: pd.DataFrame, company_info_df: pd.DataFrame) -> None:
    """
    Render the rules-based business quality score.
    """
    score_data = build_business_quality_score(metrics_df, company_info_df)
    score = score_data["score"]
    label = score_data["label"]
    strengths = score_data["strengths"]
    risks = score_data["risks"]
    explanation = score_data["explanation"]
    accent_color, accent_bg = _score_band_colors(label)

    st.markdown("### Business Quality Score")
    score_col, summary_col = st.columns([1, 2])
    with score_col:
        st.markdown(
            f"""
            <div class="dbr-card" data-tone="neutral" style="border-color: {accent_color}; background: linear-gradient(135deg, {accent_bg}, rgba(15, 23, 42, 0.92));">
                <div class="dbr-card-label">Business Quality Score</div>
                <div class="dbr-card-value" style="color: {accent_color};">{score}/100</div>
                <div class="dbr-card-sub" style="color: {accent_color};">{label}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with summary_col:
        st.markdown(f"**Overall:** {score}/100 ({label})")
        st.markdown(explanation)
        st.markdown(
            '<div class="dbr-score-note">This score is a rules-based research aid, not a buy/sell recommendation.</div>',
            unsafe_allow_html=True,
        )

    strength_col, risk_col = st.columns(2)
    with strength_col:
        _render_panel_header("Strengths", tone="positive")
        for item in strengths:
            st.write(f"- {item}")
    with risk_col:
        _render_panel_header("Risks", tone="caution")
        for item in risks:
            st.write(f"- {item}")
        st.markdown(
            f'<div class="dbr-muted-note">{metrics_df.attrs.get("ebitda_note", "EBITDA is often unavailable or less meaningful for banks, lenders, insurers, and other financial companies.")}</div>',
            unsafe_allow_html=True,
        )


def _display_narrative_tab(metrics_df: pd.DataFrame, company_info_df: pd.DataFrame) -> None:
    """
    Render rules-based trend, narrative, and signals sections.
    """
    package = build_narrative_package(metrics_df, company_info_df)
    trends = package["trends"]
    what_changed = package["what_changed"]
    narrative = package["narrative"]
    signals = package["signals"]

    st.markdown("### Trend Detection")
    trend_col_1, trend_col_2, trend_col_3, trend_col_4 = st.columns(4)
    _render_flag_card(trend_col_1, "Revenue Growth", str(trends["revenue_growth_trend"]).title(), "Latest trend")
    _render_flag_card(trend_col_2, "Net Income", str(trends["net_income_trend"]).title(), "Latest trend")
    _render_flag_card(trend_col_3, "Free Cash Flow", str(trends["free_cash_flow_trend"]).title(), "Latest trend")
    _render_flag_card(trend_col_4, "Margins", str(trends["margin_trend"]).title(), "Latest trend")

    _section_spacer(0.35)
    st.markdown("### What Changed vs Prior Period")
    for bullet in what_changed:
        st.write(f"- {bullet}")

    _section_spacer(0.35)
    st.markdown("### Investment Narrative")
    st.write(f"**Current read:** {narrative['current_read']}")
    st.write("**What improved:**")
    for item in narrative["what_improved"]:
        st.write(f"- {item}")
    st.write("**What weakened:**")
    for item in narrative["what_weakened"]:
        st.write(f"- {item}")
    st.write(f"**Key tension:** {narrative['key_tension']}")
    st.write("**What to watch next:**")
    for item in narrative["what_to_watch_next"]:
        st.write(f"- {item}")

    _section_spacer(0.35)
    st.markdown("### Signals")
    bullish_col, bearish_col, neutral_col = st.columns(3)
    with bullish_col:
        st.markdown("#### Bullish signals")
        for item in signals["bullish"]:
            st.write(f"- {item}")
    with bearish_col:
        st.markdown("#### Bearish signals")
        for item in signals["bearish"]:
            st.write(f"- {item}")
    with neutral_col:
        st.markdown("#### Neutral / context signals")
        for item in signals["neutral"]:
            st.write(f"- {item}")


def _build_comparison_row(
    ticker: str,
    company_info_df: pd.DataFrame,
    metrics_df: pd.DataFrame,
) -> dict[str, Any]:
    """
    Build one comparison row using the latest available period.
    """
    info_row = _latest_info_row(company_info_df)
    quality_score = build_business_quality_score(metrics_df, company_info_df)

    return {
        "Ticker": ticker,
        "Company Name": safe_string(info_row.get("name") if hasattr(info_row, "get") else None, ticker),
        "Sector": safe_string(info_row.get("sector") if hasattr(info_row, "get") else None),
            "Market Cap": info_row.get("market_cap") if hasattr(info_row, "get") else None,
        "Revenue": latest_metric_value(metrics_df, "revenue"),
        "Revenue Growth": latest_metric_value(metrics_df, "revenue_growth_pct"),
        "EBITDA": latest_metric_value(metrics_df, "ebitda"),
        "EBITDA Margin": latest_metric_value(metrics_df, "ebitda_margin_pct"),
        "Net Income Margin": latest_metric_value(metrics_df, "net_income_margin_pct"),
        "Free Cash Flow": latest_metric_value(metrics_df, "free_cash_flow"),
        "Cash": latest_metric_value(metrics_df, "cash_and_equivalents"),
        "Debt": latest_metric_value(metrics_df, "total_debt"),
        "Net Cash / Debt": latest_metric_value(metrics_df, "net_cash_debt"),
        "P/S": info_row.get("price_to_sales") if hasattr(info_row, "get") else None,
        "P/E": info_row.get("trailing_pe") if hasattr(info_row, "get") else None,
        "EV/Revenue": info_row.get("ev_to_revenue") if hasattr(info_row, "get") else None,
        "Business Quality Score": quality_score["score"],
    }


def _format_comparison_table(comparison_df: pd.DataFrame) -> pd.DataFrame:
    """
    Format the comparison dataframe for display.
    """
    if not isinstance(comparison_df, pd.DataFrame) or comparison_df.empty:
        return pd.DataFrame()

    display_df = comparison_df.copy()
    money_columns = [
        "Market Cap",
        "Revenue",
        "EBITDA",
        "Free Cash Flow",
        "Cash",
        "Debt",
        "Net Cash / Debt",
    ]
    percent_columns = [
        "Revenue Growth",
        "EBITDA Margin",
        "Net Income Margin",
    ]
    multiple_columns = ["P/S", "EV/Revenue"]
    plain_number_columns = ["P/E", "Business Quality Score"]

    for column in money_columns:
        if column in display_df.columns:
            display_df[column] = display_df[column].apply(format_dollars_short)
    for column in percent_columns:
        if column in display_df.columns:
            display_df[column] = display_df[column].apply(_format_compare_percent)
    for column in multiple_columns:
        if column in display_df.columns:
            display_df[column] = display_df[column].apply(_format_multiple)
    for column in plain_number_columns:
        if column in display_df.columns:
            display_df[column] = display_df[column].apply(_format_plain_number)

    display_df = display_df.where(pd.notna(display_df), "N/A")
    return display_df


def _best_row_by_numeric(comparison_df: pd.DataFrame, column: str, ascending: bool = False) -> str:
    """
    Return a simple winner string for the comparison summary.
    """
    if column not in comparison_df.columns:
        return "N/A"
    numeric_series = pd.to_numeric(comparison_df[column], errors="coerce")
    valid_df = comparison_df.loc[numeric_series.notna()].copy()
    if valid_df.empty:
        return "N/A"
    valid_df["_sort"] = pd.to_numeric(valid_df[column], errors="coerce")
    best_row = valid_df.sort_values("_sort", ascending=ascending).iloc[0]
    return f"{best_row['Ticker']} ({best_row['Company Name']})"


def _display_best_worst_section(comparison_df: pd.DataFrame) -> None:
    """
    Render a simple best/worst ranking section for comparison mode.
    """
    cards = [
        ("Best Growth", _best_row_by_numeric(comparison_df, "Revenue Growth"), "Highest revenue growth", "positive"),
        ("Best Profitability", _best_row_by_numeric(comparison_df, "Net Income Margin"), "Highest net income margin", "positive"),
        ("Best Balance Sheet", _best_row_by_numeric(comparison_df, "Net Cash / Debt"), "Strongest net cash position", "positive"),
        ("Cheapest P/S", _best_row_by_numeric(comparison_df, "P/S", ascending=True), "Lowest price-to-sales", "neutral"),
        ("Highest Score", _best_row_by_numeric(comparison_df, "Business Quality Score"), "Best quality score", "positive"),
        ("Most Expensive P/S", _best_row_by_numeric(comparison_df, "P/S"), "Highest price-to-sales", "caution"),
    ]
    _render_metric_card_grid(cards)


def _display_comparison_summary(comparison_df: pd.DataFrame) -> None:
    """
    Render a simple comparison summary section.
    """
    cards = [
        ("Highest Revenue Growth", _best_row_by_numeric(comparison_df, "Revenue Growth"), "Top-line momentum leader", "positive"),
        ("Highest Net Income Margin", _best_row_by_numeric(comparison_df, "Net Income Margin"), "Best profitability", "positive"),
        ("Strongest Balance Sheet", _best_row_by_numeric(comparison_df, "Net Cash / Debt"), "Net cash leadership", "positive"),
        ("Lowest P/S", _best_row_by_numeric(comparison_df, "P/S", ascending=True), "Lowest sales multiple", "neutral"),
        ("Highest Quality Score", _best_row_by_numeric(comparison_df, "Business Quality Score"), "Rules-based quality leader", "positive"),
    ]
    _render_metric_card_grid(cards)


def _display_peer_summary_strip(comparison_df: pd.DataFrame) -> None:
    """
    Render a compact peer-comparison executive summary.
    """
    valuation_series = pd.to_numeric(comparison_df.get("P/S"), errors="coerce")
    growth_series = pd.to_numeric(comparison_df.get("Revenue Growth"), errors="coerce")
    score_series = pd.to_numeric(comparison_df.get("Business Quality Score"), errors="coerce")

    key_caveat = "Some valuation or financial fields may be unavailable across peers."
    if valuation_series.notna().any() and valuation_series.max() > 10:
        key_caveat = "At least one peer trades at a materially elevated sales multiple."
    elif growth_series.notna().any() and growth_series.min() < 0:
        key_caveat = "Growth dispersion is wide, with at least one peer showing contraction."

    items = [
        ("Best Overall", _best_row_by_numeric(comparison_df, "Business Quality Score"), "Highest quality score", "positive"),
        ("Cheapest Valuation", _best_row_by_numeric(comparison_df, "P/S", ascending=True), "Lowest price-to-sales", "neutral"),
        ("Strongest Growth", _best_row_by_numeric(comparison_df, "Revenue Growth"), "Highest revenue growth", "positive"),
        ("Key Caveat", key_caveat, "Important context across the peer set", "caution"),
    ]
    _render_summary_strip(items)
    insight = (
        f"Best overall: {_best_row_by_numeric(comparison_df, 'Business Quality Score')}. "
        f"Cheapest valuation: {_best_row_by_numeric(comparison_df, 'P/S', ascending=True)}. "
        f"Strongest growth: {_best_row_by_numeric(comparison_df, 'Revenue Growth')}. "
        f"Key caveat: {key_caveat}"
    )
    _render_dbr_insight(insight)


def _display_comparison_charts(comparison_df: pd.DataFrame) -> None:
    """
    Render comparison-mode charts below the summary.
    """
    _render_panel_header("Comparison Charts")
    chart_specs = [
        ("Revenue Growth", "Revenue Growth by Ticker", "Revenue Growth", "percent", "#38bdf8", None),
        ("Net Income Margin", "Net Income Margin by Ticker", "Net Income Margin", "percent", "#22c55e", None),
        ("Free Cash Flow", "Free Cash Flow by Ticker", "Free Cash Flow", "currency", "#f59e0b", None),
        ("Net Cash / Debt", "Net Cash / Debt by Ticker", "Net Cash / Debt", "currency", "#8b5cf6", None),
        ("P/S", "P/S Multiple by Ticker", "P/S", "multiple", "#ef4444", None),
        ("Business Quality Score", "Business Quality Score by Ticker", "Score", "score", "#38bdf8", [0, 100]),
    ]

    for first_spec, second_spec in zip(chart_specs[::2], chart_specs[1::2]):
        left_col, right_col = st.columns(2)
        with left_col:
            fig = create_comparison_bar_chart(
                comparison_df,
                value_column=first_spec[0],
                title=first_spec[1],
                yaxis_title=first_spec[2],
                tickformat=first_spec[3],
                color=first_spec[4],
                yaxis_range=first_spec[5],
            )
            st.plotly_chart(fig, use_container_width=True)
        with right_col:
            fig = create_comparison_bar_chart(
                comparison_df,
                value_column=second_spec[0],
                title=second_spec[1],
                yaxis_title=second_spec[2],
                tickformat=second_spec[3],
                color=second_spec[4],
                yaxis_range=second_spec[5],
            )
            st.plotly_chart(fig, use_container_width=True)


def _display_comparison_price_charts(
    price_history_map: dict[str, pd.DataFrame],
    price_timeframe: str,
) -> None:
    """
    Render multi-ticker comparison price charts.
    """
    _render_panel_header("Price Comparison")
    normalized_fig = create_multi_ticker_price_chart(
        price_history_map,
        price_period=price_timeframe,
        normalized=True,
    )
    st.plotly_chart(normalized_fig, use_container_width=True)

    raw_fig = create_multi_ticker_price_chart(
        price_history_map,
        price_period=price_timeframe,
        normalized=False,
    )
    st.plotly_chart(raw_fig, use_container_width=True)


def _run_comparison_analysis(
    tickers: list[str],
    financial_period: str,
    price_timeframe: str,
) -> None:
    """
    Run comparison mode across multiple companies using the latest available period for each.
    """
    comparison_rows: list[dict[str, Any]] = []
    failed_tickers: list[str] = []
    price_history_map: dict[str, pd.DataFrame] = {}

    with st.spinner(f"Running comparison for {', '.join(tickers)}..."):
        for ticker in tickers:
            try:
                data = _cached_financial_data(ticker, financial_period, price_timeframe)
                company_info_df = data.get("company_info")
                metrics_df = calculate_financial_metrics(
                    income_statement=data.get("income_statement"),
                    balance_sheet=data.get("balance_sheet"),
                    cash_flow_statement=data.get("cash_flow_statement"),
                    sector=(
                        company_info_df.iloc[0].get("sector")
                        if isinstance(company_info_df, pd.DataFrame) and not company_info_df.empty
                        else None
                    ),
                )
                comparison_rows.append(_build_comparison_row(ticker, company_info_df, metrics_df))
                price_history_map[ticker] = data.get("price_history", pd.DataFrame())
            except Exception:
                failed_tickers.append(ticker)

    if not comparison_rows:
        st.error("Comparison data could not be loaded for the selected tickers.")
        return

    comparison_df = pd.DataFrame(comparison_rows)
    _render_panel_header("Peer Summary", copy="Top-level read on leadership, valuation, and caveats across the selected peer set.")
    _display_peer_summary_strip(comparison_df)
    _section_spacer(0.18)
    _render_panel_header("Comparison Summary")
    _display_comparison_summary(comparison_df)
    _section_spacer(0.35)
    _render_panel_header("Best / Worst")
    _display_best_worst_section(comparison_df)
    _section_spacer(0.35)
    _display_comparison_price_charts(price_history_map, price_timeframe)
    _section_spacer(0.35)
    _display_comparison_charts(comparison_df)
    _section_spacer(0.35)
    _render_panel_header("Comparison Table")
    st.dataframe(_format_comparison_table(comparison_df), use_container_width=True, hide_index=True)

    if failed_tickers:
        _render_inline_alert(f"Some tickers could not be loaded: {', '.join(failed_tickers)}", tone="warning")


def _display_portfolio_metrics(metrics: dict[str, Any]) -> None:
    """
    Render portfolio summary KPI cards.
    """
    metric_cards = [
        ("Cumulative Return", format_percent(metrics.get("cumulative_return")), "Portfolio total return", _tone_from_numeric(metrics.get("cumulative_return"))),
        ("Annualized Return", format_percent(metrics.get("annualized_return")), "Annualized", _tone_from_numeric(metrics.get("annualized_return"))),
        ("Annualized Volatility", format_percent(metrics.get("annualized_volatility")), "Risk", "caution"),
        ("Sharpe Ratio", _format_plain_number(metrics.get("sharpe_ratio")), "Risk-free rate = 0", _tone_from_numeric(metrics.get("sharpe_ratio"))),
        ("Max Drawdown", format_percent(metrics.get("max_drawdown")), "Worst peak-to-trough", _tone_from_numeric(metrics.get("max_drawdown"), invert=True)),
    ]
    _render_metric_card_grid(metric_cards)


def _display_benchmark_summary(analysis: dict[str, Any]) -> None:
    """
    Render benchmark-relative KPI cards for the active portfolio run.
    """
    benchmark_metrics = analysis.get("benchmark_metrics", {})
    benchmark_ticker = analysis.get("benchmark_ticker", "Benchmark")
    benchmark_cards = [
        ("Portfolio Return", format_percent(analysis.get("metrics", {}).get("cumulative_return")), "Total return", _tone_from_numeric(analysis.get("metrics", {}).get("cumulative_return"))),
        (f"{benchmark_ticker} Return", format_percent(benchmark_metrics.get("cumulative_return")), "Benchmark total return", "neutral"),
        ("Excess Return", format_percent(benchmark_metrics.get("excess_return")), "Portfolio minus benchmark", _tone_from_numeric(benchmark_metrics.get("excess_return"))),
        ("Beta", _format_plain_number(benchmark_metrics.get("beta")), "Sensitivity vs benchmark", "neutral"),
        ("Correlation", _format_plain_number(benchmark_metrics.get("correlation")), "Daily return correlation", "neutral"),
        ("Max Drawdown Diff", format_percent(benchmark_metrics.get("max_drawdown_difference")), "Portfolio minus benchmark", _tone_from_numeric(benchmark_metrics.get("max_drawdown_difference"), invert=True)),
    ]
    _render_metric_card_grid(benchmark_cards)

    tracking_error = benchmark_metrics.get("tracking_error")
    if pd.notna(pd.to_numeric(tracking_error, errors="coerce")):
        st.caption(f"Tracking error: {format_percent(tracking_error)}")


def _display_portfolio_summary_strip(analysis: dict[str, Any]) -> None:
    """
    Render a compact portfolio executive summary.
    """
    metrics = analysis.get("metrics", {})
    benchmark_metrics = analysis.get("benchmark_metrics", {})
    warnings_list = analysis.get("warnings", [])
    volatility = pd.to_numeric(metrics.get("annualized_volatility"), errors="coerce")
    max_drawdown = pd.to_numeric(metrics.get("max_drawdown"), errors="coerce")

    risk_level = "Moderate"
    risk_tone = "neutral"
    if pd.notna(volatility):
        if float(volatility) > 0.25:
            risk_level = "High"
            risk_tone = "negative"
        elif float(volatility) < 0.15:
            risk_level = "Low"
            risk_tone = "positive"

    drawdown_read = "Contained"
    drawdown_tone = "positive"
    if pd.notna(max_drawdown):
        if float(max_drawdown) < -0.25:
            drawdown_read = "Deep drawdown"
            drawdown_tone = "negative"
        elif float(max_drawdown) < -0.15:
            drawdown_read = "Moderate drawdown"
            drawdown_tone = "caution"

    concentration_text = "Balanced"
    concentration_tone = "neutral"
    if any("concentration" in message.lower() or "correlation" in message.lower() for message in warnings_list):
        concentration_text = "Elevated concentration/correlation"
        concentration_tone = "caution"

    items = [
        ("Return vs Benchmark", format_percent(benchmark_metrics.get("excess_return")), "Excess return", _tone_from_numeric(benchmark_metrics.get("excess_return"))),
        ("Risk Level", risk_level, format_percent(volatility), risk_tone),
        ("Drawdown Read", drawdown_read, format_percent(max_drawdown), drawdown_tone),
        ("Concentration", concentration_text, "Positioning / correlation context", concentration_tone),
    ]
    _render_summary_strip(items)
    insight = (
        f"Return vs benchmark is {format_percent(benchmark_metrics.get('excess_return'))}, "
        f"with a {risk_level.lower()} risk profile. "
        f"Drawdown has been {drawdown_read.lower()}, and the current portfolio shows {concentration_text.lower()}."
    )
    _render_dbr_insight(insight)


def _display_what_if_results(what_if_result: dict[str, Any]) -> None:
    """
    Render the current vs proposed portfolio comparison and summary.
    """
    st.markdown("## What-If Summary")
    for line in what_if_result.get("summary", []):
        st.markdown(f"- {line}")

    comparison_rows = [
        {
            "Metric": "Cumulative Return",
            "Current": format_percent(what_if_result.get("current_metrics", {}).get("cumulative_return")),
            "Proposed": format_percent(what_if_result.get("proposed_metrics", {}).get("cumulative_return")),
        },
        {
            "Metric": "Annualized Volatility",
            "Current": format_percent(what_if_result.get("current_metrics", {}).get("annualized_volatility")),
            "Proposed": format_percent(what_if_result.get("proposed_metrics", {}).get("annualized_volatility")),
        },
        {
            "Metric": "Sharpe Ratio",
            "Current": _format_plain_number(what_if_result.get("current_metrics", {}).get("sharpe_ratio")),
            "Proposed": _format_plain_number(what_if_result.get("proposed_metrics", {}).get("sharpe_ratio")),
        },
        {
            "Metric": "Max Drawdown",
            "Current": format_percent(what_if_result.get("current_metrics", {}).get("max_drawdown")),
            "Proposed": format_percent(what_if_result.get("proposed_metrics", {}).get("max_drawdown")),
        },
        {
            "Metric": "Largest Holding",
            "Current": format_percent(what_if_result.get("current_largest_holding", 0.0) / 100.0),
            "Proposed": format_percent(what_if_result.get("proposed_largest_holding", 0.0) / 100.0),
        },
        {
            "Metric": "Cash Allocation",
            "Current": format_percent(what_if_result.get("current_cash_allocation", 0.0) / 100.0),
            "Proposed": format_percent(what_if_result.get("proposed_cash_allocation", 0.0) / 100.0),
        },
    ]
    st.dataframe(pd.DataFrame(comparison_rows), use_container_width=True, hide_index=True)


def _run_portfolio_analysis() -> None:
    """
    Execute portfolio analysis mode.
    """
    _render_page_header(
        "Portfolio Lab",
        "Analyze a custom basket of holdings with benchmark context, drawdown diagnostics, and scenario testing.",
    )
    if "portfolio_holdings_seed" not in st.session_state:
        st.session_state["portfolio_holdings_seed"] = DEFAULT_PORTFOLIO.copy()
    if "portfolio_editor_version" not in st.session_state:
        st.session_state["portfolio_editor_version"] = 0
    if "proposed_portfolio_seed" not in st.session_state:
        st.session_state["proposed_portfolio_seed"] = DEFAULT_PORTFOLIO.copy()
    if "proposed_portfolio_editor_version" not in st.session_state:
        st.session_state["proposed_portfolio_editor_version"] = 0

    _open_settings_panel("Analysis Settings")
    timeframe_col, benchmark_col, custom_col, run_toolbar_col = st.columns([1.05, 1.0, 1.15, 0.9])
    with timeframe_col:
        price_timeframe = st.selectbox("Stock Price Timeframe", ["6mo", "1y", "2y", "5y", "max"], index=3)
    with benchmark_col:
        benchmark_choice = st.selectbox("Benchmark", ["SPY", "QQQ", "DIA", "IWM", "Custom"], index=0)
    with custom_col:
        benchmark_custom = st.text_input(
            "Custom Benchmark",
            value="SPY" if benchmark_choice == "Custom" else benchmark_choice,
            help="Enter a public market ETF or ticker if you want a custom benchmark.",
        ).strip().upper()
    with run_toolbar_col:
        st.markdown('<div style="height:1.55rem;"></div>', unsafe_allow_html=True)
        run_clicked = st.button("Run Portfolio Analysis", type="primary", use_container_width=True)
    benchmark_ticker = benchmark_custom if benchmark_choice == "Custom" and benchmark_custom else benchmark_choice

    _render_panel_header("Holdings Editor", copy="Add, edit, or delete holdings. Use CASH for cash allocation.")
    portfolio_editor_key = f"portfolio_holdings_editor_{st.session_state['portfolio_editor_version']}"
    holdings_input = st.data_editor(
        st.session_state["portfolio_holdings_seed"],
        use_container_width=True,
        num_rows="dynamic",
        hide_index=True,
        column_config={
            "Ticker": st.column_config.TextColumn("Ticker"),
            "Weight %": st.column_config.NumberColumn("Weight %", format="%.2f"),
        },
        key=portfolio_editor_key,
    )
    st.session_state["portfolio_holdings_seed"] = holdings_input.copy()
    normalize_weights = st.checkbox("Normalize weights to 100%")

    holdings_df, holding_warnings = clean_holdings(holdings_input, normalize_weights=normalize_weights)
    total_weight = float(pd.to_numeric(holdings_df.get("Weight %", pd.Series(dtype=float)), errors="coerce").fillna(0.0).sum()) if not holdings_df.empty else 0.0
    st.write(f"**Total Weight:** {total_weight:.1f}%")
    for warning in holding_warnings:
        _render_inline_alert(warning, tone="warning")

    action_col, reset_col = st.columns([1, 1])
    with action_col:
        st.markdown('<div class="dbr-section-copy">Normalize before running if weights do not equal 100%.</div>', unsafe_allow_html=True)
    with reset_col:
        reset_clicked = st.button("Reset Portfolio", use_container_width=True)
    _close_settings_panel()

    if reset_clicked:
        st.session_state["portfolio_holdings_seed"] = DEFAULT_PORTFOLIO.copy()
        st.session_state["portfolio_editor_version"] += 1
        st.session_state.pop("portfolio_analysis_result", None)
        st.session_state.pop("portfolio_what_if_result", None)
        st.session_state.pop("portfolio_what_if_analysis", None)
        st.rerun()

    if holdings_df.empty:
        st.info("Add at least one holding to analyze the portfolio.")
        return

    if abs(total_weight - 100.0) > 0.01 and not normalize_weights:
        _render_inline_alert("Portfolio weights must equal 100% unless normalization is enabled.", tone="warning")
        if "portfolio_analysis_result" not in st.session_state:
            return

    if run_clicked:
        if abs(total_weight - 100.0) > 0.01 and not normalize_weights:
            return
        with st.spinner("Running portfolio analysis..."):
            price_history_map: dict[str, pd.DataFrame] = {}
            for ticker in holdings_df["Ticker"].tolist():
                if ticker == "CASH":
                    continue
                price_history_map[ticker] = _cached_price_history(ticker, price_timeframe)
            analysis = analyze_portfolio(
                holdings_df,
                price_history_map,
                benchmark_history=_cached_price_history(benchmark_ticker, price_timeframe),
                benchmark_ticker=benchmark_ticker,
            )
        st.session_state["portfolio_analysis_result"] = analysis
        st.session_state["portfolio_analysis_holdings"] = holdings_df.copy()
        st.session_state["portfolio_analysis_timeframe"] = price_timeframe
        st.session_state["portfolio_analysis_benchmark"] = benchmark_ticker

    analysis = st.session_state.get("portfolio_analysis_result")
    if analysis is None:
        st.info("Set your holdings and click Run Portfolio Analysis.")
        return

    _section_spacer(0.25)
    _render_panel_header("Executive Summary", copy="Return, risk, drawdown, and concentration reads for the current portfolio versus the chosen benchmark.")
    _display_portfolio_summary_strip(analysis)
    _section_spacer(0.18)
    _render_panel_header("Portfolio Scorecard")
    _display_portfolio_metrics(analysis.get("metrics", {}))
    _section_spacer(0.35)

    if analysis.get("warnings", []):
        warning_html = "".join(f"<div>{escape(str(message))}</div>" for message in analysis.get("warnings", []))
        st.markdown(f'<div class="dbr-inline-alert">{warning_html}</div>', unsafe_allow_html=True)

    if analysis.get("benchmark_available"):
        _render_panel_header("Benchmark Comparison")
        _display_benchmark_summary(analysis)
        _section_spacer(0.35)
    else:
        _render_inline_alert("Benchmark data was unavailable for the selected benchmark ticker.", tone="warning")

    _render_panel_header("Portfolio Charts")
    hero_benchmark_chart = create_portfolio_vs_benchmark_chart(
        analysis.get("portfolio_equity", pd.Series(dtype="float64")),
        analysis.get("benchmark_equity", pd.Series(dtype="float64")),
        analysis.get("benchmark_ticker", benchmark_ticker),
    ) if analysis.get("benchmark_available") else create_portfolio_cumulative_chart(
        analysis.get("portfolio_equity", pd.Series(dtype="float64"))
    )
    st.plotly_chart(hero_benchmark_chart, use_container_width=True)

    left_col, right_col = st.columns(2)
    with left_col:
        st.plotly_chart(
            create_holdings_comparison_chart(analysis.get("holdings_normalized_df", pd.DataFrame())),
            use_container_width=True,
        )
        st.plotly_chart(
            create_allocation_chart(analysis.get("weights_df", holdings_df)),
            use_container_width=True,
        )
    with right_col:
        if analysis.get("benchmark_available"):
            st.plotly_chart(
                create_drawdown_comparison_chart(
                    analysis.get("portfolio_drawdown", pd.Series(dtype="float64")),
                    analysis.get("benchmark_drawdown", pd.Series(dtype="float64")),
                    analysis.get("benchmark_ticker", benchmark_ticker),
                ),
                use_container_width=True,
            )
        else:
            st.plotly_chart(
                create_drawdown_chart(analysis.get("portfolio_drawdown", pd.Series(dtype="float64"))),
                use_container_width=True,
            )
        st.plotly_chart(
            create_correlation_heatmap(analysis.get("correlation_df", pd.DataFrame())),
            use_container_width=True,
        )

    _section_spacer(0.55)
    _render_panel_header(
        "What-If Analysis",
        copy="Build a proposed portfolio scenario and compare it with the latest current portfolio run.",
    )
    _render_panel_header("Proposed Holdings", copy="Add, edit, or delete proposed holdings. Use CASH for cash allocation.")
    proposed_editor_key = f"proposed_portfolio_editor_{st.session_state['proposed_portfolio_editor_version']}"
    proposed_input = st.data_editor(
        st.session_state["proposed_portfolio_seed"],
        use_container_width=True,
        num_rows="dynamic",
        hide_index=True,
        column_config={
            "Ticker": st.column_config.TextColumn("Ticker"),
            "Weight %": st.column_config.NumberColumn("Weight %", format="%.2f"),
        },
        key=proposed_editor_key,
    )
    st.session_state["proposed_portfolio_seed"] = proposed_input.copy()
    normalize_proposed_weights = st.checkbox("Normalize proposed weights to 100%")
    proposed_holdings_df, proposed_warnings = clean_holdings(
        proposed_input,
        normalize_weights=normalize_proposed_weights,
    )
    proposed_total_weight = (
        float(
            pd.to_numeric(
                proposed_holdings_df.get("Weight %", pd.Series(dtype=float)),
                errors="coerce",
            ).fillna(0.0).sum()
        )
        if not proposed_holdings_df.empty
        else 0.0
    )
    st.write(f"**Proposed Total Weight:** {proposed_total_weight:.1f}%")
    for warning in proposed_warnings:
        _render_inline_alert(warning, tone="warning")

    what_if_col, proposed_reset_col = st.columns(2)
    with what_if_col:
        run_what_if_clicked = st.button("Run What-If", type="primary", use_container_width=True)
    with proposed_reset_col:
        reset_proposed_clicked = st.button("Reset Proposed Portfolio", use_container_width=True)

    if reset_proposed_clicked:
        st.session_state["proposed_portfolio_seed"] = DEFAULT_PORTFOLIO.copy()
        st.session_state["proposed_portfolio_editor_version"] += 1
        st.session_state.pop("portfolio_what_if_result", None)
        st.rerun()

    if run_what_if_clicked:
        if proposed_holdings_df.empty:
            _render_inline_alert("Add at least one proposed holding to run what-if analysis.", tone="warning")
        elif abs(proposed_total_weight - 100.0) > 0.01 and not normalize_proposed_weights:
            _render_inline_alert("Proposed portfolio weights must equal 100% unless normalization is enabled.", tone="warning")
        else:
            with st.spinner("Running what-if analysis..."):
                proposed_price_history_map: dict[str, pd.DataFrame] = {}
                all_tickers = sorted(
                    {
                        ticker
                        for ticker in pd.concat(
                            [holdings_df["Ticker"], proposed_holdings_df["Ticker"]],
                            ignore_index=True,
                        ).tolist()
                        if ticker != "CASH"
                    }
                )
                for ticker in all_tickers:
                    proposed_price_history_map[ticker] = _cached_price_history(ticker, price_timeframe)

                proposed_analysis = analyze_portfolio(
                    proposed_holdings_df,
                    proposed_price_history_map,
                    benchmark_history=_cached_price_history(benchmark_ticker, price_timeframe),
                    benchmark_ticker=benchmark_ticker,
                )
                what_if_result = compare_portfolio_scenarios(
                    analysis,
                    proposed_analysis,
                    st.session_state.get("portfolio_analysis_holdings", holdings_df),
                    proposed_holdings_df,
                )

            st.session_state["portfolio_what_if_result"] = what_if_result
            st.session_state["portfolio_what_if_analysis"] = proposed_analysis
            st.session_state["portfolio_what_if_holdings"] = proposed_holdings_df.copy()

    what_if_result = st.session_state.get("portfolio_what_if_result")
    if what_if_result is not None:
        _section_spacer(0.25)
        _display_what_if_results(what_if_result)


def _display_charts(charts: dict[str, Any], metrics_df: pd.DataFrame, company_info_df: pd.DataFrame) -> None:
    """
    Render non-empty charts inside Streamlit tabs.
    """
    if not charts:
        st.info("No chartable data is available for this ticker.")
        return

    overview_tab, profitability_tab, cash_tab, stock_tab, quality_tab, narrative_tab, metrics_tab = st.tabs(
        ["Overview", "Profitability", "Cash Flow & Balance Sheet", "Stock Price", "Quality & Valuation", "Narrative", "Metrics"]
    )

    with overview_tab:
        if charts.get("revenue_chart") is not None:
            st.plotly_chart(charts["revenue_chart"], use_container_width=True)
        else:
            st.info("Revenue chart data is unavailable.")

    with profitability_tab:
        if charts.get("margin_chart") is not None:
            st.plotly_chart(charts["margin_chart"], use_container_width=True)
        if charts.get("income_fcf_chart") is not None:
            st.plotly_chart(charts["income_fcf_chart"], use_container_width=True)
        if charts.get("margin_chart") is None and charts.get("income_fcf_chart") is None:
            st.info("Profitability chart data is unavailable.")

    with cash_tab:
        if charts.get("cash_debt_chart") is not None:
            st.plotly_chart(charts["cash_debt_chart"], use_container_width=True)
        if charts.get("cash_debt_chart") is None:
            st.info("Cash flow and balance sheet chart data is unavailable.")

    with stock_tab:
        if charts.get("stock_price_chart") is not None:
            st.plotly_chart(charts["stock_price_chart"], use_container_width=True)
        else:
            st.info("Stock price data is unavailable.")

    with quality_tab:
        _display_business_quality_score(metrics_df, company_info_df)
        _display_valuation_section(company_info_df)

    with narrative_tab:
        _display_narrative_tab(metrics_df, company_info_df)

    with metrics_tab:
        _display_metrics_table(metrics_df)

def _prepare_metrics_table(metrics_df: pd.DataFrame) -> pd.DataFrame:
    """
    Build the compact metrics table shown in Streamlit.
    """
    if not isinstance(metrics_df, pd.DataFrame) or metrics_df.empty:
        return pd.DataFrame()

    column_map = {
        "Period": "Period",
        "revenue": "Revenue",
        "revenue_growth_pct": "Revenue Growth",
        "ebitda": "EBITDA",
        "ebitda_margin_pct": "EBITDA Margin",
        "gross_margin_pct": "Gross Margin",
        "operating_margin_pct": "Operating Margin",
        "net_income": "Net Income",
        "net_income_margin_pct": "Net Income Margin",
        "free_cash_flow": "Free Cash Flow",
        "cash_and_equivalents": "Cash",
        "total_debt": "Debt",
        "net_cash_debt": "Net Cash / Debt",
    }

    available_columns = [column for column in column_map if column in metrics_df.columns]
    if not available_columns:
        return pd.DataFrame()

    display_df = metrics_df[available_columns].copy().rename(columns=column_map)

    money_columns = [
        "Revenue",
        "EBITDA",
        "Net Income",
        "Free Cash Flow",
        "Cash",
        "Debt",
        "Net Cash / Debt",
    ]
    percent_columns = [
        "Revenue Growth",
        "EBITDA Margin",
        "Gross Margin",
        "Operating Margin",
        "Net Income Margin",
    ]

    if "Period" in display_df.columns:
        display_df["Period"] = display_df["Period"].astype("string").fillna("N/A")

    for column in money_columns:
        if column in display_df.columns:
            display_df[column] = display_df[column].apply(_format_table_money)

    for column in percent_columns:
        if column in display_df.columns:
            display_df[column] = display_df[column].apply(_format_table_percent)

    display_df = display_df.where(pd.notna(display_df), "N/A")
    return display_df


def _display_metrics_table(metrics_df: pd.DataFrame) -> None:
    display_df = _prepare_metrics_table(metrics_df)
    if display_df.empty:
        st.info("No metrics are available for this ticker.")
        return

    st.dataframe(display_df, use_container_width=True, hide_index=True)


def _limit_metrics_periods(metrics_df: pd.DataFrame, limit_label: str) -> pd.DataFrame:
    """
    Limit the metrics view to the latest N periods when requested.
    """
    if not isinstance(metrics_df, pd.DataFrame) or metrics_df.empty:
        return metrics_df

    limit_map = {
        "Latest 4": 4,
        "Latest 8": 8,
        "Latest 12": 12,
        "All": None,
    }
    limit = limit_map.get(limit_label)
    if limit is None:
        return metrics_df.copy()
    return metrics_df.tail(limit).reset_index(drop=True)


def _render_data_warnings(metrics_df: pd.DataFrame, period_type: str) -> None:
    """
    Render non-fatal data warnings without breaking the dashboard.
    """
    warnings_list = metrics_df.attrs.get("warnings", []) if isinstance(metrics_df, pd.DataFrame) else []
    for message in warnings_list:
        _render_inline_alert(message, tone="warning")

    if period_type == "quarterly" and (not isinstance(metrics_df, pd.DataFrame) or metrics_df.empty):
        _render_inline_alert(
            "Quarterly financial statement data was not available for this ticker. Some companies, ETFs, funds, or unsupported symbols may not expose quarterly statements through yfinance."
        )
    elif not isinstance(metrics_df, pd.DataFrame) or metrics_df.empty:
        _render_inline_alert(
            "Financial statement data was not available for this ticker. This may happen for ETFs, funds, or unsupported symbols."
        )


def _latest_statement_date(data: dict[str, pd.DataFrame]) -> pd.Timestamp | None:
    """
    Return the latest statement date available across the loaded financial statements.
    """
    dates: list[pd.Timestamp] = []
    for key in ("income_statement", "balance_sheet", "cash_flow_statement"):
        frame = data.get(key, pd.DataFrame())
        if isinstance(frame, pd.DataFrame) and not frame.empty and "Date" in frame.columns:
            series = pd.to_datetime(frame["Date"], errors="coerce").dropna()
            if not series.empty:
                dates.append(series.iloc[-1])
    if not dates:
        return None
    return max(dates)


def _display_data_availability(data: dict[str, pd.DataFrame], period_type: str) -> None:
    """
    Render a compact diagnostic expander for data availability.
    """
    summary = summarize_data_availability(data, period_type=period_type)
    latest_statement_date = _latest_statement_date(data)
    latest_price_date = summary.get("latest_stock_price_date", "N/A")

    with st.expander("Data availability"):
        st.write(f"Latest financial period available: {summary.get('latest_financial_period', 'N/A')}")
        st.write(f"Number of financial periods loaded: {summary.get('financial_periods_loaded', 0)}")
        st.write(f"Selected financial period type: {summary.get('selected_period_type', 'N/A').title()}")
        st.write(f"Stock price latest date: {latest_price_date}")
        st.write(f"{summary.get('selected_period_type', 'N/A').title()} income statement returned: {'Yes' if summary.get('income_statement_available') else 'No'}")
        st.write(f"{summary.get('selected_period_type', 'N/A').title()} balance sheet returned: {'Yes' if summary.get('balance_sheet_available') else 'No'}")
        st.write(f"{summary.get('selected_period_type', 'N/A').title()} cash flow returned: {'Yes' if summary.get('cash_flow_statement_available') else 'No'}")
        st.markdown(
            '<div class="dbr-muted-note">EBITDA is often unavailable or less meaningful for banks, lenders, insurers, and other financial companies.</div>',
            unsafe_allow_html=True,
        )

    if latest_statement_date is not None and latest_price_date != "N/A":
        latest_price_ts = pd.to_datetime(latest_price_date, errors="coerce")
        if pd.notna(latest_price_ts) and latest_price_ts.year > latest_statement_date.year:
            st.info(
                "Price data may be more current than financial statement data. This usually means the latest quarter has not been loaded by the source yet."
            )


def _run_analysis(
    ticker: str,
    financial_period: str,
    price_timeframe: str,
    display_periods: str,
) -> None:
    """
    Execute the end-to-end analysis flow and render results in the app.
    """
    with st.spinner(f"Running analysis for {ticker.upper()}..."):
        data = _cached_financial_data(ticker, financial_period, price_timeframe)
        metrics_df_all = calculate_financial_metrics(
            income_statement=data.get("income_statement"),
            balance_sheet=data.get("balance_sheet"),
            cash_flow_statement=data.get("cash_flow_statement"),
            sector=(
                data.get("company_info").iloc[0].get("sector")
                if isinstance(data.get("company_info"), pd.DataFrame) and not data.get("company_info").empty
                else None
            ),
        )
        metrics_df = _limit_metrics_periods(metrics_df_all, display_periods)
        metrics_df.attrs["warnings"] = metrics_df_all.attrs.get("warnings", [])
        charts = create_all_charts(
            metrics_df=metrics_df,
            price_history_df=data.get("price_history"),
            ticker=ticker,
            price_period=price_timeframe,
        )

    company_info_df = data.get("company_info")
    is_financial = _is_financial_company(company_info_df)
    _display_company_header(ticker, company_info_df, metrics_df)
    _section_spacer(0.2)
    _render_panel_header("Executive Summary", copy="Top-down read on quality, growth, profitability, and the main watch item.")
    _display_company_summary_strip(metrics_df, company_info_df)
    _section_spacer(0.18)
    _display_kpis(metrics_df)
    _section_spacer(0.45)
    _display_quality_flags(metrics_df)
    _section_spacer(0.35)
    _render_data_warnings(metrics_df, financial_period.lower())
    _display_data_availability(data, financial_period.lower())

    if is_financial:
        _render_inline_alert(
            "Note: For financial companies, free cash flow and traditional margin metrics can be less useful because cash flow statements reflect lending, deposits, and balance-sheet activity."
        )

    _section_spacer(0.35)
    _display_executive_snapshot(metrics_df, is_financial)
    _section_spacer(0.45)
    _display_charts(charts, metrics_df, company_info_df)


def main() -> None:
    """
    Streamlit entrypoint for the DBR Research Terminal UI.
    """
    _configure_page()
    page = _render_sidebar()

    if page == "Home":
        _render_home_page()
    elif page == "Company Research":
        _render_page_header(
            "Company Research",
            "Analyze one ticker using reported financials, valuation, quality signals, rules-based narrative, and market behavior.",
        )

        _section_spacer(0.25)
        _open_settings_panel("Analysis Settings")
        input_col, period_col, timeframe_col, count_col, run_col = st.columns([2.6, 1.2, 1.2, 1.2, 0.9])
        with input_col:
            ticker = st.text_input(
                "Ticker Symbol",
                value="SOFI",
                max_chars=15,
                help="Enter a public company ticker. ETFs may not have financial statements.",
            ).strip().upper()
        with period_col:
            financial_period = st.selectbox("Financial Period", ["Annual", "Quarterly"], index=0)
        with timeframe_col:
            price_timeframe = st.selectbox("Stock Price Timeframe", ["6mo", "1y", "2y", "5y", "max"], index=3)
        with count_col:
            display_periods = st.selectbox("Financial Periods Shown", ["Latest 4", "Latest 8", "Latest 12", "All"], index=1)
        with run_col:
            st.markdown('<div style="height:1.55rem;"></div>', unsafe_allow_html=True)
            run_clicked = st.button("Run Analysis", type="primary", use_container_width=True)
        _close_settings_panel()

        if run_clicked:
            try:
                if not ticker:
                    st.error("Enter a ticker symbol before running analysis.")
                    return
                _run_analysis(
                    ticker=ticker,
                    financial_period=financial_period,
                    price_timeframe=price_timeframe,
                    display_periods=display_periods,
                )
            except Exception as exc:
                st.error(f"Analysis failed for {ticker}: {exc}")
        else:
            st.info("Enter a ticker symbol and click Run Analysis.")

    elif page == "Peer Comparison":
        _render_page_header(
            "Peer Comparison",
            "Compare multiple public companies on growth, profitability, valuation, balance sheet strength, and stock performance.",
        )

        _section_spacer(0.25)
        _open_settings_panel("Analysis Settings")
        input_col, period_col, timeframe_col, run_col = st.columns([3.0, 1.3, 1.3, 0.9])
        with input_col:
            comparison_input = st.text_input(
                "Ticker Symbols",
                value="SOFI, HOOD, AFRM",
                help="Enter comma-separated public company tickers.",
            ).strip().upper()
        with period_col:
            financial_period = st.selectbox("Financial Period", ["Annual", "Quarterly"], index=0)
        with timeframe_col:
            price_timeframe = st.selectbox("Stock Price Timeframe", ["6mo", "1y", "2y", "5y", "max"], index=3)
        with run_col:
            st.markdown('<div style="height:1.55rem;"></div>', unsafe_allow_html=True)
            run_clicked = st.button("Run Comparison", type="primary", use_container_width=True)
        _close_settings_panel()

        if run_clicked:
            try:
                tickers = _parse_ticker_list(comparison_input)
                if not tickers:
                    st.error("Enter at least one ticker for comparison.")
                    return
                _run_comparison_analysis(
                    tickers=tickers,
                    financial_period=financial_period,
                    price_timeframe=price_timeframe,
                )
            except Exception as exc:
                st.error(f"Comparison analysis failed: {exc}")
        else:
            st.info("Enter one or more tickers and click Run Comparison.")

    elif page == "Portfolio Lab":
        _section_spacer(0.25)
        _run_portfolio_analysis()

    st.markdown(
        """
        <div class="dbr-footer">
            DBR Research Terminal is a rules-based research aid. Data is sourced from Yahoo Finance/yfinance and may be delayed or incomplete. Not investment advice.
        </div>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
