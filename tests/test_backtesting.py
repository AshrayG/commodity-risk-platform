
import pandas as pd
import pytest

from src.risk.backtesting import historical_var_backtest
from src.risk.backtest_summary import (
    summarize_backtest,
    kupiec_pof_test,
    christoffersen_independence_test,
    conditional_coverage_test,
)


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


def test_backtest_uses_observed_order_statistic_for_extreme_tail():
    pnl = pd.Series(range(-150, 151), dtype=float)

    result = historical_var_backtest(
        pnl,
        window=100,
        confidence=0.99,
    )

    # A 1% quantile of 100 observations should use the worst observed loss.
    # Linear interpolation almost reaches the second-worst loss and inflates
    # the effective out-of-sample breach probability toward 2%.
    assert result.iloc[0]["var_loss_usd"] == pytest.approx(150.0)


def test_higher_confidence_uses_wider_var_and_changes_breaches():
    pnl = pd.Series(([1.0] * 97 + [-200.0] * 3) * 3, dtype=float)

    results_95 = historical_var_backtest(pnl, window=100, confidence=0.95)
    results_99 = historical_var_backtest(pnl, window=100, confidence=0.99)

    assert (results_99["var_loss_usd"] >= results_95["var_loss_usd"]).all()
    assert (results_99["var_loss_usd"] > results_95["var_loss_usd"]).any()
    assert results_95["breach"].sum() > results_99["breach"].sum()


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


def test_summary_rejects_missing_breach_values():
    results = pd.DataFrame({"breach": [False, None, True]})

    with pytest.raises(ValueError, match="missing"):
        summarize_backtest(results)


def test_summary_rejects_invalid_confidence():
    results = pd.DataFrame({"breach": [False, True]})

    with pytest.raises(ValueError, match="Confidence"):
        summarize_backtest(results, confidence=1.0)


def test_kupiec_returns_valid_p_value():
    results = pd.DataFrame({
        "breach": [False] * 95 + [True] * 5,
    })

    result = kupiec_pof_test(results, confidence=0.95)

    assert result["test"] == "Kupiec POF"
    assert result["lr_statistic"] >= 0
    assert 0 <= result["p_value"] <= 1
    assert result["observations"] == 100
    assert result["breaches"] == 5


def test_kupiec_detects_excessive_breaches():
    results = pd.DataFrame({
        "breach": [True] * 50 + [False] * 50,
    })

    result = kupiec_pof_test(results, confidence=0.99)

    assert result["p_value"] < 0.05
    assert result["reject_at_5_percent"] is True


def test_independence_test_detects_clustered_breaches():
    clustered = pd.DataFrame({
        "breach": [False] * 50 + [True] * 10 + [False] * 40,
    })

    alternating = pd.DataFrame({
        "breach": [False, True] * 50,
    })

    clustered_result = christoffersen_independence_test(clustered)
    alternating_result = christoffersen_independence_test(alternating)

    assert clustered_result["p_value"] < 0.05
    assert alternating_result["p_value"] < 0.05


def test_independence_test_rejects_single_observation():
    results = pd.DataFrame({"breach": [False]})

    with pytest.raises(ValueError, match="two observations"):
        christoffersen_independence_test(results)


def test_conditional_coverage_equals_component_statistics():
    results = pd.DataFrame({
        "breach": [False] * 45 + [True] * 5 + [False] * 45 + [True] * 5,
    })

    kupiec = kupiec_pof_test(results, confidence=0.95)
    independence = christoffersen_independence_test(
        results,
        confidence=0.95,
    )
    conditional = conditional_coverage_test(
        results,
        confidence=0.95,
    )

    expected_statistic = (
        kupiec["lr_statistic"] + independence["lr_statistic"]
    )

    assert conditional["lr_statistic"] == pytest.approx(expected_statistic)
    assert 0 <= conditional["p_value"] <= 1
