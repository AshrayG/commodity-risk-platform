
import math

import pandas as pd


def summarize_backtest(
    results: pd.DataFrame,
    confidence: float = 0.99,
) -> dict:
    """Summarize historical VaR backtesting results."""

    if results.empty:
        raise ValueError("Backtest results cannot be empty.")

    if not 0 < confidence < 1:
        raise ValueError("Confidence must be between 0 and 1.")

    if "breach" not in results.columns:
        raise ValueError("Results must contain a 'breach' column.")

    breaches_series = results["breach"]

    if breaches_series.isna().any():
        raise ValueError("Breach column cannot contain missing values.")

    if not breaches_series.isin([True, False, 0, 1]).all():
        raise ValueError("Breach values must be boolean or binary.")

    breaches = int(breaches_series.sum())
    observations = len(results)

    return {
        "confidence": confidence,
        "observations": observations,
        "breaches": breaches,
        "breach_rate": breaches / observations,
        "expected_breach_rate": 1 - confidence,
    }


def _likelihood_ratio(
    observed: int,
    total: int,
    probability: float,
) -> float:
    """Calculate a binomial likelihood-ratio statistic."""

    if total == 0:
        return 0.0

    observed_rate = observed / total

    log_likelihood_null = (
        observed * math.log(probability)
        if observed > 0 else 0.0
    ) + (
        (total - observed) * math.log(1 - probability)
        if observed < total else 0.0
    )

    log_likelihood_alt = (
        observed * math.log(observed_rate)
        if observed > 0 else 0.0
    ) + (
        (total - observed) * math.log(1 - observed_rate)
        if observed < total else 0.0
    )

    return max(
        0.0,
        2 * (log_likelihood_alt - log_likelihood_null),
    )


def _chi_square_1df_pvalue(statistic: float) -> float:
    """Calculate the upper-tail p-value for chi-square with 1 df."""

    return math.erfc(math.sqrt(max(0.0, statistic) / 2))


def kupiec_pof_test(
    results: pd.DataFrame,
    confidence: float = 0.99,
) -> dict:
    """Test whether the observed VaR breach rate matches expectations."""

    summary = summarize_backtest(results, confidence)

    n = summary["observations"]
    x = summary["breaches"]
    expected_rate = 1 - confidence

    statistic = _likelihood_ratio(x, n, expected_rate)
    p_value = _chi_square_1df_pvalue(statistic)

    return {
        "test": "Kupiec POF",
        "observations": n,
        "breaches": x,
        "expected_breach_rate": expected_rate,
        "observed_breach_rate": x / n,
        "lr_statistic": statistic,
        "p_value": p_value,
        "reject_at_5_percent": p_value < 0.05,
    }


def christoffersen_independence_test(
    results: pd.DataFrame,
    confidence: float = 0.99,
) -> dict:
    """Test whether VaR breaches are independent over time."""

    summarize_backtest(results, confidence)
    hits = results["breach"].astype(int).tolist()

    n00 = n01 = n10 = n11 = 0

    for previous, current in zip(hits, hits[1:]):
        if previous == 0 and current == 0:
            n00 += 1
        elif previous == 0 and current == 1:
            n01 += 1
        elif previous == 1 and current == 0:
            n10 += 1
        else:
            n11 += 1

    transitions = n00 + n01 + n10 + n11

    if transitions == 0:
        raise ValueError("At least two observations are required.")

    total_zeros = n00 + n10
    total_ones = n01 + n11

    if total_zeros == 0 or total_ones == 0:
        raise ValueError(
            "Independence test requires both breach and non-breach observations."
        )

    def log_bernoulli(successes: int, total: int) -> float:
        if total == 0:
            return 0.0

        probability = successes / total
        value = 0.0

        if successes > 0:
            value += successes * math.log(probability)

        if successes < total:
            value += (total - successes) * math.log(1 - probability)

        return value

    pooled_successes = n01 + n11

    log_likelihood_independent = log_bernoulli(
        pooled_successes,
        transitions,
    )

    log_likelihood_markov = (
        log_bernoulli(n01, n00 + n01)
        + log_bernoulli(n11, n10 + n11)
    )

    statistic = max(
        0.0,
        2 * (log_likelihood_markov - log_likelihood_independent),
    )

    p_value = _chi_square_1df_pvalue(statistic)

    return {
        "test": "Christoffersen independence",
        "n00": n00,
        "n01": n01,
        "n10": n10,
        "n11": n11,
        "lr_statistic": statistic,
        "p_value": p_value,
        "reject_at_5_percent": p_value < 0.05,
    }


def conditional_coverage_test(
    results: pd.DataFrame,
    confidence: float = 0.99,
) -> dict:
    """Jointly test breach frequency and independence."""

    kupiec = kupiec_pof_test(results, confidence)

    independence = christoffersen_independence_test(
        results,
        confidence,
    )

    statistic = (
        kupiec["lr_statistic"]
        + independence["lr_statistic"]
    )

    # The joint statistic asymptotically follows chi-square with 2 df.
    p_value = math.exp(-statistic / 2)

    return {
        "test": "Christoffersen conditional coverage",
        "lr_statistic": statistic,
        "p_value": p_value,
        "reject_at_5_percent": p_value < 0.05,
    }
