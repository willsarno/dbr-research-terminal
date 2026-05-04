from __future__ import annotations

import math

import pandas as pd
import plotly.graph_objects as go


def _apply_dark_layout(fig: go.Figure, title: str, yaxis_title: str = "") -> go.Figure:
    """
    Apply a consistent dark theme across all charts.
    """
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0b1220",
        plot_bgcolor="#0f172a",
        font={"family": "Arial, sans-serif", "color": "#dbe4f0"},
        hovermode="x unified",
        margin={"l": 58, "r": 24, "t": 96, "b": 42},
        legend={
            "orientation": "h",
            "yanchor": "top",
            "y": 1.07,
            "x": 0,
            "xanchor": "left",
            "bgcolor": "rgba(0,0,0,0)",
            "font": {"size": 11},
        },
        yaxis_title=yaxis_title,
        height=336,
        title={"text": title, "x": 0.0, "xanchor": "left", "y": 0.985, "yanchor": "top", "font": {"size": 17}},
    )
    fig.update_xaxes(showgrid=True, gridcolor="rgba(148, 163, 184, 0.14)", tickfont={"size": 11}, title_font={"size": 11})
    fig.update_yaxes(showgrid=True, gridcolor="rgba(148, 163, 184, 0.14)", zerolinecolor="#3b4a66", tickfont={"size": 11}, title_font={"size": 11})
    return fig


def _safe_metrics_frame(metrics_df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize the metrics input so chart functions can safely operate on it.
    """
    if not isinstance(metrics_df, pd.DataFrame) or metrics_df.empty:
        return pd.DataFrame(columns=["Period", "Year"])

    cleaned = metrics_df.copy()
    if "Year" in cleaned.columns:
        cleaned["Year"] = pd.to_numeric(cleaned["Year"], errors="coerce")
    if "Period" in cleaned.columns:
        cleaned["Period"] = cleaned["Period"].astype("string")
    sort_columns = [column for column in ("Year", "Period") if column in cleaned.columns]
    if sort_columns:
        cleaned = cleaned.sort_values(sort_columns).reset_index(drop=True)
    return cleaned


def _safe_price_frame(price_history_df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize price-history input and preserve only known price columns when present.
    """
    if not isinstance(price_history_df, pd.DataFrame) or price_history_df.empty:
        return pd.DataFrame(columns=["Date", "Close"])

    cleaned = price_history_df.copy()
    if "Date" in cleaned.columns:
        cleaned["Date"] = pd.to_datetime(cleaned["Date"], errors="coerce")
        cleaned = cleaned.dropna(subset=["Date"]).sort_values("Date").reset_index(drop=True)
    return cleaned


def _column_with_values(frame: pd.DataFrame, column: str) -> pd.Series | None:
    """
    Return a numeric series only when the column exists and has at least one value.
    """
    if column not in frame.columns:
        return None

    series = pd.to_numeric(frame[column], errors="coerce")
    if series.dropna().empty:
        return None
    return series


def format_number_short(value: float | int | None) -> str:
    """
    Format large numeric values using K/M/B suffixes.
    """
    if value is None or pd.isna(value):
        return "N/A"

    numeric_value = float(value)
    absolute_value = abs(numeric_value)

    if absolute_value >= 1_000_000_000:
        return f"{numeric_value / 1_000_000_000:.1f}B"
    if absolute_value >= 1_000_000:
        return f"{numeric_value / 1_000_000:.1f}M"
    if absolute_value >= 1_000:
        return f"{numeric_value / 1_000:.1f}K"
    if float(numeric_value).is_integer():
        return f"{int(numeric_value)}"
    return f"{numeric_value:.2f}"


def format_dollars_short(value: float | int | None) -> str:
    """
    Format large dollar values using K/M/B suffixes.
    """
    short_number = format_number_short(value)
    if short_number == "N/A":
        return short_number
    return f"${short_number}"


def _apply_short_axis_format(
    fig: go.Figure,
    axis: str = "y",
    currency: bool = False,
    fixed_range: list[float] | None = None,
) -> go.Figure:
    """
    Apply readable K/M/B tick labels instead of scientific/G notation.
    """
    values: list[float] = []
    for trace in fig.data:
        trace_values = getattr(trace, axis, None)
        if trace_values is None:
            continue
        numeric_values = pd.to_numeric(pd.Series(trace_values), errors="coerce").dropna().tolist()
        values.extend(float(value) for value in numeric_values)

    update_kwargs: dict[str, object] = {}
    if fixed_range is not None:
        update_kwargs["range"] = fixed_range
        values.extend([fixed_range[0], fixed_range[1]])

    if not values:
        fig.update_yaxes(**update_kwargs)
        return fig

    min_value = min(values)
    max_value = max(values)
    if min_value == max_value:
        tick_values = [min_value]
    else:
        steps = 4
        span = max_value - min_value
        step = span / steps if span else 1.0
        tick_values = [min_value + (step * index) for index in range(steps + 1)]

    formatter = format_dollars_short if currency else format_number_short
    tick_text = [formatter(value) for value in tick_values]
    update_kwargs["tickmode"] = "array"
    update_kwargs["tickvals"] = tick_values
    update_kwargs["ticktext"] = tick_text
    fig.update_yaxes(**update_kwargs)
    return fig


def _has_chart_data(fig: go.Figure) -> bool:
    """
    Determine whether a Plotly figure contains at least one rendered trace.
    """
    return len(fig.data) > 0


def create_comparison_bar_chart(
    comparison_df: pd.DataFrame,
    value_column: str,
    title: str,
    yaxis_title: str,
    tickformat: str | None = None,
    color: str = "#38bdf8",
    yaxis_range: list[float] | None = None,
) -> go.Figure:
    """
    Build a dark-theme comparison bar chart across tickers.
    """
    fig = go.Figure()
    if not isinstance(comparison_df, pd.DataFrame) or comparison_df.empty:
        return _apply_dark_layout(fig, title, yaxis_title)

    if value_column not in comparison_df.columns or "Ticker" not in comparison_df.columns:
        return _apply_dark_layout(fig, title, yaxis_title)

    chart_df = comparison_df[["Ticker", value_column]].copy()
    chart_df[value_column] = pd.to_numeric(chart_df[value_column], errors="coerce")
    chart_df = chart_df.dropna(subset=[value_column])
    if chart_df.empty:
        return _apply_dark_layout(fig, title, yaxis_title)

    fig.add_trace(
        go.Bar(
            x=chart_df["Ticker"],
            y=chart_df[value_column],
            marker_color=color,
            name=title,
            hovertemplate="%{x}<br>%{y}<extra></extra>",
        )
    )
    _apply_dark_layout(fig, title, yaxis_title)
    fig.update_xaxes(type="category")
    if tickformat == "percent":
        fig.update_yaxes(tickformat=".0%")
        if yaxis_range is not None:
            fig.update_yaxes(range=yaxis_range)
        return fig
    if tickformat == "score":
        return _apply_short_axis_format(fig, currency=False, fixed_range=yaxis_range)
    if tickformat == "multiple":
        fig.update_yaxes(tickformat=".1f", ticksuffix="x")
        if yaxis_range is not None:
            fig.update_yaxes(range=yaxis_range)
        return fig
    return _apply_short_axis_format(fig, currency=(tickformat == "currency"), fixed_range=yaxis_range)


def _configure_period_axis(fig: go.Figure, metrics: pd.DataFrame) -> go.Figure:
    """
    Force financial periods to render as clean categorical labels.
    """
    if "Period" not in metrics.columns:
        return fig

    categories = [label for label in metrics["Period"].tolist() if pd.notna(label)]
    fig.update_xaxes(
        type="category",
        categoryorder="array",
        categoryarray=categories,
        tickmode="array",
        tickvals=categories,
        ticktext=categories,
    )
    return fig


def create_revenue_chart(metrics_df: pd.DataFrame) -> go.Figure:
    """
    Build a revenue trend chart.
    """
    metrics = _safe_metrics_frame(metrics_df)
    fig = go.Figure()

    revenue = _column_with_values(metrics, "revenue")
    if revenue is not None and "Period" in metrics.columns:
        fig.add_trace(
            go.Bar(
                x=metrics["Period"],
                y=revenue,
                name="Revenue",
                marker_color="#38bdf8",
                hovertemplate="Period %{x}<br>Revenue %{y:$,.2f}<extra></extra>",
            )
        )

    _apply_dark_layout(fig, "Revenue", "Revenue")
    _configure_period_axis(fig, metrics)
    return _apply_short_axis_format(fig, currency=True)


def create_margin_chart(metrics_df: pd.DataFrame) -> go.Figure:
    """
    Build a chart for gross, operating, and net margins.
    """
    metrics = _safe_metrics_frame(metrics_df)
    fig = go.Figure()

    margin_config = [
        ("ebitda_margin_pct", "EBITDA Margin", "#38bdf8"),
        ("gross_margin_pct", "Gross Margin", "#22c55e"),
        ("operating_margin_pct", "Operating Margin", "#f59e0b"),
        ("net_income_margin_pct", "Net Income Margin", "#f43f5e"),
    ]

    for column, label, color in margin_config:
        series = _column_with_values(metrics, column)
        if series is not None and "Period" in metrics.columns:
            fig.add_trace(
                go.Scatter(
                    x=metrics["Period"],
                    y=series,
                    mode="lines+markers",
                    name=label,
                    line={"width": 3, "color": color},
                    hovertemplate="Period %{x}<br>" + label + " %{y:.2%}<extra></extra>",
                )
            )

    _apply_dark_layout(fig, "Profitability Margins", "Margin %")
    _configure_period_axis(fig, metrics)
    fig.update_yaxes(tickformat=".0%")
    return fig


def create_income_fcf_chart(metrics_df: pd.DataFrame) -> go.Figure:
    """
    Build a comparison chart for net income, EBITDA, and free cash flow.
    """
    metrics = _safe_metrics_frame(metrics_df)
    fig = go.Figure()

    net_income = _column_with_values(metrics, "net_income")
    ebitda = _column_with_values(metrics, "ebitda")
    free_cash_flow = _column_with_values(metrics, "free_cash_flow")

    if net_income is not None and "Period" in metrics.columns:
        fig.add_trace(
            go.Bar(
                x=metrics["Period"],
                y=net_income,
                name="Net Income",
                marker_color="#8b5cf6",
                hovertemplate="Period %{x}<br>Net Income %{y:$,.2f}<extra></extra>",
            )
        )

    if ebitda is not None and "Period" in metrics.columns:
        fig.add_trace(
            go.Scatter(
                x=metrics["Period"],
                y=ebitda,
                name="EBITDA",
                mode="lines+markers",
                line={"width": 3, "color": "#22c55e"},
                hovertemplate="Period %{x}<br>EBITDA %{y:$,.2f}<extra></extra>",
            )
        )

    if free_cash_flow is not None and "Period" in metrics.columns:
        fig.add_trace(
            go.Scatter(
                x=metrics["Period"],
                y=free_cash_flow,
                name="Free Cash Flow",
                mode="lines+markers",
                line={"width": 3, "color": "#f59e0b"},
                hovertemplate="Period %{x}<br>Free Cash Flow %{y:$,.2f}<extra></extra>",
            )
        )

    _apply_dark_layout(fig, "Net Income, EBITDA, and Free Cash Flow", "Value")
    _configure_period_axis(fig, metrics)
    return _apply_short_axis_format(fig, currency=True)


def create_cash_debt_chart(metrics_df: pd.DataFrame) -> go.Figure:
    """
    Build a balance-sheet chart for cash, debt, and net cash/debt.
    """
    metrics = _safe_metrics_frame(metrics_df)
    fig = go.Figure()

    cash = _column_with_values(metrics, "cash_and_equivalents")
    debt = _column_with_values(metrics, "total_debt")
    net_cash_debt = _column_with_values(metrics, "net_cash_debt")

    if cash is not None and "Period" in metrics.columns:
        fig.add_trace(
            go.Bar(
                x=metrics["Period"],
                y=cash,
                name="Cash & Equivalents",
                marker_color="#22c55e",
                hovertemplate="Period %{x}<br>Cash %{y:$,.2f}<extra></extra>",
            )
        )

    if debt is not None and "Period" in metrics.columns:
        fig.add_trace(
            go.Bar(
                x=metrics["Period"],
                y=debt,
                name="Total Debt",
                marker_color="#ef4444",
                hovertemplate="Period %{x}<br>Debt %{y:$,.2f}<extra></extra>",
            )
        )

    if net_cash_debt is not None and "Period" in metrics.columns:
        fig.add_trace(
            go.Scatter(
                x=metrics["Period"],
                y=net_cash_debt,
                name="Net Cash / Debt",
                mode="lines+markers",
                line={"width": 3, "color": "#38bdf8"},
                hovertemplate="Period %{x}<br>Net Cash / Debt %{y:$,.2f}<extra></extra>",
            )
        )

    _apply_dark_layout(fig, "Cash, Debt, and Net Cash / Debt", "Value")
    _configure_period_axis(fig, metrics)
    return _apply_short_axis_format(fig, currency=True)


def create_stock_price_chart(
    price_history_df: pd.DataFrame,
    ticker: str,
    price_period: str = "5y",
) -> go.Figure:
    """
    Build a 5-year stock price chart for the requested ticker.
    """
    prices = _safe_price_frame(price_history_df)
    fig = go.Figure()

    close_series = _column_with_values(prices, "Close")
    if close_series is not None and "Date" in prices.columns:
        fig.add_trace(
            go.Scatter(
                x=prices["Date"],
                y=close_series,
                mode="lines",
                name=f"{ticker.upper()} Close",
                line={"width": 2.5, "color": "#38bdf8"},
                hovertemplate="%{x|%Y-%m-%d}<br>Close %{y:$,.2f}<extra></extra>",
            )
        )

    _apply_dark_layout(fig, f"{ticker.upper()} Stock Price ({price_period.upper()})", "Price")
    fig.update_layout(height=360)
    return _apply_short_axis_format(fig, currency=True)


def create_multi_ticker_price_chart(
    price_history_map: dict[str, pd.DataFrame],
    price_period: str = "1y",
    normalized: bool = True,
) -> go.Figure:
    """
    Build a multi-ticker line chart for comparison mode.
    """
    fig = go.Figure()
    title = "Stock Price Performance (Normalized)" if normalized else "Stock Price (Raw)"
    yaxis_title = "Normalized to 100" if normalized else "Price"

    palette = ["#38bdf8", "#22c55e", "#f59e0b", "#8b5cf6", "#ef4444", "#14b8a6", "#eab308"]
    for index, (ticker, frame) in enumerate(price_history_map.items()):
        prices = _safe_price_frame(frame)
        close_series = _column_with_values(prices, "Close")
        if close_series is None or "Date" not in prices.columns:
            continue

        chart_values = close_series.copy()
        if normalized:
            first_value = chart_values.dropna().iloc[0] if not chart_values.dropna().empty else None
            if first_value in (None, 0):
                continue
            chart_values = (chart_values / float(first_value)) * 100.0

        fig.add_trace(
            go.Scatter(
                x=prices["Date"],
                y=chart_values,
                mode="lines",
                name=ticker,
                line={"width": 2.5, "color": palette[index % len(palette)]},
            )
        )

    _apply_dark_layout(fig, title, yaxis_title)
    fig.update_layout(height=380)
    if normalized:
        fig.update_yaxes(tickformat=".0f")
        return fig
    return _apply_short_axis_format(fig, currency=True)


def create_all_charts(
    metrics_df: pd.DataFrame,
    price_history_df: pd.DataFrame,
    ticker: str,
    price_period: str = "5y",
) -> dict[str, go.Figure]:
    """
    Create and return the full chart set as a dictionary of Plotly figures.

    Empty charts are omitted so the Streamlit UI does not render placeholders.
    """
    candidates = {
        "revenue_chart": create_revenue_chart(metrics_df),
        "margin_chart": create_margin_chart(metrics_df),
        "income_fcf_chart": create_income_fcf_chart(metrics_df),
        "cash_debt_chart": create_cash_debt_chart(metrics_df),
        "stock_price_chart": create_stock_price_chart(price_history_df, ticker, price_period=price_period),
    }
    return {
        chart_name: figure
        for chart_name, figure in candidates.items()
        if _has_chart_data(figure)
    }
