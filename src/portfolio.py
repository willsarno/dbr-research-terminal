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
        paper_bgcolor="#0b1220",
        plot_bgcolor="#0b1220",
        font={"family": "Arial, sans-serif"},
        hovermode="x unified",
        margin={"l": 55, "r": 20, "t": 88, "b": 38},
        legend={"orientation": "h", "yanchor": "top", "y": 1.0, "x": 0, "xanchor": "left"},
        yaxis_title=yaxis_title,
        height=360,
        title={"text": title, "x": 0.0, "xanchor": "left", "y": 0.97, "yanchor": "top"},
    )
    fig.update_xaxes(showgrid=True, gridcolor="#22304a")
    fig.update_yaxes(showgrid=True, gridcolor="#22304a", zerolinecolor="#3b4a66")
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


def analyze_portfolio(
    holdings_df: pd.DataFrame,
    price_history_map: dict[str, pd.DataFrame],
) -> dict[str, Any]:
    """
    Analyze a portfolio from holdings and price histories.
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
        if not isinstance(history, pd.DataFrame) or history.empty:
            continue

        column = "Adj Close" if "Adj Close" in history.columns and history["Adj Close"].notna().any() else "Close"
        if column not in history.columns or "Date" not in history.columns:
            continue

        price_series = pd.to_numeric(history[column], errors="coerce")
        date_series = pd.to_datetime(history["Date"], errors="coerce")
        series = pd.Series(price_series.values, index=date_series).dropna().sort_index()
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
    annualized_return = (equity_curve.iloc[-1] ** (252 / len(weighted_returns)) - 1.0) if len(weighted_returns) > 0 else 0.0
    annualized_volatility = float(weighted_returns.std(ddof=0) * (252**0.5)) if not weighted_returns.empty else 0.0
    sharpe_ratio = annualized_return / annualized_volatility if annualized_volatility else 0.0
    rolling_max = equity_curve.cummax()
    drawdown = equity_curve / rolling_max - 1.0
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

    return {
        "metrics": {
            "cumulative_return": cumulative_return,
            "annualized_return": annualized_return,
            "annualized_volatility": annualized_volatility,
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown": max_drawdown,
        },
        "warnings": warnings,
        "returns_df": returns_df,
        "correlation_df": correlation_df,
        "portfolio_equity": equity_curve,
        "portfolio_drawdown": drawdown,
        "holdings_normalized_df": normalized_df,
        "holdings_raw_df": raw_df,
        "weights_df": holdings,
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
                line={"width": 3, "color": "#38bdf8"},
            )
        )
    _apply_dark_layout(fig, "Portfolio Cumulative Return", "Return")
    fig.update_yaxes(tickformat=".0%")
    return fig


def create_holdings_comparison_chart(holdings_normalized_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    palette = ["#38bdf8", "#22c55e", "#f59e0b", "#8b5cf6", "#ef4444", "#14b8a6", "#eab308"]
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
                hole=0.45,
                textinfo="label+percent",
            )
        )
    _apply_dark_layout(fig, "Portfolio Allocation", "")
    fig.update_layout(showlegend=False)
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
                line={"width": 2.5, "color": "#ef4444"},
                fill="tozeroy",
            )
        )
    _apply_dark_layout(fig, "Portfolio Drawdown", "Drawdown")
    fig.update_yaxes(tickformat=".0%")
    return fig
