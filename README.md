# DBR Research Terminal

DBR Research Terminal is a Streamlit app for rules-based equity research. It combines Yahoo Finance/yfinance market and financial statement data with deterministic metrics, valuation snapshots, business quality scoring, narrative analysis, and comparison tools.

## Features

- Single-company analysis with:
  - KPI cards
  - executive snapshot
  - valuation and quality scoring
  - narrative and signals
  - annual or quarterly financial views
- Comparison mode with:
  - side-by-side metrics table
  - visual ranking charts
  - best/worst summary
- Streamlit UI with a dark DBR-style layout

## Setup

1. Create and activate a virtual environment if you want one.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run the app:

```bash
streamlit run app.py
```

## Notes

- Data is sourced from Yahoo Finance via `yfinance`.
- Financial statement coverage can vary by ticker.
- ETFs, funds, and some financial institutions may have partial or missing fields.
- This app is a rules-based research aid, not investment advice.

## Deployment

This project is ready to deploy to Streamlit Community Cloud.

Recommended settings:

- Main file path: `app.py`
- Python dependencies: `requirements.txt`

After deployment, Streamlit Community Cloud will install the listed packages and run:

```bash
streamlit run app.py
```
