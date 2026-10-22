
from pathlib import Path
import sys

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Make imports work when Streamlit launches this file from the project root.
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.risk.risk_engine import (
    POSITIONS as DEFAULT_POSITIONS,
    load_returns,
    build_portfolio_pnl,
    historical_var_es,
    asset_risk_attribution,
    correlation_matrix,
    run_standard_stress_scenarios,
)
from src.risk.backtesting import historical_var_backtest
from src.risk.backtest_summary import (
    summarize_backtest,
    kupiec_pof_test,
    christoffersen_independence_test,
    conditional_coverage_test,
)


def format_confidence(confidence: float) -> str:
    """Format confidence as a percentage without an unnecessary .0."""
    return f"{confidence * 100:g}%"


st.set_page_config(
    page_title="Commodity Risk Platform",
    page_icon="📊",
    layout="wide",
)

st.title("Commodity Risk Platform")
st.caption(
    "Portfolio risk | Historical VaR | Backtesting | Risk attribution | Stress testing"
)



# -----------------------------
# Load aligned historical data
# -----------------------------
try:
    returns = load_returns()
except Exception as exc:
    st.error(f"Could not load aligned returns: {exc}")
    st.info(
        "Check that data/processed/returns/aligned_returns.csv exists. "
        "Run `python -m src.analytics.returns` from the project root."
    )
    st.stop()

if returns.empty:
    st.error("The aligned returns dataset is empty.")
    st.stop()

st.sidebar.header("Portfolio configuration")
st.sidebar.caption("Change signed USD notionals. Negative values represent short positions.")

positions = {}
for asset, default_value in DEFAULT_POSITIONS.items():
    positions[asset] = st.sidebar.number_input(
        asset.replace("_", " ").title(),
        value=float(default_value),
        step=25000.0,
        format="%.0f",
        key=f"position_{asset}",
    )

confidence_percent = st.sidebar.number_input(
    "Expected Shortfall confidence (%)",
    min_value=90.0,
    max_value=99.9,
    value=99.0,
    step=0.1,
    format="%.1f",
    key="expected_shortfall_confidence_percent",
    help=(
        "Sets the loss-tail percentile for the Expected Shortfall card: "
        "95% averages the worst 5% of losses, while 99% averages the worst 1%. "
        "Very high settings use few tail observations. The overview always "
        "shows both 95% and 99% Historical VaR."
    ),
)
confidence = confidence_percent / 100.0

lookback = st.sidebar.number_input(
    "VaR backtest lookback (observations)",
    min_value=30,
    max_value=1000,
    value=250,
    step=10,
)

backtest_confidence_percent = st.sidebar.number_input(
    "VaR backtest confidence (%)",
    min_value=90.0,
    max_value=99.9,
    value=99.0,
    step=0.1,
    format="%.1f",
    key="var_backtest_confidence_percent",
    help=(
        "Sets the confidence for rolling VaR thresholds, breach counts, "
        "and statistical backtesting tests. The expected breach rate is "
        "100% minus this value. Very high settings leave few tail observations "
        "in each rolling lookback window."
    ),
)
backtest_confidence = backtest_confidence_percent / 100.0

missing = set(positions) - set(returns.columns)
if missing:
    st.error(f"Missing return columns: {sorted(missing)}")
    st.stop()
if not any(value != 0 for value in positions.values()):
    st.info(
        "No active positions. Enter a non-zero notional for at least "
        "one product to calculate portfolio risk and backtesting."
    )
    st.stop()

# -----------------------------
# Calculate portfolio metrics
# -----------------------------
portfolio_pnl = build_portfolio_pnl(returns, positions)
portfolio_risk = historical_var_es(portfolio_pnl, confidence)
var_95 = historical_var_es(portfolio_pnl, 0.95)
var_99 = historical_var_es(portfolio_pnl, 0.99)

gross_notional = sum(abs(value) for value in positions.values())
net_notional = sum(positions.values())

# Run a fresh backtest using the selected positions.
backtest = historical_var_backtest(
    portfolio_pnl,
    window=int(lookback),
    confidence=backtest_confidence,
)

backtest_df = backtest.copy()
if "date" not in backtest_df.columns:
    backtest_df["date"] = backtest_df.index

backtest_df["date"] = pd.to_datetime(backtest_df["date"])
backtest_df = backtest_df.sort_index()
backtest_df["var_threshold_pnl_usd"] = -backtest_df["var_loss_usd"]

summary = summarize_backtest(
    backtest,
    confidence=backtest_confidence,
)
kupiec = kupiec_pof_test(
    backtest,
    confidence=backtest_confidence,
)
christoffersen = christoffersen_independence_test(
    backtest,
    confidence=backtest_confidence,
)
conditional_coverage = conditional_coverage_test(
    backtest,
    confidence=backtest_confidence,
)

# -----------------------------
# Tabs
# -----------------------------
overview_tab, backtest_tab, attribution_tab, stress_tab, data_tab = st.tabs(
    [
        "Portfolio overview",
        "VaR backtesting",
        "Asset attribution",
        "Stress testing",
        "Data & exports",
    ]
)

# =========================================================
# 1. PORTFOLIO OVERVIEW
# =========================================================
with overview_tab:
    st.subheader("Portfolio risk snapshot")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric(
    "Active products",
    sum(value != 0 for value in positions.values()),
)

    c2.metric("Gross notional", f"${gross_notional:,.0f}")
    c3.metric("Net notional", f"${net_notional:,.0f}")
    c4.metric("Daily P&L volatility", f"${portfolio_pnl.std():,.0f}")

    c5, c6, c7 = st.columns(3)
    c5.metric("95% Historical VaR", f"${var_95['var_usd']:,.0f}")
    c6.metric("99% Historical VaR", f"${var_99['var_usd']:,.0f}")
    c7.metric(
        f"{format_confidence(confidence)} Expected Shortfall",
        f"${portfolio_risk['expected_shortfall_usd']:,.0f}",
    )

    st.caption(
        "VaR and Expected Shortfall are positive loss estimates calculated from "
        "historical portfolio P&L. They are not maximum-loss guarantees."
    )

    pnl_frame = portfolio_pnl.rename("daily_pnl_usd").reset_index()
    pnl_frame.columns = ["date", "daily_pnl_usd"]
    pnl_frame["date"] = pd.to_datetime(pnl_frame["date"])
    pnl_frame = pnl_frame.sort_values("date")
    pnl_frame["cumulative_pnl_usd"] = pnl_frame["daily_pnl_usd"].cumsum()

    st.subheader("Historical daily portfolio P&L")
    fig_pnl = px.line(
        pnl_frame,
        x="date",
        y="daily_pnl_usd",
        title="Daily P&L (USD)",
        labels={"date": "Date", "daily_pnl_usd": "Daily P&L (USD)"},
    )
    fig_pnl.add_hline(y=0, line_dash="dash")
    st.plotly_chart(fig_pnl, width="stretch")

    st.subheader("Cumulative hypothetical P&L")
    fig_cumulative = px.line(
        pnl_frame,
        x="date",
        y="cumulative_pnl_usd",
        title="Cumulative P&L from the beginning of the sample",
        labels={
            "date": "Date",
            "cumulative_pnl_usd": "Cumulative P&L (USD)",
        },
    )
    fig_cumulative.add_hline(y=0, line_dash="dash")
    st.plotly_chart(fig_cumulative, width="stretch")

    st.caption(
        "Cumulative P&L sums estimated daily P&L using constant notionals; "
        "it is not a portfolio return series with rebalancing or financing."
    )

# =========================================================
# 2. VAR BACKTESTING
# =========================================================
with backtest_tab:
    st.subheader("Historical VaR backtest")
    st.caption(
        f"Confidence: {format_confidence(backtest_confidence)} | "
        f"Rolling lookback: {int(lookback)} observations | "
        "VaR uses prior observations only."
    )

    b1, b2, b3, b4 = st.columns(4)
    b1.metric("Backtest observations", f"{summary['observations']:,}")
    b2.metric("VaR breaches", f"{summary['breaches']:,}")
    b3.metric("Observed breach rate", f"{summary['breach_rate']:.2%}")
    b4.metric("Expected breach rate", f"{summary['expected_breach_rate']:.2%}")

    # P&L is plotted against a negative VaR threshold.
    fig_backtest = go.Figure()
    fig_backtest.add_trace(
        go.Scatter(
            x=backtest_df["date"],
            y=backtest_df["actual_pnl_usd"],
            mode="lines",
            name="Actual daily P&L",
        )
    )
    fig_backtest.add_trace(
        go.Scatter(
            x=backtest_df["date"],
            y=backtest_df["var_threshold_pnl_usd"],
            mode="lines",
            name=f"{format_confidence(backtest_confidence)} VaR loss threshold",
            line={"dash": "dash"},
        )
    )

    breaches = backtest_df[backtest_df["breach"].astype(bool)]
    fig_backtest.add_trace(
        go.Scatter(
            x=breaches["date"],
            y=breaches["actual_pnl_usd"],
            mode="markers",
            name="VaR breach",
            marker={"size": 9, "symbol": "x"},
        )
    )
    fig_backtest.update_layout(
        title="Actual P&L versus the rolling VaR threshold",
        xaxis_title="Date",
        yaxis_title="P&L (USD)",
        hovermode="x unified",
    )
    st.plotly_chart(fig_backtest, width="stretch")

    st.subheader("Statistical validation tests")
    diagnostic_rows = [
        {"Diagnostic": "Kupiec proportion of failures", **kupiec},
        {
            "Diagnostic": "Christoffersen independence",
            **christoffersen,
        },
        {
            "Diagnostic": "Christoffersen conditional coverage",
            **conditional_coverage,
        },
    ]
    diagnostics_df = pd.DataFrame(diagnostic_rows)
    st.dataframe(diagnostics_df, width="stretch", hide_index=True)

    if (
        christoffersen.get("reject_at_5_percent", False)
        or conditional_coverage.get("reject_at_5_percent", False)
    ):
        st.warning(
            "At least one backtesting test rejects its null hypothesis at the 5% "
            "level. Investigate breach clustering and model calibration before "
            "treating the VaR estimates as validated."
        )
    elif kupiec.get("reject_at_5_percent", False):
        st.warning(
            "The Kupiec test rejects the expected breach frequency at the 5% level."
        )
    else:
        st.info(
            "The displayed tests did not reject at the 5% level. "
            "This alone does not establish that the model is adequate."
        )

    st.subheader("Breach details")
    breach_columns = [
        "date",
        "actual_pnl_usd",
        "var_loss_usd",
        "breach",
    ]
    breach_table = backtest_df.loc[
        backtest_df["breach"].astype(bool), breach_columns
    ].copy()
    breach_table["excess_loss_usd"] = (
        -breach_table["actual_pnl_usd"] - breach_table["var_loss_usd"]
    )
    st.dataframe(breach_table, width="stretch", hide_index=True)

    st.download_button(
        "Download backtest results CSV",
        data=backtest_df.to_csv(index=False).encode("utf-8"),
        file_name="dashboard_var_backtest_results.csv",
        mime="text/csv",
    )

# =========================================================
# 3. ASSET RISK ATTRIBUTION
# =========================================================
with attribution_tab:
    st.subheader("Standalone asset risk")

    attribution = asset_risk_attribution(returns, positions)
    st.dataframe(
        attribution.sort_values("gross_notional_usd", ascending=False),
        width="stretch",
        hide_index=True,
    )

    fig_exposure = px.bar(
        attribution,
        x="instrument",
        y="gross_notional_usd",
        title="Gross notional by instrument",
        labels={
            "instrument": "Instrument",
            "gross_notional_usd": "Gross notional (USD)",
        },
    )
    st.plotly_chart(fig_exposure, width="stretch")

    fig_var = px.bar(
        attribution,
        x="instrument",
        y="standalone_var_99_usd",
        title="Standalone 99% Historical VaR by instrument",
        labels={
            "instrument": "Instrument",
            "standalone_var_99_usd": "Standalone VaR (USD)",
        },
    )
    st.plotly_chart(fig_var, width="stretch")

    st.subheader("Historical return correlations")
    correlations = correlation_matrix(returns.loc[:, list(positions)])
    fig_corr = px.imshow(
        correlations,
        text_auto=".2f",
        aspect="auto",
        zmin=-1,
        zmax=1,
        color_continuous_scale="RdBu",
        title="Correlation of aligned daily returns",
    )
    st.plotly_chart(fig_corr, width="stretch")

    st.download_button(
        "Download asset attribution CSV",
        data=attribution.to_csv(index=False).encode("utf-8"),
        file_name="dashboard_asset_risk_attribution.csv",
        mime="text/csv",
    )

# =========================================================
# 4. STRESS TESTING
# =========================================================
with stress_tab:
    st.subheader("Standard hypothetical stress scenarios")
    scenarios = run_standard_stress_scenarios(positions)

    scenario_rows = []
    detail_rows = []

    for scenario_name, result in scenarios.items():
        total_pnl = result.get(
            "total_pnl_usd",
            result.get("total_scenario_pnl_usd", 0.0),
        )
        scenario_rows.append(
            {
                "scenario": scenario_name,
                "total_scenario_pnl_usd": total_pnl,
            }
        )

        for asset, pnl_value in result["pnl_by_instrument_usd"].items():
            detail_rows.append(
                {
                    "scenario": scenario_name,
                    "instrument": asset,
                    "scenario_pnl_usd": pnl_value,
                }
            )

    scenario_df = pd.DataFrame(scenario_rows)
    detail_df = pd.DataFrame(detail_rows)

    st.dataframe(scenario_df, width="stretch", hide_index=True)

    fig_stress = px.bar(
        scenario_df,
        x="scenario",
        y="total_scenario_pnl_usd",
        title="Total scenario P&L (USD)",
        labels={
            "scenario": "Scenario",
            "total_scenario_pnl_usd": "Scenario P&L (USD)",
        },
    )
    fig_stress.add_hline(y=0, line_dash="dash")
    st.plotly_chart(fig_stress, width="stretch")

    st.subheader("Instrument-level stress impact")
    fig_detail = px.bar(
        detail_df,
        x="instrument",
        y="scenario_pnl_usd",
        color="scenario",
        barmode="group",
        title="Scenario P&L by instrument",
        labels={
            "instrument": "Instrument",
            "scenario_pnl_usd": "Scenario P&L (USD)",
            "scenario": "Scenario",
        },
    )
    fig_detail.add_hline(y=0, line_dash="dash")
    st.plotly_chart(fig_detail, width="stretch")

    st.dataframe(detail_df, width="stretch", hide_index=True)

    st.download_button(
        "Download stress scenario CSV",
        data=detail_df.to_csv(index=False).encode("utf-8"),
        file_name="dashboard_stress_scenarios.csv",
        mime="text/csv",
    )

    st.caption(
        "Scenario shocks are deterministic assumptions defined in the risk engine. "
        "They are not forecasts or estimates of the worst possible loss."
    )

# =========================================================
# 5. DATA AND EXPORTS
# =========================================================
with data_tab:
    st.subheader("Data quality and coverage")

    d1, d2, d3 = st.columns(3)
    d1.metric("Aligned observations", f"{len(returns):,}")
    d2.metric("Instruments", f"{len(returns.columns)}")
    d3.metric("Missing return cells", f"{int(returns.isna().sum().sum()):,}")

    st.write(
        "**Date range:**",
        f"{returns.index.min().date()} to {returns.index.max().date()}",
    )
    st.write("**Loaded instruments:**", ", ".join(returns.columns))

    st.dataframe(
        returns.tail(20).reset_index(),
        width="stretch",
        hide_index=True,
    )

    st.download_button(
        "Download aligned returns CSV",
        data=returns.to_csv(index=True).encode("utf-8"),
        file_name="dashboard_aligned_returns.csv",
        mime="text/csv",
    )

    st.info(
        "Crypto trades on weekends while most commodity markets do not. "
        "This dashboard uses the existing aligned returns dataset, so weekend "
        "crypto price moves may not be fully represented. A calendar-aware "
        "portfolio alignment is a future improvement."
    )

st.divider()
st.caption(
    "Commodity Risk Platform | Historical estimates depend on the data, "
    "positions, lookback window, and assumptions selected."
)
