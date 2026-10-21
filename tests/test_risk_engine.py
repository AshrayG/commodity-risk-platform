
import pandas as pd
import pytest

from src.risk.risk_engine import (
    build_portfolio_pnl,
    correlation_matrix,
    run_stress_scenario,
)


def test_portfolio_pnl_uses_instrument_names():
    returns = pd.DataFrame({
        "brent_proxy": [0.01, -0.02],
        "wti_proxy": [0.02, -0.01],
    })

    positions = {
        "brent_proxy": 100_000,
        "wti_proxy": 50_000,
    }

    pnl = build_portfolio_pnl(returns, positions)

    assert pnl.iloc[0] == pytest.approx(2_000)
    assert pnl.iloc[1] == pytest.approx(-2_500)


def test_missing_instrument_raises_error():
    returns = pd.DataFrame({"brent_proxy": [0.01]})
    positions = {"wti_proxy": 100_000}

    with pytest.raises(ValueError, match="Missing return columns"):
        build_portfolio_pnl(returns, positions)


def test_correlation_matrix_is_symmetric():
    returns = pd.DataFrame({
        "brent_proxy": [0.01, 0.02, -0.01, 0.03],
        "wti_proxy": [0.02, 0.01, -0.02, 0.04],
    })

    corr = correlation_matrix(returns)

    assert corr.shape == (2, 2)
    assert corr.loc["brent_proxy", "brent_proxy"] == pytest.approx(1.0)
    assert corr.loc["brent_proxy", "wti_proxy"] == pytest.approx(
        corr.loc["wti_proxy", "brent_proxy"]
    )


def test_stress_scenario_total():
    positions = {
        "brent_proxy": 500_000,
        "wti_proxy": 300_000,
        "natural_gas_proxy": 200_000,
        "coffee_proxy": 100_000,
    }

    shocks = {
        "brent_proxy": -0.10,
        "wti_proxy": -0.10,
        "natural_gas_proxy": -0.20,
        "coffee_proxy": -0.15,
    }

    result = run_stress_scenario(positions, shocks)

    assert result["total_pnl_usd"] == pytest.approx(-135_000)
