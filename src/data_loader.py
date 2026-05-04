from __future__ import annotations

from typing import Any

import pandas as pd
import yfinance as yf


def _empty_price_frame() -> pd.DataFrame:
    """Return a consistent empty price-history frame."""
    return pd.DataFrame(
        columns=["Date", "Open", "High", "Low", "Close", "Adj Close", "Volume"]
    )


def _empty_statement_frame() -> pd.DataFrame:
    """Return a consistent empty financial-statement frame."""
    return pd.DataFrame(columns=["Period", "Year", "Date"])


def _normalize_label(label: object) -> str:
    """
    Normalize raw yfinance line-item labels into a consistent column format.
    """
    text = str(label).strip()
    text = " ".join(text.split())
    return text


def _normalize_period_type(period_type: str) -> str:
    """
    Normalize the requested financial statement period type.
    """
    normalized = str(period_type).strip().lower()
    return "quarterly" if normalized == "quarterly" else "annual"


def _normalize_price_history(history: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize yfinance price history output into a clean DataFrame.

    The result always uses a Date column and keeps standard OHLCV fields when present.
    """
    if not isinstance(history, pd.DataFrame) or history.empty:
        return _empty_price_frame()

    cleaned = history.copy().reset_index()

    if "Date" not in cleaned.columns and "Datetime" in cleaned.columns:
        cleaned = cleaned.rename(columns={"Datetime": "Date"})

    expected_columns = ["Date", "Open", "High", "Low", "Close", "Adj Close", "Volume"]
    available_columns = [col for col in expected_columns if col in cleaned.columns]
    cleaned = cleaned[available_columns].copy()

    if "Date" in cleaned.columns:
        cleaned["Date"] = pd.to_datetime(cleaned["Date"], errors="coerce")

    numeric_columns = ["Open", "High", "Low", "Close", "Adj Close", "Volume"]
    for column in numeric_columns:
        if column in cleaned.columns:
            cleaned[column] = pd.to_numeric(cleaned[column], errors="coerce")

    cleaned = cleaned.dropna(subset=["Date"]).sort_values("Date").reset_index(drop=True)
    return cleaned


def _build_period_label(date_value: pd.Timestamp, period_type: str) -> str | None:
    """
    Convert a statement date into an annual or quarterly period label.
    """
    if pd.isna(date_value):
        return None
    if period_type == "quarterly":
        quarter = ((int(date_value.month) - 1) // 3) + 1
        return f"{int(date_value.year)}Q{quarter}"
    return str(int(date_value.year))


def _normalize_statement(statement: Any, period_type: str = "annual") -> pd.DataFrame:
    """
    Convert a yfinance statement into a year-indexed DataFrame.

    yfinance returns statements with line items as rows and periods as columns.
    This function transposes that shape so rows become periods/years.
    """
    normalized_period_type = _normalize_period_type(period_type)

    if not isinstance(statement, pd.DataFrame) or statement.empty:
        return _empty_statement_frame()

    cleaned = statement.copy()
    cleaned.index = [_normalize_label(index) for index in cleaned.index]
    cleaned = cleaned.transpose()
    cleaned.index = pd.to_datetime(cleaned.index, errors="coerce")
    cleaned = cleaned[~cleaned.index.isna()].sort_index()
    cleaned.index.name = "Date"
    cleaned = cleaned.reset_index()
    cleaned["Year"] = cleaned["Date"].dt.year
    cleaned["Period"] = cleaned["Date"].apply(
        lambda value: _build_period_label(value, normalized_period_type)
    )

    # Put Year first for readability while keeping the original Date column.
    ordered_columns = ["Period", "Year", "Date"] + [
        col for col in cleaned.columns if col not in {"Period", "Year", "Date"}
    ]
    cleaned = cleaned[ordered_columns]

    # Best-effort numeric coercion for statement values.
    for column in cleaned.columns:
        if column not in {"Period", "Year", "Date"}:
            cleaned[column] = pd.to_numeric(cleaned[column], errors="coerce").astype(float)

    cleaned["Year"] = pd.to_numeric(cleaned["Year"], errors="coerce")
    cleaned = cleaned.dropna(subset=["Date", "Period"]).sort_values(
        ["Date", "Period"], ascending=True
    ).reset_index(drop=True)

    return cleaned


def get_price_history(ticker: str, period: str = "5y") -> pd.DataFrame:
    """
    Fetch historical stock prices for a ticker.

    Returns a clean DataFrame with a Date column and standard price fields.
    On any failure, returns an empty DataFrame with the expected columns.
    """
    try:
        history = yf.Ticker(ticker).history(period=period, auto_adjust=False)
    except Exception:
        return _empty_price_frame()

    return _normalize_price_history(history)


def _get_income_statement_source(ticker: yf.Ticker, period_type: str) -> Any:
    """
    Resolve the appropriate yfinance income statement object.
    """
    if period_type == "quarterly":
        for attribute in ("quarterly_income_stmt", "quarterly_financials"):
            value = getattr(ticker, attribute, None)
            if value is not None:
                return value
        return None
    return getattr(ticker, "financials", None)


def _get_balance_sheet_source(ticker: yf.Ticker, period_type: str) -> Any:
    """
    Resolve the appropriate yfinance balance sheet object.
    """
    if period_type == "quarterly":
        return getattr(ticker, "quarterly_balance_sheet", None)
    return getattr(ticker, "balance_sheet", None)


def _get_cash_flow_source(ticker: yf.Ticker, period_type: str) -> Any:
    """
    Resolve the appropriate yfinance cash flow statement object.
    """
    if period_type == "quarterly":
        for attribute in ("quarterly_cashflow", "quarterly_cash_flow"):
            value = getattr(ticker, attribute, None)
            if value is not None:
                return value
        return None
    return getattr(ticker, "cashflow", None)


def get_income_statement(ticker: str, period_type: str = "annual") -> pd.DataFrame:
    """
    Fetch the annual income statement and return it with rows = years.

    On failure or missing data, returns an empty DataFrame.
    """
    normalized_period_type = _normalize_period_type(period_type)
    try:
        statement = _get_income_statement_source(yf.Ticker(ticker), normalized_period_type)
    except Exception:
        return _empty_statement_frame()

    return _normalize_statement(statement, period_type=normalized_period_type)


def get_balance_sheet(ticker: str, period_type: str = "annual") -> pd.DataFrame:
    """
    Fetch the annual balance sheet and return it with rows = years.

    On failure or missing data, returns an empty DataFrame.
    """
    normalized_period_type = _normalize_period_type(period_type)
    try:
        statement = _get_balance_sheet_source(yf.Ticker(ticker), normalized_period_type)
    except Exception:
        return _empty_statement_frame()

    return _normalize_statement(statement, period_type=normalized_period_type)


def get_cash_flow_statement(ticker: str, period_type: str = "annual") -> pd.DataFrame:
    """
    Fetch the annual cash flow statement and return it with rows = years.

    On failure or missing data, returns an empty DataFrame.
    """
    normalized_period_type = _normalize_period_type(period_type)
    try:
        statement = _get_cash_flow_source(yf.Ticker(ticker), normalized_period_type)
    except Exception:
        return _empty_statement_frame()

    return _normalize_statement(statement, period_type=normalized_period_type)


def get_company_info(ticker: str) -> pd.DataFrame:
    """
    Fetch a small set of basic company details.

    Returns a one-row DataFrame so downstream code can treat the result as tabular data.
    Missing values are kept as None instead of raising errors.
    """
    ticker_obj = yf.Ticker(ticker)

    try:
        info = ticker_obj.info
    except Exception:
        info = {}

    if not isinstance(info, dict):
        info = {}

    try:
        fast_info = ticker_obj.fast_info
    except Exception:
        fast_info = {}

    if fast_info is None:
        fast_info = {}

    def _pick_numeric(*values: Any) -> float | None:
        for value in values:
            numeric_value = pd.to_numeric(value, errors="coerce")
            if pd.notna(numeric_value):
                return float(numeric_value)
        return None

    current_price = _pick_numeric(
        info.get("currentPrice"),
        info.get("regularMarketPrice"),
        getattr(fast_info, "lastPrice", None) if not isinstance(fast_info, dict) else fast_info.get("lastPrice"),
        getattr(fast_info, "last_price", None) if not isinstance(fast_info, dict) else fast_info.get("last_price"),
    )
    fifty_two_week_high = _pick_numeric(
        info.get("fiftyTwoWeekHigh"),
        getattr(fast_info, "yearHigh", None) if not isinstance(fast_info, dict) else fast_info.get("yearHigh"),
        getattr(fast_info, "year_high", None) if not isinstance(fast_info, dict) else fast_info.get("year_high"),
    )
    fifty_two_week_low = _pick_numeric(
        info.get("fiftyTwoWeekLow"),
        getattr(fast_info, "yearLow", None) if not isinstance(fast_info, dict) else fast_info.get("yearLow"),
        getattr(fast_info, "year_low", None) if not isinstance(fast_info, dict) else fast_info.get("year_low"),
    )

    row = {
        "ticker": ticker.upper(),
        "name": info.get("longName") or info.get("shortName"),
        "sector": info.get("sector"),
        "market_cap": pd.to_numeric(info.get("marketCap"), errors="coerce"),
        "enterprise_value": pd.to_numeric(info.get("enterpriseValue"), errors="coerce"),
        "trailing_pe": pd.to_numeric(info.get("trailingPE"), errors="coerce"),
        "forward_pe": pd.to_numeric(info.get("forwardPE"), errors="coerce"),
        "price_to_sales": pd.to_numeric(info.get("priceToSalesTrailing12Months"), errors="coerce"),
        "price_to_book": pd.to_numeric(info.get("priceToBook"), errors="coerce"),
        "ev_to_revenue": pd.to_numeric(
            info.get("enterpriseToRevenue"), errors="coerce"
        ),
        "ev_to_ebitda": pd.to_numeric(
            info.get("enterpriseToEbitda"), errors="coerce"
        ),
        "beta": pd.to_numeric(info.get("beta"), errors="coerce"),
        "fifty_two_week_high": current_price * 0 + fifty_two_week_high if fifty_two_week_high is not None else pd.NA,
        "fifty_two_week_low": current_price * 0 + fifty_two_week_low if fifty_two_week_low is not None else pd.NA,
        "current_price": current_price if current_price is not None else pd.NA,
    }
    return pd.DataFrame([row])


def load_all_financial_data(
    ticker: str,
    period_type: str = "annual",
    price_period: str = "5y",
) -> dict[str, pd.DataFrame]:
    """
    Convenience wrapper for fetching all currently supported datasets for a ticker.

    This keeps the module easy to test in isolation before metrics/report logic exists.
    """
    normalized_ticker = ticker.strip().upper()
    normalized_period_type = _normalize_period_type(period_type)
    data = {
        "company_info": get_company_info(normalized_ticker),
        "price_history": get_price_history(normalized_ticker, period=price_period),
        "income_statement": get_income_statement(normalized_ticker, period_type=normalized_period_type),
        "balance_sheet": get_balance_sheet(normalized_ticker, period_type=normalized_period_type),
        "cash_flow_statement": get_cash_flow_statement(normalized_ticker, period_type=normalized_period_type),
    }

    if normalized_period_type == "quarterly":
        income_statement = data["income_statement"]
        balance_sheet = data["balance_sheet"]
        cash_flow_statement = data["cash_flow_statement"]
        print(f"[quarterly debug] income_statement shape: {income_statement.shape}")
        print(f"[quarterly debug] balance_sheet shape: {balance_sheet.shape}")
        print(f"[quarterly debug] cash_flow_statement shape: {cash_flow_statement.shape}")
        print(f"[quarterly debug] income_statement columns: {list(income_statement.columns)}")
        print("[quarterly debug] income_statement head:")
        print(income_statement.head().to_string())

    return data


def summarize_data_availability(
    data: dict[str, pd.DataFrame],
    period_type: str,
) -> dict[str, Any]:
    """
    Build a compact availability summary for the Streamlit diagnostic expander.
    """
    normalized_period_type = _normalize_period_type(period_type)
    income_statement = data.get("income_statement", pd.DataFrame())
    balance_sheet = data.get("balance_sheet", pd.DataFrame())
    cash_flow_statement = data.get("cash_flow_statement", pd.DataFrame())
    price_history = data.get("price_history", pd.DataFrame())

    latest_period = "N/A"
    periods_loaded = 0
    if isinstance(income_statement, pd.DataFrame) and not income_statement.empty and "Period" in income_statement.columns:
        period_series = income_statement["Period"].dropna().astype(str)
        if not period_series.empty:
            latest_period = period_series.iloc[-1]
            periods_loaded = int(period_series.nunique())

    latest_price_date = "N/A"
    if isinstance(price_history, pd.DataFrame) and not price_history.empty and "Date" in price_history.columns:
        latest_date = pd.to_datetime(price_history["Date"], errors="coerce").dropna()
        if not latest_date.empty:
            latest_price_date = latest_date.iloc[-1].strftime("%Y-%m-%d")

    return {
        "selected_period_type": normalized_period_type,
        "latest_financial_period": latest_period,
        "financial_periods_loaded": periods_loaded,
        "latest_stock_price_date": latest_price_date,
        "income_statement_available": bool(isinstance(income_statement, pd.DataFrame) and not income_statement.empty),
        "balance_sheet_available": bool(isinstance(balance_sheet, pd.DataFrame) and not balance_sheet.empty),
        "cash_flow_statement_available": bool(isinstance(cash_flow_statement, pd.DataFrame) and not cash_flow_statement.empty),
    }
