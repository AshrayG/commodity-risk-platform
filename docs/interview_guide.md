# Interview walkthrough: Commodity Risk Platform

## A short project pitch

> I built a Python dashboard that estimates historical risk for a hypothetical portfolio of commodity proxies and cryptocurrencies. It turns daily price data into aligned returns, estimates portfolio P&L from signed notionals, calculates historical VaR and Expected Shortfall, and checks rolling VaR forecasts with breach diagnostics. Streamlit and Plotly make the results interactive. I also designed a SQLite schema and scripts for storing and checking market data. The dashboard currently reads prepared CSV data, so connecting the live dashboard calculations to SQLite is a clear next step.

## What problem does it solve?

A portfolio can hold several products at once. Looking at each price separately does not show how the whole portfolio might move on a bad day. This project combines the products' historical returns with example position sizes, then summarizes how large past portfolio losses were and whether a simple risk threshold was breached too often or in clusters.

It is a learning and research tool. The positions and scenarios are hypothetical; it does not connect to a broker or make forecasts.

## How a price becomes a risk result

```text
Yahoo Finance history
        |
        v
Download and clean prices (Python / yfinance / pandas)
        |
        v
Align dates and calculate daily returns (pandas)
        |
        v
Multiply each return by its signed USD notional
        |
        v
Portfolio P&L -> VaR / Expected Shortfall / backtest
        |
        v
Interactive charts, diagnostics, and CSV downloads (Streamlit / Plotly)
```

The dashboard uses the prepared `data/processed/returns/aligned_returns.csv` file. Commodity markets close on some dates when crypto still trades. The return-building step carries the last observed commodity close over market closures, keeps actual Bitcoin and Ethereum weekend prices, and drops dates where a required input return is missing.

## The core portfolio calculation

For asset `i` on date `t`:

```text
asset P&L(i, t) = signed USD notional(i) * daily return(i, t)
portfolio P&L(t) = sum of asset P&L(i, t) across the portfolio
```

Example: suppose a portfolio is long $100,000 of an asset that rises 2%, and short $50,000 of another asset that falls 3%.

```text
Long position P&L  = $100,000 *  2% =  $2,000
Short position P&L = -$50,000 * -3% =  $1,500
Total P&L                                  $3,500
```

The negative notional represents a short. Multiplying a negative position by a negative return gives a positive P&L.

## VaR and Expected Shortfall

The app converts P&L into losses by changing the sign: a P&L of -$8,000 is an $8,000 loss. Historical VaR is a selected percentile of those historical losses. At 99% confidence, 99% of historical losses in the sample are at or below the VaR threshold and about 1% are beyond it. It is not a maximum-loss guarantee.

Expected Shortfall (ES) averages the losses at or beyond the chosen VaR cutoff. If the worst 1% of five example losses are $10,000, $12,000, $18,000, $20,000, and $40,000, then 99% ES for this tiny illustration is their average: $20,000. Real calculations use the full available history. Ties at the cutoff can mean that more observations are included in the tail average.

The overview always displays 95% and 99% Historical VaR. The ES confidence is independently adjustable. The VaR backtest has its own confidence input because it controls a different calculation: the rolling thresholds and expected breach rate used for backtesting.

## What the backtest does

For each date after the selected lookback window is available, the backtest:

1. Looks only at the earlier P&L observations in that window.
2. Calculates the historical VaR loss threshold from those earlier observations.
3. Compares the next day's actual P&L with the negative VaR threshold.
4. Marks a breach when the actual loss is larger than the threshold.

Using only past observations avoids using the result being checked to set its own threshold. If confidence is 99%, the expected breach rate is 1%. With 2,000 backtest observations, that corresponds to about 20 breaches on average, though a finite sample will vary.

### The three statistical diagnostics

| Test | Newbie explanation | Example question |
| --- | --- | --- |
| Kupiec proportion of failures (POF) | Checks whether the number of breaches is consistent with the target breach rate. | At 99% confidence, is 1 breach in 2,000 observations plausible, or is the model breaching far too often? |
| Christoffersen independence | Checks whether breaches arrive independently or cluster together. | Are breaches scattered over time, or do they tend to happen on adjacent observations? |
| Christoffersen conditional coverage | Combines the breach-frequency and independence checks. | Is the model getting both the overall rate and the timing pattern about right? |

The tests report p-values. The dashboard uses 0.05 as a conventional flag: below 0.05 is evidence against that test's null assumption. A result above 0.05 does not prove the model is correct. A high confidence level paired with a short lookback leaves very few observations in the tail, so the estimated threshold can be coarse and the tests may have limited power.

## What the other dashboard areas show

- **Portfolio overview:** active products, gross and net notional, daily P&L, VaR, and ES.
- **Asset attribution:** standalone asset risk, exposure, correlation, and contribution views.
- **Stress testing:** deterministic price shocks such as an energy sell-off or combined market drop. These are user-defined scenarios, not probability forecasts.
- **Data and exports:** aligned input data and downloadable result tables.

## What each technology contributes

- **Python** holds the application logic and data-processing steps.
- **pandas** reads CSVs, organizes dates and assets into tables, aligns time series, and prepares results.
- **NumPy** performs numerical operations such as quantiles and loss calculations.
- **Streamlit** builds the web interface from Python, including sidebar controls, metrics, tables, and downloads.
- **Plotly** creates zoomable, hoverable charts.
- **yfinance** downloads example historical prices from Yahoo Finance when the data pipeline is run.
- **SQL / SQLite** defines relational tables and supports scripts that load and inspect instrument, price, and return records. The dashboard's risk calculations currently load the aligned CSV, not SQLite.
- **pytest** checks core calculations and edge cases, including invalid confidence levels, lookback history, and clustered breach behavior.

## If asked, “Why use SQL if the app reads CSV?”

The project includes a relational data layer to practice storing instruments, prices, and returns with keys and constraints, and it has a loader and verification script. The interactive analysis path currently consumes a prepared CSV because it is simple for this prototype and easy to deploy. I would describe SQL as part of the ingestion and storage work, not claim that the dashboard is currently backed by database queries. A next improvement would be to make the dashboard load from SQLite or a hosted database and add a repeatable refresh process.

## Sensible next improvements

1. Connect the dashboard to the SQLite schema or a hosted database, with a clear source-of-truth path.
2. Add a refresh workflow with data freshness checks and visible last-updated dates.
3. Add risk-method comparisons and stronger validation across multiple portfolios and market regimes.
4. Add deployment monitoring and a small automated build check for the hosted app.
5. Improve charts and smaller-screen layouts based on interview and user feedback.

## Honest limitations to mention

- Historical risk measures describe the chosen historical sample; they do not promise what will happen next.
- Futures proxies are not the same as holding a specific deliverable futures contract. Contract rolls, transaction costs, funding, liquidity, and margin are not modeled.
- Stress scenarios are deterministic examples, not forecasts or probabilities.
- The project is not connected to a broker, live position feed, or live trading system.
