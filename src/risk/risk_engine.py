
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RETURNS_FILE = (
    ROOT / "data" / "processed" / "returns" / "aligned_returns.csv"
)

# Illustrative USD notionals, not actual market positions.
POSITIONS = {
    "brent_proxy": 500_000,
    "wti_proxy": 300_000,
    "natural_gas_proxy": 200_000,
    "coffee_proxy": 100_000,
    "bitcoin": 100_000,
    "ethereum": 50_000,
}


def load_returns() -> pd.DataFrame:
    """Load aligned returns for the configured portfolio assets."""
    if not RETURNS_FILE.exists():
        raise FileNotFoundError(
            f"Returns file not found: {RETURNS_FILE}. "
            "Run src.analytics.returns first."
        )

    df = pd.read_csv(RETURNS_FILE, index_col=0, parse_dates=True)
    df = df.apply(pd.to_numeric, errors="coerce").dropna()

    if df.empty:
        raise ValueError("The aligned returns dataset is empty.")

    if df.columns.duplicated().any():
        raise ValueError("Duplicate instrument columns found in returns data.")

    return df.sort_index()


def historical_var_es(
    pnl: pd.Series,
    confidence: float = 0.95,
) -> dict:
    """
    Calculate historical VaR and Expected Shortfall from P&L.

    VaR and ES are positive loss thresholds, floored at zero.
    """
    if not 0 < confidence < 1:
        raise ValueError("Confidence must be between 0 and 1.")

    pnl = pd.Series(pnl).dropna()

    if len(pnl) < 100:
        raise ValueError("At least 100 observations are required.")

    losses = -pnl.to_numpy()
    var = float(np.quantile(losses, confidence))
    tail_losses = losses[losses >= var]
    es = float(tail_losses.mean())

    return {
        "confidence": confidence,
        "observations": len(losses),
        "var_usd": max(0.0, var),
        "expected_shortfall_usd": max(0.0, es),
    }


def build_portfolio_pnl(
    returns: pd.DataFrame,
    positions: dict[str, float],
) -> pd.Series:
    """
    Estimate portfolio P&L from signed USD notionals and returns.

    Positive notional means long exposure; negative means short exposure.
    """
    if not positions:
        raise ValueError("At least one position is required.")

    missing = set(positions) - set(returns.columns)
    if missing:
        raise ValueError(
            f"Missing return columns: {sorted(missing)}. "
            f"Available columns: {list(returns.columns)}"
        )

    notionals = pd.Series(positions, dtype=float)
    selected_returns = returns.loc[:, list(notionals.index)]

    return selected_returns.mul(notionals, axis="columns").sum(axis=1)


def asset_risk_attribution(
    returns: pd.DataFrame,
    positions: dict[str, float],
) -> pd.DataFrame:
    """Summarize standalone asset return and P&L risk statistics."""
    missing = set(positions) - set(returns.columns)
    if missing:
        raise ValueError(f"Missing return columns: {sorted(missing)}")

    rows = []

    for asset, notional in positions.items():
        asset_returns = returns[asset].dropna()
        asset_pnl = asset_returns * notional

        rows.append({
            "instrument": asset,
            "signed_notional_usd": float(notional),
            "gross_notional_usd": abs(float(notional)),
            "observations": len(asset_returns),
            "mean_return": float(asset_returns.mean()),
            "daily_return_volatility": float(asset_returns.std()),
            "daily_pnl_volatility_usd": float(asset_pnl.std()),
            "standalone_var_95_usd": historical_var_es(
                asset_pnl, 0.95
            )["var_usd"],
            "standalone_var_99_usd": historical_var_es(
                asset_pnl, 0.99
            )["var_usd"],
        })

    return pd.DataFrame(rows)


def correlation_matrix(returns: pd.DataFrame) -> pd.DataFrame:
    """Return the historical correlation matrix."""
    return returns.corr()


def run_stress_scenario(
    positions: dict[str, float],
    shocks: dict[str, float],
) -> dict:
    """
    Estimate one-interval P&L under user-defined percentage price shocks.

    Example: -0.10 means a 10% price decline.
    This is a deterministic scenario, not a forecast.
    """
    missing = set(positions) - set(shocks)
    if missing:
        raise ValueError(f"Missing shocks for positions: {sorted(missing)}")

    pnl_by_instrument = {
        asset: float(notional * shocks[asset])
        for asset, notional in positions.items()
    }

    return {
        "pnl_by_instrument_usd": pnl_by_instrument,
        "total_pnl_usd": sum(pnl_by_instrument.values()),
    }


def run_standard_stress_scenarios(
    positions: dict[str, float],
) -> dict[str, dict]:
    """Run illustrative crypto, energy, and combined sell-off scenarios."""
    scenarios = {
        "crypto_crash": {
            "brent_proxy": 0.0,
            "wti_proxy": 0.0,
            "natural_gas_proxy": 0.0,
            "coffee_proxy": 0.0,
            "bitcoin": -0.30,
            "ethereum": -0.40,
        },
        "energy_shock": {
            "brent_proxy": -0.15,
            "wti_proxy": -0.15,
            "natural_gas_proxy": -0.25,
            "coffee_proxy": 0.0,
            "bitcoin": 0.0,
            "ethereum": 0.0,
        },
        "combined_selloff": {
            "brent_proxy": -0.15,
            "wti_proxy": -0.15,
            "natural_gas_proxy": -0.25,
            "coffee_proxy": -0.10,
            "bitcoin": -0.30,
            "ethereum": -0.40,
        },
    }

    return {
        name: run_stress_scenario(positions, shocks)
        for name, shocks in scenarios.items()
    }



def main() -> None:
    returns = load_returns()

    missing = set(POSITIONS) - set(returns.columns)
    if missing:
        raise ValueError(f"Missing configured assets: {sorted(missing)}")

    # Create output directory.
    reports_dir = ROOT / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    # Calculate portfolio P&L and risk summary.
    pnl = build_portfolio_pnl(returns, POSITIONS)

    summary_rows = []
    for confidence in (0.95, 0.99):
        result = historical_var_es(pnl, confidence)
        summary_rows.append({
            "metric": "historical_var_es",
            **result,
        })

    portfolio_summary = pd.DataFrame(summary_rows)
    portfolio_summary["asset_count"] = len(POSITIONS)
    portfolio_summary["gross_notional_usd"] = sum(
        abs(value) for value in POSITIONS.values()
    )
    portfolio_summary["pnl_observations"] = len(pnl)
    portfolio_summary["daily_pnl_volatility_usd"] = pnl.std()

    # Asset-level risk attribution.
    attribution = asset_risk_attribution(returns, POSITIONS)

    # Historical return correlations.
    correlations = correlation_matrix(
        returns.loc[:, list(POSITIONS)]
    )

    # Stress scenario results in one flat table.
    stress_rows = []
    stress_results = run_standard_stress_scenarios(POSITIONS)

    for scenario_name, result in stress_results.items():
        for asset, pnl_value in result["pnl_by_instrument_usd"].items():
            stress_rows.append({
                "scenario": scenario_name,
                "instrument": asset,
                "scenario_pnl_usd": pnl_value,
                "total_scenario_pnl_usd": result["total_pnl_usd"],
            })

    stress_report = pd.DataFrame(stress_rows)

    # Export results.
    outputs = {
        "portfolio_risk_summary.csv": portfolio_summary,
        "asset_risk_attribution.csv": attribution,
        "correlation_matrix.csv": correlations,
        "stress_scenarios.csv": stress_report,
    }

    for filename, dataframe in outputs.items():
        output_path = reports_dir / filename
        dataframe.to_csv(output_path, index=True)
        print(f"Saved: {output_path}")

    # Print a concise run summary.
    print("\nPORTFOLIO RISK SUMMARY")
    print(f"Assets: {len(POSITIONS)}")
    print(
        "Gross notional: "
        f"${sum(abs(v) for v in POSITIONS.values()):,.2f}"
    )
    print(f"Observations: {len(pnl)}")
    print(f"Daily P&L volatility: ${pnl.std():,.2f}")

    print("\nHISTORICAL VaR AND EXPECTED SHORTFALL")
    print(portfolio_summary.to_string(index=False))

    print("\nASSET RISK ATTRIBUTION")
    print(attribution.to_string(index=False))

    print("\nCORRELATION MATRIX")
    print(correlations.round(3))

    print("\nSTRESS SCENARIOS")
    print(
        stress_report.drop_duplicates("scenario")[
            ["scenario", "total_scenario_pnl_usd"]
        ].to_string(index=False)
    )



if __name__ == "__main__":
    main()
