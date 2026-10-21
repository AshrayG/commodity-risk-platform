
import pandas as pd
import pytest

from src.risk.backtesting import historical_var_backtest
from src.risk.backtest_summary import summarize_backtest


def test_backtest_uses_only_prior_observations():
    pnl = pd.Series(range(-150, 151), dtype=float)

    result = historical_var_backtest(
        pnl,
        window=100,
        confidence=0.95,
    )

    assert len(result) == len(pnl) - 100
    assert "var_loss_usd" in result.columns
    assert "breach" in result.columns


def test_backtest_rejects_insufficient_history():
    pnl = pd.Series(range(30), dtype=float)

    with pytest.raises(ValueError, match="Need more than"):
        historical_var_backtest(pnl, window=30)


def test_backtest_rejects_invalid_confidence():
    pnl = pd.Series(range(100), dtype=float)

    with pytest.raises(ValueError, match="confidence"):
        historical_var_backtest(pnl, window=50, confidence=1.0)


def test_summary_calculates_breach_rate():
    results = pd.DataFrame({
        "breach": [False, False, True, False, True],
    })

    summary = summarize_backtest(results, confidence=0.95)

    assert summary["observations"] == 5
    assert summary["breaches"] == 2
    assert summary["breach_rate"] == pytest.approx(0.4)
    assert summary["expected_breach_rate"] == pytest.approx(0.05)
