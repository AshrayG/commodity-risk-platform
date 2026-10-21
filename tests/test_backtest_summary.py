
import pandas as pd
import pytest

from src.risk.backtest_summary import (
    summarize_backtest,
    kupiec_pof_test,
    christoffersen_independence_test,
    conditional_coverage_test,
)


def make_results(hits):
    """Create a DataFrame of VaR breach indicators."""
    return pd.DataFrame({"breach": hits})


def test_summary_calculates_breach_rate():
    results = make_results([False, False, True, False, True])

    summary = summarize_backtest(results, confidence=0.95)

    assert summary["observations"] == 5
    assert summary["breaches"] == 2
    assert summary["breach_rate"] == pytest.approx(0.40)
    assert summary["expected_breach_rate"] == pytest.approx(0.05)


def test_kupiec_returns_valid_statistics():
    results = make_results(
        [False] * 95 + [True] * 5
    )

    result = kupiec_pof_test(results, confidence=0.95)

    assert result["test"] == "Kupiec POF"
    assert result["observations"] == 100
    assert result["breaches"] == 5
    assert result["lr_statistic"] >= 0
    assert 0 <= result["p_value"] <= 1



def test_independence_returns_transition_counts():
    hits = [
        False, False, True, False, False,
        True, False, False, True,
    ]
    results = make_results(hits)

    result = christoffersen_independence_test(
        results, confidence=0.95
    )

    # Check that every adjacent pair is counted exactly once.
    assert (
        result["n00"]
        + result["n01"]
        + result["n10"]
        + result["n11"]
    ) == len(hits) - 1

    assert result["n00"] == 3
    assert result["n01"] == 3
    assert result["n10"] == 2
    assert result["n11"] == 0
    assert result["lr_statistic"] >= 0
    assert 0 <= result["p_value"] <= 1




def test_conditional_coverage_combines_statistics():
    results = make_results(
        [False, False, True, False, False,
         True, False, False, True, False]
    )

    result = conditional_coverage_test(
        results, confidence=0.95
    )

    assert result["test"] == "Christoffersen conditional coverage"
    assert result["lr_statistic"] >= 0
    assert 0 <= result["p_value"] <= 1
    assert isinstance(result["reject_at_5_percent"], bool)


def test_summary_rejects_empty_results():
    with pytest.raises(ValueError, match="empty"):
        summarize_backtest(pd.DataFrame({"breach": []}))


def test_summary_rejects_missing_breach_column():
    with pytest.raises(ValueError, match="breach"):
        summarize_backtest(pd.DataFrame({"pnl": [100, -50]}))


def test_summary_rejects_missing_breach_values():
    results = pd.DataFrame({"breach": [False, None, True]})

    with pytest.raises(ValueError, match="missing"):
        summarize_backtest(results)


def test_independence_requires_two_observations():
    results = make_results([False])

    with pytest.raises(ValueError, match="two observations"):
        christoffersen_independence_test(results)
