# Commodity Risk Platform

A Python and Streamlit research dashboard for exploring historical portfolio risk across commodity proxies and crypto assets. It calculates hypothetical P&L from signed USD notionals and historical returns; it does not place trades or represent live positions.

## What it does

- Shows portfolio exposure, historical daily P&L, volatility, and historical Value at Risk (VaR) and Expected Shortfall (ES).
- Lets you change asset notionals, ES confidence, and the confidence and lookback used by the rolling VaR backtest.
- Reports backtest breaches and Kupiec and Christoffersen statistical diagnostics, including consecutive breach runs.
- Breaks risk down by asset, shows return correlations, and estimates results under illustrative stress scenarios.
- Exports the dashboard's backtest and attribution data as CSV files.
- Handles the mixed trading calendars by carrying commodity closes across market closures while retaining observed Bitcoin and Ethereum weekend prices.

## Run locally

Use Python 3.15 to match the development environment used for this release.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
streamlit run app/pages/dashboard.py
```

The dashboard reads `data/processed/returns/aligned_returns.csv`, which is included in the repository. To rebuild the historical input from Yahoo Finance data, run:

```powershell
python -m src.data.download_prices
python -m src.data.clean_prices
python -m src.analytics.returns
```

The data download requires an internet connection. The SQLite loader is optional:

```powershell
python -m src.data.load_database
```

## How the calculations work

For each date, the app estimates portfolio P&L as the sum of each asset's signed USD notional multiplied by that asset's daily return. Historical VaR is a percentile of the portfolio's historical losses. Expected Shortfall is the average loss in the selected tail at or beyond that VaR cutoff.

The rolling VaR backtest uses only earlier observations to set each day's threshold, then checks whether that day's P&L crossed it. Kupiec's proportion-of-failures test checks the overall breach frequency. Christoffersen's independence test checks whether breaches cluster; conditional coverage combines both checks. These diagnostics are evidence about the historical backtest, not proof of future performance.

## Technology and architecture

| Technology | How this project uses it |
| --- | --- |
| Python | Data preparation, portfolio P&L, risk measures, backtests, stress scenarios, and dashboard logic |
| pandas and NumPy | Time-series alignment and numerical calculations |
| Streamlit | Interactive dashboard, controls, tables, and CSV downloads |
| Plotly | Interactive P&L, risk attribution, correlation, and stress charts |
| yfinance | Optional download of historical Yahoo Finance price data |
| SQLite and SQL | Relational schema plus scripts to load and inspect instruments, prices, and returns |
| pytest | Automated checks for the risk engine, rolling backtest, statistical tests, and command-line options |

The dashboard currently reads the aligned CSV directly. SQLite is a separate data-storage and learning component; the interactive dashboard is not yet querying the database. See [the interview guide](docs/interview_guide.md) for a walkthrough and a clear explanation of this distinction.

## Publish with Streamlit Community Cloud

1. Push this repository to GitHub.
2. In [Streamlit Community Cloud](https://share.streamlit.io/), create an app using repository `AshrayG/commodity-risk-platform`, branch `master`, and entrypoint `app/pages/dashboard.py`.
3. In Advanced settings, choose Python 3.15 to match the local environment, then deploy.

The app needs no API key or secrets to run because its historical input is committed with the project. Community Cloud installs the packages from the root `requirements.txt` and reads the theme in `.streamlit/config.toml`.

## Scope and limitations

- Positions and stress shocks are hypothetical. This is a research and learning project, not investment advice or a trading system.
- The commodity series are futures-based proxies; historical returns do not capture every real-world contract roll, transaction cost, funding cost, or liquidity constraint.
- Historical VaR and ES depend on the chosen period and historical sample. Backtest tests can have limited power, especially at high confidence levels or with short lookbacks.
- The dashboard currently relies on a prepared CSV rather than refreshing prices automatically when it starts.

## Project guide

- [Interview walkthrough](docs/interview_guide.md) — a plain-language explanation, example, architecture, and interview talking points.
- [VaR backtesting guide (PDF)](output/pdf/var_backtesting_for_beginners.pdf) — beginner explanation of breaches and the Kupiec and Christoffersen tests.
- [Comprehensive project guide (PDF)](output/pdf/commodity-risk-platform-comprehensive-guide.pdf)
