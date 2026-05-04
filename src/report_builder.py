from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
from plotly.io import to_html


def format_money(value: Any) -> str:
    """
    Format numeric values into readable dollar strings.
    """
    if value is None or pd.isna(value):
        return "N/A"

    value = float(value)
    abs_value = abs(value)

    if abs_value >= 1_000_000_000:
        return f"${value / 1_000_000_000:.2f}B"
    if abs_value >= 1_000_000:
        return f"${value / 1_000_000:.2f}M"
    if abs_value >= 1_000:
        return f"${value / 1_000:.2f}K"
    return f"${value:,.2f}"


def format_percent(value: Any) -> str:
    """
    Format decimal ratios as percentages.
    """
    if value is None or pd.isna(value):
        return "N/A"
    return f"{float(value):.2%}"


def safe_string(value: Any, default: str = "N/A") -> str:
    """
    Convert optional values to strings without leaking NaN into output.
    """
    if value is None:
        return default
    if isinstance(value, float) and pd.isna(value):
        return default
    text = str(value).strip()
    return text if text else default


def latest_metric_value(metrics_df: pd.DataFrame, column: str) -> Any:
    """
    Return the most recent non-null value for a metric column.
    """
    if not isinstance(metrics_df, pd.DataFrame) or metrics_df.empty or column not in metrics_df.columns:
        return None

    series = pd.to_numeric(metrics_df[column], errors="coerce").dropna()
    if series.empty:
        return None
    return series.iloc[-1]


def latest_year(metrics_df: pd.DataFrame) -> str:
    """
    Return the latest available year from the metrics frame.
    """
    if not isinstance(metrics_df, pd.DataFrame) or metrics_df.empty or "Year" not in metrics_df.columns:
        return "N/A"

    years = pd.to_numeric(metrics_df["Year"], errors="coerce").dropna()
    if years.empty:
        return "N/A"
    return str(int(years.iloc[-1]))


def save_metrics_csv(metrics_df: pd.DataFrame, reports_dir: Path, ticker: str) -> Path:
    """
    Save the metrics DataFrame as a CSV file in the reports directory.
    """
    reports_dir.mkdir(parents=True, exist_ok=True)
    output_path = reports_dir / f"{ticker.upper()}_metrics.csv"
    metrics_df.to_csv(output_path, index=False)
    return output_path


def generate_markdown_summary(
    ticker: str,
    company_info_df: pd.DataFrame,
    metrics_df: pd.DataFrame,
) -> str:
    """
    Generate a simple Markdown summary using the latest available company and metric values.
    """
    info_row = company_info_df.iloc[0] if isinstance(company_info_df, pd.DataFrame) and not company_info_df.empty else {}

    company_name = safe_string(info_row.get("name") if hasattr(info_row, "get") else None, ticker.upper())
    sector = safe_string(info_row.get("sector") if hasattr(info_row, "get") else None)
    market_cap = format_money(info_row.get("market_cap") if hasattr(info_row, "get") else None)
    year = latest_year(metrics_df)

    revenue = format_money(latest_metric_value(metrics_df, "revenue"))
    revenue_growth = format_percent(latest_metric_value(metrics_df, "revenue_growth_pct"))
    net_income = format_money(latest_metric_value(metrics_df, "net_income"))
    free_cash_flow = format_money(latest_metric_value(metrics_df, "free_cash_flow"))
    cash = format_money(latest_metric_value(metrics_df, "cash_and_equivalents"))
    debt = format_money(latest_metric_value(metrics_df, "total_debt"))

    lines = [
        f"# {ticker.upper()} Research Summary",
        "",
        "## Company Snapshot",
        f"- Company Name: {company_name}",
        f"- Sector: {sector}",
        f"- Market Cap: {market_cap}",
        f"- Latest Fiscal Year: {year}",
        "",
        "## Latest Financial Highlights",
        f"- Revenue: {revenue}",
        f"- Revenue Growth: {revenue_growth}",
        f"- Net Income: {net_income}",
        f"- Free Cash Flow: {free_cash_flow}",
        f"- Cash and Equivalents: {cash}",
        f"- Total Debt: {debt}",
        "",
        "## Notes",
        "- Values are pulled from yfinance and may vary by company and filing availability.",
        "- Missing values are shown as N/A when a line item is unavailable.",
        "",
    ]
    return "\n".join(lines)


def save_markdown_summary(
    ticker: str,
    company_info_df: pd.DataFrame,
    metrics_df: pd.DataFrame,
    reports_dir: Path,
) -> Path:
    """
    Save the Markdown summary to the reports directory.
    """
    reports_dir.mkdir(parents=True, exist_ok=True)
    output_path = reports_dir / f"{ticker.upper()}_summary.md"
    markdown = generate_markdown_summary(ticker, company_info_df, metrics_df)
    output_path.write_text(markdown, encoding="utf-8")
    return output_path


def build_html_report(
    ticker: str,
    company_info_df: pd.DataFrame,
    metrics_df: pd.DataFrame,
    charts: dict[str, Any],
) -> str:
    """
    Build a standalone HTML report with embedded Plotly chart snippets.
    """
    info_row = company_info_df.iloc[0] if isinstance(company_info_df, pd.DataFrame) and not company_info_df.empty else {}

    company_name = safe_string(info_row.get("name") if hasattr(info_row, "get") else None, ticker.upper())
    sector = safe_string(info_row.get("sector") if hasattr(info_row, "get") else None)
    market_cap = format_money(info_row.get("market_cap") if hasattr(info_row, "get") else None)
    year = latest_year(metrics_df)

    stat_cards = {
        "Revenue": format_money(latest_metric_value(metrics_df, "revenue")),
        "Revenue Growth": format_percent(latest_metric_value(metrics_df, "revenue_growth_pct")),
        "Net Income": format_money(latest_metric_value(metrics_df, "net_income")),
        "Free Cash Flow": format_money(latest_metric_value(metrics_df, "free_cash_flow")),
        "Cash": format_money(latest_metric_value(metrics_df, "cash_and_equivalents")),
        "Debt": format_money(latest_metric_value(metrics_df, "total_debt")),
    }

    chart_html_blocks: list[str] = []
    include_plotlyjs = "cdn"
    for chart_name, figure in charts.items():
        block = to_html(figure, full_html=False, include_plotlyjs=include_plotlyjs)
        chart_html_blocks.append(
            f'<section class="chart-card"><h2>{chart_name.replace("_", " ").title()}</h2>{block}</section>'
        )
        include_plotlyjs = False

    stats_html = "".join(
        f'<div class="stat-card"><div class="stat-label">{label}</div><div class="stat-value">{value}</div></div>'
        for label, value in stat_cards.items()
    )

    table_html = metrics_df.to_html(index=False, classes="metrics-table", border=0) if isinstance(metrics_df, pd.DataFrame) and not metrics_df.empty else "<p>No metrics available.</p>"

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{ticker.upper()} Report</title>
  <style>
    body {{
      margin: 0;
      background: #020617;
      color: #e2e8f0;
      font-family: Arial, sans-serif;
    }}
    .container {{
      max-width: 1280px;
      margin: 0 auto;
      padding: 32px 24px 48px;
    }}
    .hero {{
      background: linear-gradient(135deg, #0f172a, #111827);
      border: 1px solid #1e293b;
      border-radius: 18px;
      padding: 28px;
      margin-bottom: 24px;
    }}
    .hero h1 {{
      margin: 0 0 10px;
    }}
    .hero-meta {{
      color: #93c5fd;
      line-height: 1.8;
    }}
    .stats-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 16px;
      margin: 24px 0;
    }}
    .stat-card {{
      background: #0f172a;
      border: 1px solid #1e293b;
      border-radius: 14px;
      padding: 18px;
    }}
    .stat-label {{
      color: #93c5fd;
      font-size: 0.9rem;
      margin-bottom: 8px;
    }}
    .stat-value {{
      font-size: 1.25rem;
      font-weight: 700;
    }}
    .chart-card, .table-card {{
      background: #0f172a;
      border: 1px solid #1e293b;
      border-radius: 18px;
      padding: 20px;
      margin-bottom: 24px;
    }}
    .metrics-table {{
      width: 100%;
      border-collapse: collapse;
      color: #e2e8f0;
    }}
    .metrics-table th, .metrics-table td {{
      padding: 10px 8px;
      border-bottom: 1px solid #1e293b;
      text-align: left;
    }}
    .metrics-table th {{
      color: #93c5fd;
    }}
  </style>
</head>
<body>
  <div class="container">
    <section class="hero">
      <h1>{company_name} ({ticker.upper()})</h1>
      <div class="hero-meta">
        <div>Sector: {sector}</div>
        <div>Market Cap: {market_cap}</div>
        <div>Latest Fiscal Year: {year}</div>
      </div>
    </section>
    <section class="stats-grid">
      {stats_html}
    </section>
    {''.join(chart_html_blocks)}
    <section class="table-card">
      <h2>Metrics Table</h2>
      {table_html}
    </section>
  </div>
</body>
</html>
"""


def save_html_report(
    ticker: str,
    company_info_df: pd.DataFrame,
    metrics_df: pd.DataFrame,
    charts: dict[str, Any],
    reports_dir: Path,
) -> Path:
    """
    Save the HTML report to the reports directory.
    """
    reports_dir.mkdir(parents=True, exist_ok=True)
    output_path = reports_dir / f"{ticker.upper()}_report.html"
    html = build_html_report(ticker, company_info_df, metrics_df, charts)
    output_path.write_text(html, encoding="utf-8")
    return output_path


def save_all_outputs(
    ticker: str,
    company_info_df: pd.DataFrame,
    metrics_df: pd.DataFrame,
    charts: dict[str, Any],
    reports_dir: str | Path = "reports",
) -> dict[str, Path]:
    """
    Save the CSV, Markdown summary, and HTML report in one step.
    """
    reports_path = Path(reports_dir)
    reports_path.mkdir(parents=True, exist_ok=True)

    csv_path = save_metrics_csv(metrics_df, reports_path, ticker)
    markdown_path = save_markdown_summary(ticker, company_info_df, metrics_df, reports_path)
    html_path = save_html_report(ticker, company_info_df, metrics_df, charts, reports_path)

    return {
        "metrics_csv": csv_path,
        "summary_md": markdown_path,
        "report_html": html_path,
    }
