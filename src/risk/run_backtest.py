import argparse
from pathlib import Path
from typing import Optional, Sequence

import pandas as pd

from src.risk.risk_engine import POSITIONS, load_returns, build_portfolio_pnl
from src.risk.backtesting import historical_var_backtest
from src.risk.backtest_summary import (
    summarize_backtest,
    kupiec_pof_test,
    christoffersen_independence_test,
    conditional_coverage_test,
)


# --------------------------------------------------
# Configuration
# --------------------------------------------------

LOOKBACK_WINDOW = 250
CONFIDENCE_LEVEL = 0.99

ROOT = Path(__file__).resolve().parents[2]
REPORTS_DIR = ROOT / "reports"
RESULTS_FILE = REPORTS_DIR / "var_backtest_results.csv"
DIAGNOSTICS_FILE = REPORTS_DIR / "var_backtest_diagnostics.csv"



def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run a rolling historical VaR backtest for the sample portfolio."
        )
    )
    parser.add_argument(
        "--window",
        type=int,
        default=LOOKBACK_WINDOW,
        help=(
            "Rolling history length in observations "
            f"(default: {LOOKBACK_WINDOW})."
        ),
    )
    parser.add_argument(
        "--confidence",
        type=float,
        choices=(0.95, 0.99),
        default=CONFIDENCE_LEVEL,
        help="VaR confidence level: 0.95 or 0.99 (default: 0.99).",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> None:
    args = parse_args(argv)
    # Load the aligned returns for all configured assets.
    returns = load_returns()

    print("\nASSETS LOADED")
    print(returns.columns.tolist())

    # Confirm every configured position has return data.
    missing = set(POSITIONS) - set(returns.columns)
    if missing:
        raise ValueError(
            f"Missing assets in returns data: {sorted(missing)}"
        )

    # Build portfolio P&L from all six positions.
    portfolio_pnl = build_portfolio_pnl(returns, POSITIONS)

    print(f"\nAssets in portfolio: {len(POSITIONS)}")
    print(f"Gross notional: ${sum(abs(v) for v in POSITIONS.values()):,.2f}")
    print(f"P&L observations: {len(portfolio_pnl)}")

    results = historical_var_backtest(
        portfolio_pnl,
        window=args.window,
        confidence=args.confidence,
    )

    summary = summarize_backtest(
        results,
        confidence=args.confidence,
    )

    kupiec = kupiec_pof_test(
        results,
        confidence=args.confidence,
    )

    christoffersen = christoffersen_independence_test(
        results,
        confidence=args.confidence,
    )

    conditional_coverage = conditional_coverage_test(
        results,
        confidence=args.confidence,
    )

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    results.to_csv(RESULTS_FILE, index=True)

    diagnostics = pd.DataFrame([
        {"diagnostic": "backtest_summary", **summary},
        {"diagnostic": "kupiec_pof", **kupiec},
        {"diagnostic": "christoffersen_independence", **christoffersen},
        {"diagnostic": "christoffersen_conditional_coverage", **conditional_coverage},
    ])

    diagnostics.to_csv(DIAGNOSTICS_FILE, index=False)

    print("\nBACKTEST SUMMARY")
    print(summary)

    print("\nKUPIEC POF TEST")
    print(kupiec)

    print("\nCHRISTOFFERSEN INDEPENDENCE TEST")
    print(christoffersen)

    print("\nCONDITIONAL COVERAGE TEST")
    print(conditional_coverage)

    print(f"\nDetailed results exported to {RESULTS_FILE}")
    print(f"Diagnostic report exported to {DIAGNOSTICS_FILE}")



if __name__ == "__main__":
    main()
