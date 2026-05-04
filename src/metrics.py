from __future__ import annotations

from typing import Iterable
import warnings

import numpy as np
import pandas as pd


BASE_SCHEMA = [
    "Period",
    "Year",
    "revenue",
    "gross_profit",
    "operating_income",
    "ebitda",
    "net_income",
    "operating_cash_flow",
    "capital_expenditures",
    "free_cash_flow",
    "cash_and_equivalents",
    "total_debt",
    "net_cash_debt",
]

FULL_SCHEMA = BASE_SCHEMA + [
    "revenue_growth_pct",
    "ebitda_margin_pct",
    "gross_margin_pct",
    "operating_margin_pct",
    "net_income_margin_pct",
    "free_cash_flow_margin_pct",
    "depreciation_and_amortization",
    "shares_outstanding",
]


def format_money(value: float | int | None) -> str:
    """
    Format numeric values into readable dollar strings for metrics narratives.
    """
    if value is None or pd.isna(value):
        return "N/A"

    numeric_value = float(value)
    absolute_value = abs(numeric_value)

    if absolute_value >= 1_000_000_000:
        return f"${numeric_value / 1_000_000_000:.2f}B"
    if absolute_value >= 1_000_000:
        return f"${numeric_value / 1_000_000:.2f}M"
    if absolute_value >= 1_000:
        return f"${numeric_value / 1_000:.2f}K"
    return f"${numeric_value:,.2f}"


def _normalize_column_name(name: object) -> str:
    """
    Normalize a column name so slightly different yfinance labels can be matched.

    Example:
    - "Net Income"
    - "NetIncome"
    - "net_income"
    All normalize to the same comparable token.
    """
    text = str(name).strip().lower()
    for char in (" ", "_", "-", "/", "&", ",", "(", ")"):
        text = text.replace(char, "")
    return text


def find_matching_column(frame: pd.DataFrame, candidates: Iterable[str]) -> str | None:
    """
    Safely find the first matching column name from a list of candidates.

    yfinance statement labels can vary by ticker and statement version, so this
    function normalizes both the actual columns and the requested candidates.
    """
    if not isinstance(frame, pd.DataFrame) or frame.empty:
        return None

    normalized_map = {
        _normalize_column_name(column): column
        for column in frame.columns
    }

    for candidate in candidates:
        match = normalized_map.get(_normalize_column_name(candidate))
        if match is not None:
            return match

    return None


def _safe_series(frame: pd.DataFrame, candidates: Iterable[str]) -> pd.Series:
    """
    Return a numeric Series for the first matching column.

    If the column is missing, return an all-NaN Series aligned to the frame index.
    """
    if not isinstance(frame, pd.DataFrame) or frame.empty:
        return pd.Series(dtype="float64")

    column = find_matching_column(frame, candidates)
    if column is None:
        return pd.Series(index=frame.index, dtype="float64")

    return pd.to_numeric(frame[column], errors="coerce").astype(float)


def _ensure_year_sort(frame: pd.DataFrame) -> pd.DataFrame:
    """
    Return a copy sorted by Year ascending when that column exists.
    """
    if not isinstance(frame, pd.DataFrame) or frame.empty:
        return pd.DataFrame()

    cleaned = frame.copy()
    if "Year" in cleaned.columns:
        cleaned["Year"] = pd.to_numeric(cleaned["Year"], errors="coerce")
    if "Date" in cleaned.columns:
        cleaned["Date"] = pd.to_datetime(cleaned["Date"], errors="coerce")

    sort_columns = [column for column in ("Date", "Year", "Period") if column in cleaned.columns]
    if sort_columns:
        cleaned = cleaned.sort_values(sort_columns, ascending=True).reset_index(drop=True)
    else:
        cleaned = cleaned.reset_index(drop=True)

    for column in cleaned.columns:
        if column not in {"Period", "Year", "Date"}:
            cleaned[column] = pd.to_numeric(cleaned[column], errors="coerce").astype(float)

    return cleaned


def _pick_period_frame(
    income_statement: pd.DataFrame,
    balance_sheet: pd.DataFrame,
    cash_flow_statement: pd.DataFrame,
) -> pd.DataFrame:
    """
    Choose period keys from the first available statement.
    """
    for frame in (income_statement, balance_sheet, cash_flow_statement):
        if isinstance(frame, pd.DataFrame) and not frame.empty:
            available_columns = [column for column in ("Period", "Year", "Date") if column in frame.columns]
            if available_columns:
                return frame[available_columns].copy()
    return pd.DataFrame(columns=["Period", "Year", "Date"])


def _safe_divide(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    """
    Divide only where both series have data and the denominator is non-zero.
    """
    if numerator.empty or denominator.empty:
        return pd.Series(index=numerator.index if not numerator.empty else denominator.index, dtype="float64")

    result = pd.Series(np.nan, index=numerator.index, dtype="float64")
    valid_mask = numerator.notna() & denominator.notna() & (denominator != 0)
    result.loc[valid_mask] = numerator.loc[valid_mask] / denominator.loc[valid_mask]
    return result


def _warn_if_missing(series: pd.Series, label: str) -> None:
    """
    Emit a runtime warning when a key metric is completely unavailable.
    """
    if series.dropna().empty:
        warnings.warn(
            f"{label} data was not available from yfinance for this ticker.",
            stacklevel=2,
        )


def _empty_metrics_frame() -> pd.DataFrame:
    """
    Return an empty metrics DataFrame with the full standardized schema.
    """
    return pd.DataFrame(columns=FULL_SCHEMA)


def _is_financial_sector(sector: str | None) -> bool:
    """
    Identify sectors where EBITDA is commonly unavailable or less meaningful.
    """
    if not sector:
        return False
    normalized = str(sector).strip().lower()
    return normalized in {
        "financial services",
        "financial",
        "banks",
        "insurance",
        "capital markets",
        "credit services",
    }


def _latest_numeric_value(frame: pd.DataFrame, column: str) -> float | None:
    """
    Return the most recent numeric value for a metric column.
    """
    if not isinstance(frame, pd.DataFrame) or frame.empty or column not in frame.columns:
        return None
    series = pd.to_numeric(frame[column], errors="coerce").dropna()
    if series.empty:
        return None
    return float(series.iloc[-1])


def _empty_or_all_na(frame: pd.DataFrame, columns: list[str]) -> pd.Series:
    """
    Return a mask for rows where all listed metric columns are missing.
    """
    available_columns = [column for column in columns if column in frame.columns]
    if not available_columns:
        return pd.Series(True, index=frame.index)
    return frame[available_columns].isna().all(axis=1)


def _extract_metric_frame(
    frame: pd.DataFrame,
    metric_name: str,
    candidates: Iterable[str],
) -> pd.DataFrame:
    """
    Extract one metric into a period-keyed DataFrame.
    """
    if not isinstance(frame, pd.DataFrame) or frame.empty:
        return pd.DataFrame(columns=["Period", "Year", "Date", metric_name])

    keys = [column for column in ("Period", "Year", "Date") if column in frame.columns]
    if not keys:
        return pd.DataFrame(columns=["Period", "Year", "Date", metric_name])

    metric_series = _safe_series(frame, candidates)
    extracted = frame[keys].copy()
    extracted[metric_name] = metric_series
    return extracted


def _merge_metric_frames(frames: list[pd.DataFrame]) -> pd.DataFrame:
    """
    Merge multiple period-keyed metric frames into one metrics DataFrame.
    """
    merged: pd.DataFrame | None = None
    merge_keys = ["Period", "Year", "Date"]

    for frame in frames:
        if merged is None:
            merged = frame.copy()
        else:
            merged = merged.merge(frame, on=merge_keys, how="outer")

    if merged is None:
        return pd.DataFrame(columns=merge_keys)

    if "Date" in merged.columns:
        merged["Date"] = pd.to_datetime(merged["Date"], errors="coerce")
    if "Year" in merged.columns:
        merged["Year"] = pd.to_numeric(merged["Year"], errors="coerce")

    return merged.sort_values(["Date", "Year", "Period"], ascending=True).reset_index(drop=True)


def calculate_financial_metrics(
    income_statement: pd.DataFrame,
    balance_sheet: pd.DataFrame,
    cash_flow_statement: pd.DataFrame,
    sector: str | None = None,
) -> pd.DataFrame:
    """
    Build a consolidated metrics DataFrame from yfinance statement DataFrames.

    Expected input shape:
    - rows = years
    - columns include Year plus financial line items

    Rules:
    - Missing inputs or missing columns should not raise errors.
    - Missing values remain NaN.
    - Output is sorted by Year ascending.
    """
    income_statement = _ensure_year_sort(income_statement)
    balance_sheet = _ensure_year_sort(balance_sheet)
    cash_flow_statement = _ensure_year_sort(cash_flow_statement)

    metrics = pd.DataFrame()
    metrics = _pick_period_frame(
        income_statement=income_statement,
        balance_sheet=balance_sheet,
        cash_flow_statement=cash_flow_statement,
    )

    if metrics.empty:
        return _empty_metrics_frame()

    metrics = _merge_metric_frames(
        [
            _extract_metric_frame(
                income_statement,
                "revenue",
                ["Total Revenue", "Operating Revenue", "Revenue", "Total Revenues"],
            ),
            _extract_metric_frame(
                income_statement,
                "gross_profit",
                ["Gross Profit", "GrossProfit"],
            ),
            _extract_metric_frame(
                income_statement,
                "operating_income",
                ["Operating Income", "EBIT", "Income From Operations", "Operating Profit"],
            ),
            _extract_metric_frame(
                income_statement,
                "ebitda",
                ["EBITDA", "Normalized EBITDA"],
            ),
            _extract_metric_frame(
                income_statement,
                "net_income",
                [
                    "Net Income",
                    "Net Income Common Stockholders",
                    "Net Income Including Noncontrolling Interests",
                    "Net Income Continuous Operations",
                ],
            ),
            _extract_metric_frame(
                cash_flow_statement,
                "operating_cash_flow",
                [
                    "Operating Cash Flow",
                    "Cash Flow From Continuing Operating Activities",
                    "Net Cash Provided By Operating Activities",
                    "Cash Flow From Continuing Operations",
                ],
            ),
            _extract_metric_frame(
                cash_flow_statement,
                "capital_expenditures",
                [
                    "Capital Expenditure",
                    "Capital Expenditures",
                    "Purchase Of PPE",
                    "Property Plant Equipment Purchase",
                    "Capital Spending",
                ],
            ),
            _extract_metric_frame(
                cash_flow_statement,
                "depreciation_and_amortization",
                [
                    "Depreciation And Amortization",
                    "Depreciation And Amortization Expense",
                    "Depreciation Amortization And Depletion",
                    "Depreciation Amortization Depletion",
                    "Depreciation",
                    "Depreciation And Amortization In Income Statement",
                    "Depreciation Expense",
                    "Amortization",
                    "Amortization Of Intangibles",
                ],
            ),
            _extract_metric_frame(
                balance_sheet,
                "cash_and_equivalents",
                [
                    "Cash And Cash Equivalents",
                    "Cash Cash Equivalents And Short Term Investments",
                    "Cash And Short Term Investments",
                    "Cash And Cash Equivalents And Federal Funds Sold",
                    "Cash",
                ],
            ),
            _extract_metric_frame(
                balance_sheet,
                "total_debt",
                [
                    "Total Debt",
                    "Long Term Debt",
                    "Long Term Debt And Capital Lease Obligation",
                    "Current Debt",
                    "Current Debt And Capital Lease Obligation",
                    "Total Debt And Capital Lease Obligation",
                ],
            ),
            _extract_metric_frame(
                balance_sheet,
                "shares_outstanding",
                [
                    "Ordinary Shares Number",
                    "Share Issued",
                    "Common Stock Shares Outstanding",
                    "Shares Outstanding",
                ],
            ),
        ]
    )

    if "ebitda" not in metrics.columns:
        metrics["ebitda"] = np.nan
    if "depreciation_and_amortization" not in metrics.columns:
        metrics["depreciation_and_amortization"] = np.nan

    metrics["ebitda_source"] = "unavailable"
    metrics.loc[metrics["ebitda"].notna(), "ebitda_source"] = "reported"

    ebitda_missing_mask = metrics["ebitda"].isna()
    ebitda_proxy_mask = (
        ebitda_missing_mask
        & metrics["operating_income"].notna()
        & metrics["depreciation_and_amortization"].notna()
    )
    metrics.loc[ebitda_proxy_mask, "ebitda"] = (
        metrics.loc[ebitda_proxy_mask, "operating_income"]
        + metrics.loc[ebitda_proxy_mask, "depreciation_and_amortization"]
    )
    metrics.loc[ebitda_proxy_mask, "ebitda_source"] = "approximated"

    # yfinance often reports capex as a negative outflow. Adding it to OCF
    # yields standard free cash flow regardless of sign convention.
    metrics["free_cash_flow"] = metrics["operating_cash_flow"] + metrics["capital_expenditures"]

    # Net cash / debt is positive when cash exceeds debt and negative when debt exceeds cash.
    metrics["net_cash_debt"] = metrics["cash_and_equivalents"] - metrics["total_debt"]

    metrics["revenue_growth_pct"] = metrics["revenue"].pct_change()
    metrics["ebitda_margin_pct"] = _safe_divide(metrics["ebitda"], metrics["revenue"])
    metrics["gross_margin_pct"] = _safe_divide(metrics["gross_profit"], metrics["revenue"])
    metrics["operating_margin_pct"] = _safe_divide(metrics["operating_income"], metrics["revenue"])
    metrics["net_income_margin_pct"] = _safe_divide(metrics["net_income"], metrics["revenue"])
    metrics["free_cash_flow_margin_pct"] = _safe_divide(metrics["free_cash_flow"], metrics["revenue"])

    # Retain rows when at least one core operating metric exists.
    # This is especially important for quarterly statements, which may be sparse.
    key_metric_columns = [
        "revenue",
        "gross_profit",
        "operating_income",
        "ebitda",
        "net_income",
        "operating_cash_flow",
        "cash_and_equivalents",
        "total_debt",
    ]
    metrics = metrics[~_empty_or_all_na(metrics, key_metric_columns)].copy()

    if metrics.empty:
        warnings.warn(
            "Financial metric data was not available from yfinance for this ticker.",
            stacklevel=2,
        )
        return _empty_metrics_frame()

    _warn_if_missing(metrics["revenue"], "Revenue")
    _warn_if_missing(metrics["net_income"], "Net income")

    if "Period" not in metrics.columns:
        metrics["Period"] = metrics["Year"].apply(
            lambda value: str(int(value)) if pd.notna(value) else np.nan
        )
    metrics["Year"] = pd.to_numeric(metrics["Year"], errors="coerce")
    for column in FULL_SCHEMA:
        if column not in metrics.columns:
            metrics[column] = np.nan

    numeric_columns = [column for column in FULL_SCHEMA if column not in {"Period", "Year"}]
    for column in numeric_columns:
        metrics[column] = pd.to_numeric(metrics[column], errors="coerce").astype(float)

    latest_ebitda_source = (
        metrics["ebitda_source"].iloc[-1]
        if "ebitda_source" in metrics.columns and not metrics.empty
        else "unavailable"
    )
    metrics["Period"] = metrics["Period"].astype("string")
    metrics = metrics[FULL_SCHEMA].sort_values(
        ["Year", "Period"], ascending=True
    ).reset_index(drop=True)
    metrics.attrs["warnings"] = []
    metrics.attrs["ebitda_note"] = (
        "EBITDA is often unavailable or less meaningful for banks, lenders, insurers, and other financial companies."
    )
    metrics.attrs["ebitda_has_values"] = bool(metrics["ebitda"].dropna().shape[0] > 0)
    metrics.attrs["ebitda_source_latest"] = latest_ebitda_source
    if metrics["revenue"].dropna().empty:
        metrics.attrs["warnings"].append("Revenue data was not available from yfinance for this ticker.")
    if metrics["net_income"].dropna().empty:
        metrics.attrs["warnings"].append("Net income data was not available from yfinance for this ticker.")
    if not _is_financial_sector(sector) and metrics["ebitda"].dropna().empty:
        metrics.attrs["warnings"].append("EBITDA data was not available and could not be approximated from the loaded statements.")
    return metrics


def build_business_quality_score(
    metrics_df: pd.DataFrame,
    company_info_df: pd.DataFrame,
) -> dict[str, object]:
    """
    Build a transparent 0-100 business quality score from simple rules.
    """
    info_row = (
        company_info_df.iloc[0]
        if isinstance(company_info_df, pd.DataFrame) and not company_info_df.empty
        else {}
    )
    sector = info_row.get("sector") if hasattr(info_row, "get") else None
    is_financial = _is_financial_sector(sector)

    revenue_growth = _latest_numeric_value(metrics_df, "revenue_growth_pct")
    net_income = _latest_numeric_value(metrics_df, "net_income")
    free_cash_flow = _latest_numeric_value(metrics_df, "free_cash_flow")
    net_cash_debt = _latest_numeric_value(metrics_df, "net_cash_debt")
    latest_margin = _latest_numeric_value(metrics_df, "net_income_margin_pct")
    ev_to_revenue = pd.to_numeric(
        info_row.get("ev_to_revenue") if hasattr(info_row, "get") else None,
        errors="coerce",
    )
    ev_to_ebitda = pd.to_numeric(
        info_row.get("ev_to_ebitda") if hasattr(info_row, "get") else None,
        errors="coerce",
    )
    price_to_sales = pd.to_numeric(
        info_row.get("price_to_sales") if hasattr(info_row, "get") else None,
        errors="coerce",
    )

    strengths: list[str] = []
    risks: list[str] = []
    score = 50

    prior_revenue_growth = None
    if isinstance(metrics_df, pd.DataFrame) and "revenue_growth_pct" in metrics_df.columns:
        revenue_growth_series = pd.to_numeric(metrics_df["revenue_growth_pct"], errors="coerce").dropna()
        if len(revenue_growth_series) >= 2:
            prior_revenue_growth = float(revenue_growth_series.iloc[-2])

    if revenue_growth is not None:
        if revenue_growth >= 0.15:
            score += 10
            strengths.append(f"Revenue growth is strong at {revenue_growth:.1%}.")
        elif revenue_growth >= 0.05:
            score += 4
            strengths.append(f"Revenue is still growing at {revenue_growth:.1%}.")
        elif revenue_growth < 0:
            score -= 12
            risks.append(f"Revenue declined {abs(revenue_growth):.1%} in the latest period.")
    else:
        score += 1

    if revenue_growth is not None and prior_revenue_growth is not None and revenue_growth < prior_revenue_growth:
        score -= 5
        risks.append("Revenue growth slowed versus the prior period.")

    if net_income is not None:
        if net_income > 0:
            score += 8
            strengths.append("The business is currently profitable.")
        elif net_income < 0:
            score -= 10
            risks.append("The business is currently unprofitable.")
    else:
        score += 1

    if free_cash_flow is not None:
        if free_cash_flow > 0:
            score += 8
            strengths.append("Free cash flow is positive.")
        elif free_cash_flow < 0:
            score -= 9 if not is_financial else 4
            risks.append("Free cash flow is negative.")
    else:
        score += 1

    if net_cash_debt is not None:
        if net_cash_debt > 0:
            score += 7
            strengths.append("The balance sheet is in a net cash position.")
        elif net_cash_debt < 0:
            score -= 6
            risks.append("The balance sheet is in a net debt position.")
    else:
        score += 1

    if isinstance(metrics_df, pd.DataFrame) and "net_income_margin_pct" in metrics_df.columns:
        margins = pd.to_numeric(metrics_df["net_income_margin_pct"], errors="coerce").dropna()
        if len(margins) >= 2:
            margin_delta = float(margins.iloc[-1] - margins.iloc[-2])
            if margin_delta > 0.01:
                score += 5
                strengths.append("Net income margin improved versus the prior period.")
            elif margin_delta < -0.01:
                score -= 7
                risks.append("Net income margin deteriorated versus the prior period.")
        elif latest_margin is not None and latest_margin > 0:
            score += 3

    valuation_points_awarded = False
    if pd.notna(ev_to_ebitda):
        valuation_points_awarded = True
        if ev_to_ebitda <= 12:
            score += 5
            strengths.append("EV/EBITDA looks reasonable versus typical growth equity ranges.")
        elif ev_to_ebitda >= 18:
            score -= 7
            risks.append("EV/EBITDA looks elevated.")
    elif pd.notna(ev_to_revenue):
        valuation_points_awarded = True
        if ev_to_revenue <= 5:
            score += 4
            strengths.append("EV/Revenue looks reasonable.")
        elif ev_to_revenue >= 8:
            score -= 6
            risks.append("EV/Revenue looks elevated.")
    elif pd.notna(price_to_sales):
        valuation_points_awarded = True
        if price_to_sales <= 4:
            score += 3
        elif price_to_sales >= 8:
            score -= 5
            risks.append("Price-to-sales looks elevated.")

    if not valuation_points_awarded:
        score += 1

    ebitda_available = bool(metrics_df.attrs.get("ebitda_has_values", False)) if isinstance(metrics_df, pd.DataFrame) else False
    if not ebitda_available:
        score -= 4 if not is_financial else 1
        risks.append("EBITDA is unavailable or could not be approximated from the loaded statements.")

    if is_financial:
        score -= 2
        risks.append("Financial Services companies often make EBITDA and free cash flow less comparable to non-financial businesses.")

    score = int(max(0, min(100, score)))
    if score >= 85:
        label = "Excellent"
    elif score >= 70:
        label = "Strong"
    elif score >= 50:
        label = "Mixed"
    else:
        label = "Weak"

    return {
        "score": score,
        "label": label,
        "strengths": strengths[:5] or ["Limited data was available to identify clear strengths."],
        "risks": risks[:5] or ["Limited data was available to identify specific risks from the current rules-based screen."],
        "explanation": "This is a rules-based research score built from reported growth, profitability, cash flow, balance sheet, margin trend, and basic valuation inputs. It is not investment advice.",
    }


def _metric_series(metrics_df: pd.DataFrame, column: str) -> pd.Series:
    """
    Return a clean numeric metric series.
    """
    if not isinstance(metrics_df, pd.DataFrame) or metrics_df.empty or column not in metrics_df.columns:
        return pd.Series(dtype="float64")
    return pd.to_numeric(metrics_df[column], errors="coerce").dropna()


def _latest_and_prior(metrics_df: pd.DataFrame, column: str) -> tuple[float | None, float | None]:
    """
    Return the latest and prior values for a metric.
    """
    series = _metric_series(metrics_df, column)
    if series.empty:
        return None, None
    latest = float(series.iloc[-1])
    prior = float(series.iloc[-2]) if len(series) > 1 else None
    return latest, prior


def _delta_direction(
    latest: float | None,
    prior: float | None,
    positive_label: str,
    negative_label: str,
    stable_label: str,
    tolerance: float = 0.02,
) -> str:
    """
    Convert two values into a simple directional label.
    """
    if latest is None or prior is None:
        return "unavailable"
    baseline = abs(prior) if prior not in (0, None) else 1.0
    delta = (latest - prior) / baseline
    if abs(delta) <= tolerance:
        return stable_label
    return positive_label if delta > 0 else negative_label


def detect_metric_trends(metrics_df: pd.DataFrame) -> dict[str, str]:
    """
    Detect simple trends from the latest two observations.
    """
    revenue_growth_latest, revenue_growth_prior = _latest_and_prior(metrics_df, "revenue_growth_pct")
    net_income_latest, net_income_prior = _latest_and_prior(metrics_df, "net_income")
    free_cash_flow_latest, free_cash_flow_prior = _latest_and_prior(metrics_df, "free_cash_flow")
    margin_latest, margin_prior = _latest_and_prior(metrics_df, "net_income_margin_pct")

    return {
        "revenue_growth_trend": _delta_direction(
            revenue_growth_latest,
            revenue_growth_prior,
            "accelerating",
            "decelerating",
            "stable",
            tolerance=0.1,
        ),
        "net_income_trend": _delta_direction(
            net_income_latest,
            net_income_prior,
            "improving",
            "deteriorating",
            "stable",
            tolerance=0.05,
        ),
        "free_cash_flow_trend": _delta_direction(
            free_cash_flow_latest,
            free_cash_flow_prior,
            "improving",
            "deteriorating",
            "stable",
            tolerance=0.05,
        ),
        "margin_trend": _delta_direction(
            margin_latest,
            margin_prior,
            "expanding",
            "compressing",
            "stable",
            tolerance=0.05,
        ),
    }


def _format_change(value: float | None, kind: str) -> str:
    """
    Format a change value for narrative bullets.
    """
    if value is None:
        return "unavailable"
    if kind == "percent":
        return f"{value:+.1%}"
    if kind == "money":
        return format_money(value)
    return f"{value:+.2f}"


def _format_signed_money(latest: float | None, prior: float | None) -> str:
    """
    Format money delta between two periods.
    """
    if latest is None or prior is None:
        return "unavailable"
    delta = latest - prior
    sign = "+" if delta >= 0 else "-"
    return f"{sign}{format_money(abs(delta))}"


def build_what_changed(metrics_df: pd.DataFrame) -> list[str]:
    """
    Build deterministic bullets comparing the latest period with the prior period.
    """
    bullets: list[str] = []
    metric_config = [
        ("revenue", "Revenue", "money"),
        ("revenue_growth_pct", "Revenue growth", "percent"),
        ("net_income", "Net income", "money"),
        ("ebitda", "EBITDA", "money"),
        ("ebitda_margin_pct", "EBITDA margin", "percent"),
        ("free_cash_flow", "Free cash flow", "money"),
        ("cash_and_equivalents", "Cash", "money"),
        ("total_debt", "Debt", "money"),
        ("net_cash_debt", "Net cash / debt", "money"),
    ]

    for column, label, kind in metric_config:
        latest, prior = _latest_and_prior(metrics_df, column)
        if latest is None or prior is None:
            continue

        if kind == "percent":
            delta = latest - prior
            bullets.append(f"{label} changed by {_format_change(delta, 'percent')} versus the prior period.")
        else:
            bullets.append(f"{label} changed by {_format_signed_money(latest, prior)} versus the prior period.")

    return bullets or ["What changed versus the prior period is unavailable from the currently loaded metrics."]


def build_narrative_package(
    metrics_df: pd.DataFrame,
    company_info_df: pd.DataFrame,
) -> dict[str, object]:
    """
    Build a deterministic narrative and signals package from metrics only.
    """
    info_row = (
        company_info_df.iloc[0]
        if isinstance(company_info_df, pd.DataFrame) and not company_info_df.empty
        else {}
    )
    sector = info_row.get("sector") if hasattr(info_row, "get") else None
    is_financial = _is_financial_sector(sector)

    trends = detect_metric_trends(metrics_df)
    changes = build_what_changed(metrics_df)

    revenue_growth = _latest_numeric_value(metrics_df, "revenue_growth_pct")
    net_income = _latest_numeric_value(metrics_df, "net_income")
    free_cash_flow = _latest_numeric_value(metrics_df, "free_cash_flow")
    net_cash_debt = _latest_numeric_value(metrics_df, "net_cash_debt")
    ebitda = _latest_numeric_value(metrics_df, "ebitda")
    ebitda_margin = _latest_numeric_value(metrics_df, "ebitda_margin_pct")
    margin = _latest_numeric_value(metrics_df, "net_income_margin_pct")

    bullish: list[str] = []
    bearish: list[str] = []
    neutral: list[str] = []
    improved: list[str] = []
    weakened: list[str] = []

    if revenue_growth is not None:
        if revenue_growth > 0.1:
            bullish.append(f"Revenue growth is strong at {revenue_growth:.1%}.")
        elif revenue_growth < 0:
            bearish.append(f"Revenue is declining at {abs(revenue_growth):.1%}.")
        else:
            neutral.append(f"Revenue growth is modest at {revenue_growth:.1%}.")

    if net_income is not None:
        if net_income > 0:
            bullish.append("The company is profitable on a net income basis.")
        else:
            bearish.append("The company is loss-making on a net income basis.")

    if free_cash_flow is not None:
        if free_cash_flow > 0:
            bullish.append("Free cash flow is positive.")
        elif free_cash_flow < 0:
            bearish.append("Free cash flow is negative.")

    if net_cash_debt is not None:
        if net_cash_debt > 0:
            bullish.append("The balance sheet is in a net cash position.")
        elif net_cash_debt < 0:
            bearish.append("The balance sheet is in a net debt position.")

    if ebitda is None:
        neutral.append("EBITDA is unavailable from the current data pull.")
    elif ebitda_margin is not None:
        neutral.append(f"EBITDA margin is {ebitda_margin:.1%}.")

    if trends["revenue_growth_trend"] == "accelerating":
        improved.append("Revenue growth accelerated versus the prior period.")
    elif trends["revenue_growth_trend"] == "decelerating":
        weakened.append("Revenue growth decelerated versus the prior period.")

    if trends["net_income_trend"] == "improving":
        improved.append("Net income improved versus the prior period.")
    elif trends["net_income_trend"] == "deteriorating":
        weakened.append("Net income deteriorated versus the prior period.")

    if trends["free_cash_flow_trend"] == "improving":
        improved.append("Free cash flow improved versus the prior period.")
    elif trends["free_cash_flow_trend"] == "deteriorating":
        weakened.append("Free cash flow deteriorated versus the prior period.")

    if trends["margin_trend"] == "expanding":
        improved.append("Margins expanded versus the prior period.")
    elif trends["margin_trend"] == "compressing":
        weakened.append("Margins compressed versus the prior period.")

    current_read_parts: list[str] = []
    if revenue_growth is not None:
        current_read_parts.append(f"growth is {trends['revenue_growth_trend']}")
    if net_income is not None:
        current_read_parts.append("the company is profitable" if net_income > 0 else "the company is unprofitable")
    if free_cash_flow is not None:
        current_read_parts.append("free cash flow is positive" if free_cash_flow > 0 else "free cash flow is negative")

    current_read = "; ".join(current_read_parts).capitalize() + "." if current_read_parts else "Current operating momentum is unavailable from the loaded metrics."

    key_tension = "unavailable"
    if bullish and bearish:
        key_tension = f"{bullish[0]} However, {bearish[0].lower()}"
    elif bearish:
        key_tension = bearish[0]
    elif bullish:
        key_tension = bullish[0]

    watch_list: list[str] = []
    if trends["revenue_growth_trend"] in {"accelerating", "decelerating"}:
        watch_list.append(f"Whether revenue growth stays {trends['revenue_growth_trend']}.")
    if trends["margin_trend"] in {"expanding", "compressing"}:
        watch_list.append(f"Whether margins keep {trends['margin_trend']}.")
    if free_cash_flow is not None:
        watch_list.append("Whether free cash flow turns sustainably positive." if free_cash_flow < 0 else "Whether free cash flow stays positive.")
    if net_cash_debt is not None and net_cash_debt < 0:
        watch_list.append("Whether leverage improves from the current net debt position.")
    if is_financial:
        neutral.append("Financial-company accounting can make cash flow and EBITDA less comparable to non-financial businesses.")

    return {
        "trends": trends,
        "what_changed": changes,
        "narrative": {
            "current_read": current_read,
            "what_improved": improved[:5] or ["Unavailable"],
            "what_weakened": weakened[:5] or ["Unavailable"],
            "key_tension": key_tension,
            "what_to_watch_next": watch_list[:5] or ["Unavailable"],
        },
        "signals": {
            "bullish": bullish[:5] or ["Unavailable"],
            "bearish": bearish[:5] or ["Unavailable"],
            "neutral": neutral[:5] or ["Unavailable"],
        },
        "is_financial": is_financial,
        "sector": sector or "N/A",
    }
