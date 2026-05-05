# FRONTEND_INTEGRATION_NOTES

## 1. App structure

- The app is a single Streamlit entrypoint: [app.py](/C:/Users/will/python/Research%20Terminal/dbr-research-terminal/app.py)
- Core logic lives in `src/`:
  - [src/data_loader.py](/C:/Users/will/python/Research%20Terminal/dbr-research-terminal/src/data_loader.py): yfinance data access and normalization
  - [src/metrics.py](/C:/Users/will/python/Research%20Terminal/dbr-research-terminal/src/metrics.py): financial metrics, quality score, narrative/trend logic
  - [src/charts.py](/C:/Users/will/python/Research%20Terminal/dbr-research-terminal/src/charts.py): company/comparison Plotly charts and number formatting helpers
  - [src/portfolio.py](/C:/Users/will/python/Research%20Terminal/dbr-research-terminal/src/portfolio.py): portfolio analysis, benchmark analysis, portfolio charts
  - [src/report_builder.py](/C:/Users/will/python/Research%20Terminal/dbr-research-terminal/src/report_builder.py): export helpers; not part of the normal UI flow
- There is no separate frontend app, REST API server, database layer, or client-side data contract. The current “frontend” calls Python functions directly.

## 2. Main frontend pages/components

- Sidebar navigation in `app.py`:
  - `Home`
  - `Company Research`
  - `Peer Comparison`
  - `Portfolio Lab`
- Main page flows:
  - `Home`: landing page only
  - `Company Research`: ticker input, annual/quarterly toggle, timeframe selector, display-period selector, KPI cards, executive summary, charts, valuation, narrative, metrics table
  - `Peer Comparison`: comma-separated tickers, annual/quarterly toggle, timeframe selector, summary cards, best/worst cards, multi-ticker price charts, comparison charts, comparison table
  - `Portfolio Lab`: holdings editor, benchmark selector, portfolio scorecards, benchmark comparison, portfolio charts, what-if analysis
- Reusable UI helpers in `app.py`:
  - `_render_page_header`
  - `_render_panel_header`
  - `_render_metric_card_grid`
  - `_render_summary_strip`
  - `_render_dbr_insight`
  - `_render_inline_alert`

## 3. Backend/API routes the frontend depends on

- There are no HTTP API routes in this repo.
- Current UI dependencies are direct Python calls:
  - Data loading:
    - `load_all_financial_data(ticker, period_type, price_period)`
    - `get_price_history(ticker, period)`
    - `summarize_data_availability(data, period_type)`
  - Metrics and narrative:
    - `calculate_financial_metrics(income_statement, balance_sheet, cash_flow_statement, sector=None)`
    - `build_business_quality_score(metrics_df, company_info_df)`
    - `build_narrative_package(metrics_df, company_info_df)`
  - Charts:
    - `create_all_charts(metrics_df, price_history_df, ticker, price_period=...)`
    - `create_comparison_bar_chart(...)`
    - `create_multi_ticker_price_chart(...)`
    - portfolio chart builders from `src/portfolio.py`
  - Portfolio:
    - `clean_holdings(...)`
    - `analyze_portfolio(...)`
    - `compare_portfolio_scenarios(...)`

If v0 introduces a new frontend shell, it should preserve these call boundaries or wrap them, not rewrite them.

## 4. Env variables that should not be touched

- No environment variables are currently used in the repo.
- No `os.getenv`, `st.secrets`, `.env`, API keys, or database connection settings were found.
- v0 should not introduce or rename env requirements unless asked separately.

## 5. Data shapes returned to the frontend

### Company data bundle

`load_all_financial_data(...)` returns:

```python
{
  "company_info": pd.DataFrame,         # one row
  "price_history": pd.DataFrame,        # many rows
  "income_statement": pd.DataFrame,     # row-based periods
  "balance_sheet": pd.DataFrame,        # row-based periods
  "cash_flow_statement": pd.DataFrame,  # row-based periods
}
```

### `company_info` shape

One-row DataFrame with fields such as:

- `ticker`
- `name`
- `sector`
- `market_cap`
- `enterprise_value`
- `trailing_pe`
- `forward_pe`
- `price_to_sales`
- `price_to_book`
- `ev_to_revenue`
- `ev_to_ebitda`
- `beta`
- `fifty_two_week_high`
- `fifty_two_week_low`
- `current_price`

### `price_history` shape

Normalized DataFrame with columns:

- `Date`
- `Open`
- `High`
- `Low`
- `Close`
- `Adj Close`
- `Volume`

### Financial statement shapes

Normalized row-based DataFrames with:

- `Period`
- `Year`
- `Date`
- additional line-item columns from yfinance

Notes:

- Annual `Period` looks like `2025`
- Quarterly `Period` looks like `2025Q1`
- These frames are intentionally sparse and can contain missing values

### `metrics_df` shape

`calculate_financial_metrics(...)` returns a DataFrame with a stable schema:

- `Period`
- `Year`
- `revenue`
- `gross_profit`
- `operating_income`
- `ebitda`
- `net_income`
- `operating_cash_flow`
- `capital_expenditures`
- `free_cash_flow`
- `cash_and_equivalents`
- `total_debt`
- `net_cash_debt`
- `revenue_growth_pct`
- `ebitda_margin_pct`
- `gross_margin_pct`
- `operating_margin_pct`
- `net_income_margin_pct`
- `free_cash_flow_margin_pct`
- `depreciation_and_amortization`
- `shares_outstanding`

Important `metrics_df.attrs` metadata used by the UI:

- `warnings`
- `ebitda_note`
- `ebitda_has_values`
- `ebitda_source_latest`

### Business quality score shape

`build_business_quality_score(...)` returns:

```python
{
  "score": int,
  "label": str,
  "strengths": list[str],
  "risks": list[str],
  "explanation": str,
}
```

### Narrative package shape

`build_narrative_package(...)` returns a dict used by the Narrative tab. It includes trend/narrative-style fields such as:

- trend labels
- `what_changed` bullets
- `investment_narrative`
- `signals`

v0 should inspect the exact keys before replacing that tab UI, but should not change the function contract.

### Portfolio analysis shape

`analyze_portfolio(...)` returns:

```python
{
  "metrics": {
    "cumulative_return": float,
    "annualized_return": float,
    "annualized_volatility": float,
    "sharpe_ratio": float,
    "max_drawdown": float,
  },
  "benchmark_metrics": {
    "cumulative_return": float | None,
    "annualized_return": float | None,
    "excess_return": float | None,
    "beta": float | None,
    "correlation": float | None,
    "tracking_error": float | None,
    "max_drawdown": float | None,
    "max_drawdown_difference": float | None,
  },
  "benchmark_available": bool,
  "benchmark_ticker": str,
  "warnings": list[str],
  "returns_df": pd.DataFrame,
  "correlation_df": pd.DataFrame,
  "portfolio_equity": pd.Series,
  "portfolio_drawdown": pd.Series,
  "benchmark_returns": pd.Series,
  "benchmark_equity": pd.Series,
  "benchmark_drawdown": pd.Series,
  "holdings_normalized_df": pd.DataFrame,
  "holdings_raw_df": pd.DataFrame,
  "weights_df": pd.DataFrame,
}
```

### What-if analysis shape

`compare_portfolio_scenarios(...)` returns:

```python
{
  "current_metrics": dict,
  "proposed_metrics": dict,
  "current_largest_holding": float,
  "proposed_largest_holding": float,
  "current_cash_allocation": float,
  "proposed_cash_allocation": float,
  "summary": list[str],
  "deltas": dict,
}
```

## 6. Areas that v0 can safely redesign

- Overall page layout and visual hierarchy
- Sidebar styling and navigation presentation
- Card styling, spacing, typography, and responsive layout
- Section ordering within a page, as long as the same data is shown
- Chart placement and chart containers
- Data table presentation
- Form layout for:
  - ticker input
  - financial period selector
  - timeframe selector
  - comparison tickers
  - portfolio holdings editor wrapper UI
- Empty states, warning presentation, helper text, and explanatory copy

## 7. Areas v0 should not modify

- Do not rewrite `src/data_loader.py`
- Do not change yfinance field mapping or normalization rules
- Do not change `calculate_financial_metrics(...)`
- Do not change business quality scoring rules
- Do not change narrative/trend logic
- Do not change portfolio math in `src/portfolio.py`
- Do not change the shapes of returned DataFrames, Series, dicts, or `attrs`
- Do not rename keys expected by `app.py`
- Do not introduce new API routes or a new backend contract unless explicitly requested
- Do not change caching behavior or session-state behavior without a separate task
- Do not change export/report logic unless that becomes part of a separate frontend task

## Practical guidance for v0

- Treat the current Python functions as the stable backend contract.
- Redesign presentation, not computation.
- If a new frontend abstraction is needed, wrap existing function outputs rather than reshaping them at the source.
- Preserve support for:
  - annual and quarterly company analysis
  - peer comparison
  - portfolio benchmark analysis
  - what-if portfolio analysis
