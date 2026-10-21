
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



import pytest


def test_kupiec_pof_returns_valid_statistics():
    results = pd.DataFrame({
        "breach": [False] * 990 + [True] * 10
    })

    output = kupiec_pof_test(results, confidence=0.99)

    assert output["test"] == "Kupiec POF"
    assert output["observations"] == 1000
    assert output["breaches"] == 10
    assert 0 <= output["p_value"] <= 1


def test_independence_test_returns_valid_statistics():
    results = pd.DataFrame({
        "breach": [
            False, False, True, False, False,
            True, False, False, True, False,
        ]
    })

    output = christoffersen_independence_test(
        results, confidence=0.99
    )

    assert output["test"] == "Christoffersen independence"
    assert output["n00"] + output["n01"] + \
        output["n10"] + output["n11"] == 9
    assert 0 <= output["p_value"] <= 1


def test_conditional_coverage_returns_valid_statistics():
    results = pd.DataFrame({
        "breach": [
            False, False, True, False, False,
            True, False, False, True, False,
        ]
    })

    output = conditional_coverage_test(
        results, confidence=0.99
    )

    assert output["test"] == "Christoffersen conditional coverage"
    assert output["lr_statistic"] >= 0
    assert 0 <= output["p_value"] <= 1


def test_kupiec_rejects_invalid_confidence():
    results = pd.DataFrame({"breach": [False, True]})

    with pytest.raises(ValueError):
        kupiec_pof_test(results, confidence=1.0)
