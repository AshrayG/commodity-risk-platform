
import pandas as pd

from src.risk.backtest_summary import (
    kupiec_pof_test,
    christoffersen_independence_test,
    conditional_coverage_test,
)

def historical_var_backtest(
    portfolio_pnl: pd.Series,
    window: int = 250,
    confidence: float = 0.99,
) -> pd.DataFrame:
    """Run a rolling historical VaR backtest on daily USD P&L."""

    if window < 30:
        raise ValueError("window must be at least 30 observations.")

    if not 0 < confidence < 1:
        raise ValueError("confidence must be between 0 and 1.")

    pnl = portfolio_pnl.dropna().sort_index()

    if len(pnl) <= window:
        raise ValueError(
            f"Need more than {window} valid observations; got {len(pnl)}."
        )

    records = []

    for i in range(window, len(pnl)):
        history = pnl.iloc[i - window:i]
        actual_pnl = float(pnl.iloc[i])

        # Positive number representing the estimated loss threshold.
        var_loss = max(
            0.0,
            -float(history.quantile(1 - confidence)),
        )

        records.append({
            "date": pnl.index[i],
            "actual_pnl_usd": actual_pnl,
            "var_loss_usd": var_loss,
            "breach": actual_pnl < -var_loss,
        })

    return pd.DataFrame(records).set_index("date")


