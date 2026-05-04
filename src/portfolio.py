from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from src.charts import format_dollars_short, format_number_short


DEFAULT_PORTFOLIO = pd.DataFrame(
    [
        {"Ticker": "AAPL", "Weight %": 25.0},
        {"Ticker": "MSFT", "Weight %": 25.0},
        {"Ticker": "NVDA", "Weight %": 20.0},
        {"Ticker": "SOFI", "Weight %": 15.0},
        {"Ticker": "CASH", "Weight %": 15.0},
    ]
)


def _apply_dark_layout(fig: go.Figure, title: str, yaxis_title: str = "") -> go.Figure:
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#020617",
        plot_bgcolor="#0B1220",
        font={"family": "Arial, sans-serif", "color": "#E2E8F0"},
        hovermode="x unified",
        margin={"l": 56, "r": 18, "t": 92, "b": 34},
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "x": 0,
            "xanchor": "left",
            "bgcolor": "rgba(0,0,0,0)",
            "font": {"size": 10, "color": "#94A3B8"},
        },
        yaxis_title=yaxis_title,
        height=320,
        title={"text": title, "x": 0.0, "xanchor": "left", "y": 0.985, "yanchor": "top", "font": {"size": 16, "color": "#E2E8F0"}},
    )
    fig.update_xaxes(showgrid=True, gridcolor="#1E293B", tickfont={"size": 10, "color": "#94A3B8"}, title_font={"size": 10, "color": "#94A3B8"}, zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor="#1E293B", zerolinecolor="#1E293B", tickfont={"size": 10, "color": "#94A3B8"}, title_font={"size": 10, "color": "#94A3B8"}, nticks=5)
    return fig


def clean_holdings(holdings_df: pd.DataFrame, normalize_weights: bool = False) -> tuple[pd.DataFrame, list[str]]:
    """
    Clean the holdings table and optionally normalize weights to 100.
    """
    warnings: list[str] = []
    if not isinstance(holdings_df, pd.DataFrame) or holdings_df.empty:
        return DEFAULT_PORTFOLIO.copy(), warnings

    cleaned = holdings_df.copy()
    cleaned["Ticker"] = cleaned["Ticker"].astype(str).str.strip().str.upper()
    cleaned["Weight %"] = pd.to_numeric(cleaned["Weight %"], errors="coerce")
    cleaned = cleaned.dropna(subset=["Ticker", "Weight %"])
    cleaned = cleaned[cleaned["Ticker"] != ""].reset_index(drop=True)

    total_weight = float(cleaned["Weight %"].sum()) if not cleaned.empty else 0.0
    if cleaned.empty:
        warnings.append("No valid holdings were provided.")
        return cleaned, warnings

    if abs(total_weight - 100.0) > 0.01:
        warnings.append(f"Portfolio weights sum to {total_weight:.1f}%, not 100%.")
        if normalize_weights and total_weight > 0:
            cleaned["Weight %"] = cleaned["Weight %"] / total_weight * 100.0
            warnings.append("Weights were normalized to 100%.")

    return cleaned, warnings


def _extract_price_series(history: pd.DataFrame) -> pd.Series:
    """
    Build a clean price series from yfinance-style history data.
    """
    if not isinstance(history, pd.DataFrame) or history.empty:
        return pd.Series(dtype="float64")

    column = "Adj Close" if "Adj Close" in history.columns and history["Adj Close"].notna().any() else "Close"
    if column not in history.columns or "Date" not in history.columns:
        return pd.Series(dtype="float64")

    price_series = pd.to_numeric(history[column], errors="coerce")
    date_series = pd.to_datetime(history["Date"], errors="coerce")
    series = pd.Series(price_series.values, index=date_series).dropna().sort_index()
    return series[~series.index.duplicated(keep="last")]


def _calculate_drawdown(equity_curve: pd.Series) -> pd.Series:
    """
    Convert an equity curve into a peak-to-trough drawdown series.
    """
    if equity_curve.empty:
        return pd.Series(dtype="float64")

    rolling_max = equity_curve.cummax()
    return equity_curve / rolling_max - 1.0


def _annualized_return_from_equity(equity_curve: pd.Series, observations: int) -> float:
    """
    Convert a cumulative equity curve into an annualized return.
    """
    if equity_curve.empty or observations <= 0:
        return 0.0

    ending_value = float(equity_curve.iloc[-1])
    if ending_value <= 0:
        return 0.0
    return ending_value ** (252 / observations) - 1.0


def analyze_portfolio(
    holdings_df: pd.DataFrame,
    price_history_map: dict[str, pd.DataFrame],
    benchmark_history: pd.DataFrame | None = None,
    benchmark_ticker: str = "SPY",
) -> dict[str, Any]:
    """
    Analyze a portfolio from holdings, price histories, and an optional benchmark.
    """
    holdings = holdings_df.copy()
    holdings["Weight %"] = pd.to_numeric(holdings["Weight %"], errors="coerce").fillna(0.0)
    weights = {row["Ticker"]: float(row["Weight %"]) / 100.0 for _, row in holdings.iterrows()}

    return_frames: list[pd.Series] = []
    normalized_frames: list[pd.Series] = []
    raw_frames: list[pd.Series] = []

    for ticker, weight in weights.items():
        if ticker == "CASH":
            continue
        history = price_history_map.get(ticker, pd.DataFrame())
        series = _extract_price_series(history)
        if series.empty:
            continue

        returns = series.pct_change().fillna(0.0)
        returns.name = ticker
        return_frames.append(returns)

        normalized = (series / float(series.iloc[0])) * 100.0
        normalized.name = ticker
        normalized_frames.append(normalized)

        raw_series = series.copy()
        raw_series.name = ticker
        raw_frames.append(raw_series)

    if not return_frames:
        return {
            "metrics": {},
            "warnings": ["No valid market price histories were available for the selected holdings."],
            "returns_df": pd.DataFrame(),
            "correlation_df": pd.DataFrame(),
            "portfolio_equity": pd.Series(dtype="float64"),
            "portfolio_drawdown": pd.Series(dtype="float64"),
            "holdings_normalized_df": pd.DataFrame(),
            "holdings_raw_df": pd.DataFrame(),
            "weights_df": holdings,
        }

    returns_df = pd.concat(return_frames, axis=1).sort_index().fillna(0.0)
    normalized_df = pd.concat(normalized_frames, axis=1).sort_index()
    raw_df = pd.concat(raw_frames, axis=1).sort_index()

    weighted_returns = pd.Series(0.0, index=returns_df.index)
    for ticker in returns_df.columns:
        weighted_returns = weighted_returns.add(returns_df[ticker] * weights.get(ticker, 0.0), fill_value=0.0)

    equity_curve = (1.0 + weighted_returns).cumprod()
    cumulative_return = equity_curve.iloc[-1] - 1.0 if not equity_curve.empty else 0.0
    annualized_return = _annualized_return_from_equity(equity_curve, len(weighted_returns))
    annualized_volatility = float(weighted_returns.std(ddof=0) * (252**0.5)) if not weighted_returns.empty else 0.0
    sharpe_ratio = annualized_return / annualized_volatility if annualized_volatility else 0.0
    drawdown = _calculate_drawdown(equity_curve)
    max_drawdown = float(drawdown.min()) if not drawdown.empty else 0.0

    warnings: list[str] = []
    if (holdings["Weight %"] > 30).any():
        warnings.append("One or more positions exceed 30%, indicating concentration risk.")
    cash_weight = float(holdings.loc[holdings["Ticker"] == "CASH", "Weight %"].sum())
    if cash_weight > 20:
        warnings.append("Cash weight exceeds 20%, which may create cash drag.")
    if annualized_volatility > 0.25:
        warnings.append("Portfolio volatility is above 25%, indicating elevated risk.")
    if max_drawdown < -0.25:
        warnings.append("Historical drawdown is worse than -25%.")

    correlation_df = returns_df.corr()
    if not correlation_df.empty and len(correlation_df.columns) > 1:
        upper_triangle = correlation_df.where(~np.tril(np.ones(correlation_df.shape)).astype(bool))
        avg_correlation = upper_triangle.stack().mean()
        if pd.notna(avg_correlation) and avg_correlation > 0.75:
            warnings.append("Average cross-holding correlation is above 0.75.")

    benchmark_series = _extract_price_series(benchmark_history if benchmark_history is not None else pd.DataFrame())
    benchmark_returns = pd.Series(dtype="float64")
    benchmark_equity = pd.Series(dtype="float64")
    benchmark_drawdown = pd.Series(dtype="float64")
    benchmark_metrics: dict[str, float | None] = {
        "cumulative_return": None,
        "annualized_return": None,
        "excess_return": None,
        "beta": None,
        "correlation": None,
        "tracking_error": None,
        "max_drawdown": None,
        "max_drawdown_difference": None,
    }
    benchmark_available = False

    if not benchmark_series.empty:
        benchmark_available = True
        benchmark_returns = benchmark_series.pct_change().fillna(0.0)
        benchmark_equity = (1.0 + benchmark_returns).cumprod()
        benchmark_drawdown = _calculate_drawdown(benchmark_equity)
        benchmark_cumulative_return = float(benchmark_equity.iloc[-1] - 1.0) if not benchmark_equity.empty else None
        benchmark_annualized_return = _annualized_return_from_equity(benchmark_equity, len(benchmark_returns))
        benchmark_max_drawdown = float(benchmark_drawdown.min()) if not benchmark_drawdown.empty else None

        aligned = pd.concat(
            [
                weighted_returns.rename("portfolio"),
                benchmark_returns.rename("benchmark"),
            ],
            axis=1,
            join="inner",
        ).dropna()

        beta = None
        correlation = None
        tracking_error = None
        if not aligned.empty:
            benchmark_variance = float(aligned["benchmark"].var(ddof=0))
            covariance = float(aligned["portfolio"].cov(aligned["benchmark"], ddof=0))
            correlation = float(aligned["portfolio"].corr(aligned["benchmark"]))
            tracking_error = float((aligned["portfolio"] - aligned["benchmark"]).std(ddof=0) * (252**0.5))
            if benchmark_variance:
                beta = covariance / benchmark_variance

        benchmark_metrics = {
            "cumulative_return": benchmark_cumulative_return,
            "annualized_return": benchmark_annualized_return,
            "excess_return": (
                cumulative_return - benchmark_cumulative_return
                if benchmark_cumulative_return is not None
                else None
            ),
            "beta": beta,
            "correlation": correlation,
            "tracking_error": tracking_error,
            "max_drawdown": benchmark_max_drawdown,
            "max_drawdown_difference": (
                max_drawdown - benchmark_max_drawdown
                if benchmark_max_drawdown is not None
                else None
            ),
        }

    return {
        "metrics": {
            "cumulative_return": cumulative_return,
            "annualized_return": annualized_return,
            "annualized_volatility": annualized_volatility,
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown": max_drawdown,
        },
        "benchmark_metrics": benchmark_metrics,
        "benchmark_available": benchmark_available,
        "benchmark_ticker": benchmark_ticker,
        "warnings": warnings,
        "returns_df": returns_df,
        "correlation_df": correlation_df,
        "portfolio_equity": equity_curve,
        "portfolio_drawdown": drawdown,
        "benchmark_returns": benchmark_returns,
        "benchmark_equity": benchmark_equity,
        "benchmark_drawdown": benchmark_drawdown,
        "holdings_normalized_df": normalized_df,
        "holdings_raw_df": raw_df,
        "weights_df": holdings,
    }


def compare_portfolio_scenarios(
    current_analysis: dict[str, Any],
    proposed_analysis: dict[str, Any],
    current_holdings: pd.DataFrame,
    proposed_holdings: pd.DataFrame,
) -> dict[str, Any]:
    """
    Compare current and proposed portfolio scenarios using the latest run results.
    """
    current_metrics = current_analysis.get("metrics", {})
    proposed_metrics = proposed_analysis.get("metrics", {})

    current_cash = float(
        pd.to_numeric(
            current_holdings.loc[current_holdings["Ticker"] == "CASH", "Weight %"],
            errors="coerce",
        ).fillna(0.0).sum()
    ) if isinstance(current_holdings, pd.DataFrame) and not current_holdings.empty else 0.0
    proposed_cash = float(
        pd.to_numeric(
            proposed_holdings.loc[proposed_holdings["Ticker"] == "CASH", "Weight %"],
            errors="coerce",
        ).fillna(0.0).sum()
    ) if isinstance(proposed_holdings, pd.DataFrame) and not proposed_holdings.empty else 0.0

    current_largest = float(pd.to_numeric(current_holdings.get("Weight %"), errors="coerce").fillna(0.0).max()) if isinstance(current_holdings, pd.DataFrame) and not current_holdings.empty else 0.0
    proposed_largest = float(pd.to_numeric(proposed_holdings.get("Weight %"), errors="coerce").fillna(0.0).max()) if isinstance(proposed_holdings, pd.DataFrame) and not proposed_holdings.empty else 0.0

    def _metric_delta(metric_name: str) -> float | None:
        current_value = pd.to_numeric(current_metrics.get(metric_name), errors="coerce")
        proposed_value = pd.to_numeric(proposed_metrics.get(metric_name), errors="coerce")
        if pd.isna(current_value) or pd.isna(proposed_value):
            return None
        return float(proposed_value - current_value)

    deltas = {
        "return": _metric_delta("cumulative_return"),
        "volatility": _metric_delta("annualized_volatility"),
        "sharpe": _metric_delta("sharpe_ratio"),
        "drawdown": _metric_delta("max_drawdown"),
        "largest_holding": proposed_largest - current_largest,
        "cash_allocation": proposed_cash - current_cash,
    }

    summary: list[str] = []
    if deltas["return"] is not None and deltas["volatility"] is not None:
        if deltas["return"] > 0 and deltas["volatility"] > 0:
            summary.append("Proposed portfolio increases return but also increases volatility.")
        elif deltas["return"] > 0 and deltas["volatility"] <= 0:
            summary.append("Proposed portfolio improves return without taking more volatility.")
        elif deltas["return"] < 0 and deltas["volatility"] < 0:
            summary.append("Proposed portfolio lowers return but also reduces volatility.")

    if deltas["drawdown"] is not None:
        if deltas["drawdown"] > 0:
            summary.append("Proposed portfolio lowers drawdown.")
        elif deltas["drawdown"] < 0:
            summary.append("Proposed portfolio deepens drawdown risk.")

    if deltas["largest_holding"] > 0:
        summary.append("Proposed portfolio increases concentration risk.")
    elif deltas["largest_holding"] < 0:
        summary.append("Proposed portfolio reduces concentration risk.")

    if deltas["cash_allocation"] > 0:
        summary.append("Proposed portfolio increases cash allocation, which may add defensiveness but reduce upside capture.")
    elif deltas["cash_allocation"] < 0:
        summary.append("Proposed portfolio reduces cash allocation, increasing market exposure.")

    if not summary:
        summary.append("Current and proposed portfolio risk/return characteristics are broadly similar based on available price history.")

    return {
        "current_metrics": current_metrics,
        "proposed_metrics": proposed_metrics,
        "current_largest_holding": current_largest,
        "proposed_largest_holding": proposed_largest,
        "current_cash_allocation": current_cash,
        "proposed_cash_allocation": proposed_cash,
        "summary": summary,
        "deltas": deltas,
    }


def create_portfolio_cumulative_chart(portfolio_equity: pd.Series) -> go.Figure:
    fig = go.Figure()
    if not portfolio_equity.empty:
        fig.add_trace(
            go.Scatter(
                x=portfolio_equity.index,
                y=portfolio_equity - 1.0,
                mode="lines",
                name="Portfolio",
                line={"width": 3, "color": "#3B82F6"},
            )
        )
    _apply_dark_layout(fig, "Portfolio Cumulative Return", "Return")
    fig.update_yaxes(tickformat=".0%")
    return fig


def create_portfolio_vs_benchmark_chart(
    portfolio_equity: pd.Series,
    benchmark_equity: pd.Series,
    benchmark_ticker: str,
) -> go.Figure:
    fig = go.Figure()
    if not portfolio_equity.empty:
        fig.add_trace(
            go.Scatter(
                x=portfolio_equity.index,
                y=portfolio_equity - 1.0,
                mode="lines",
                name="Portfolio",
                line={"width": 3, "color": "#3B82F6"},
            )
        )
    if not benchmark_equity.empty:
        fig.add_trace(
            go.Scatter(
                x=benchmark_equity.index,
                y=benchmark_equity - 1.0,
                mode="lines",
                name=benchmark_ticker,
                line={"width": 2.5, "color": "#0F766E"},
            )
        )
    _apply_dark_layout(fig, "Portfolio vs Benchmark Cumulative Return", "Return")
    fig.update_yaxes(tickformat=".0%")
    return fig


def create_holdings_comparison_chart(holdings_normalized_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    palette = ["#3B82F6", "#0F766E", "#64748B", "#DC2626", "#D97706", "#475569", "#1D4ED8"]
    for index, column in enumerate(holdings_normalized_df.columns):
        fig.add_trace(
            go.Scatter(
                x=holdings_normalized_df.index,
                y=holdings_normalized_df[column],
                mode="lines",
                name=column,
                line={"width": 2.5, "color": palette[index % len(palette)]},
            )
        )
    _apply_dark_layout(fig, "Holdings Cumulative Return Comparison", "Normalized to 100")
    return fig


def create_allocation_chart(weights_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    if not weights_df.empty:
        fig.add_trace(
            go.Pie(
                labels=weights_df["Ticker"],
                values=weights_df["Weight %"],
                hole=0.6,
                textinfo="label+percent",
                marker={"colors": ["#3B82F6", "#64748B", "#0F766E", "#475569", "#1E293B", "#10B981"]},
            )
        )
    _apply_dark_layout(fig, "Portfolio Allocation", "")
    fig.update_layout(showlegend=False, colorway=["#3B82F6", "#64748B", "#0F766E", "#475569", "#1E293B", "#10B981"])
    return fig


def create_correlation_heatmap(correlation_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    if not correlation_df.empty:
        fig.add_trace(
            go.Heatmap(
                z=correlation_df.values,
                x=correlation_df.columns,
                y=correlation_df.index,
                colorscale="RdBu",
                zmin=-1,
                zmax=1,
            )
        )
    _apply_dark_layout(fig, "Correlation Heatmap", "")
    return fig


def create_drawdown_chart(drawdown_series: pd.Series) -> go.Figure:
    fig = go.Figure()
    if not drawdown_series.empty:
        fig.add_trace(
            go.Scatter(
                x=drawdown_series.index,
                y=drawdown_series,
                mode="lines",
                name="Drawdown",
                line={"width": 2.5, "color": "#DC2626"},
                fill="tozeroy",
            )
        )
    _apply_dark_layout(fig, "Portfolio Drawdown", "Drawdown")
    fig.update_yaxes(tickformat=".0%")
    return fig


def create_drawdown_comparison_chart(
    portfolio_drawdown: pd.Series,
    benchmark_drawdown: pd.Series,
    benchmark_ticker: str,
) -> go.Figure:
    fig = go.Figure()
    if not portfolio_drawdown.empty:
        fig.add_trace(
            go.Scatter(
                x=portfolio_drawdown.index,
                y=portfolio_drawdown,
                mode="lines",
                name="Portfolio",
                line={"width": 2.5, "color": "#DC2626"},
            )
        )
    if not benchmark_drawdown.empty:
        fig.add_trace(
            go.Scatter(
                x=benchmark_drawdown.index,
                y=benchmark_drawdown,
                mode="lines",
                name=f"{benchmark_ticker} Drawdown",
                line={"width": 2.2, "color": "#D97706"},
            )
        )
    _apply_dark_layout(fig, "Portfolio vs Benchmark Drawdown", "Drawdown")
    fig.update_yaxes(tickformat=".0%")
    return fig
