from src.risk.run_backtest import parse_args


def test_backtest_cli_defaults_match_dashboard_defaults():
    args = parse_args([])

    assert args.window == 250
    assert args.confidence == 0.99


def test_backtest_cli_accepts_alternate_window_and_confidence():
    args = parse_args(["--window", "500", "--confidence", "0.95"])

    assert args.window == 500
    assert args.confidence == 0.95
