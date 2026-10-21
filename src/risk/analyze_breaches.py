from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RESULTS_FILE = ROOT / "reports" / "var_backtest_results.csv"



def main() -> None:
    if not RESULTS_FILE.exists():
        raise FileNotFoundError(
            f"Missing {RESULTS_FILE}. Run src.risk.run_backtest first."
        )

    results = pd.read_csv(RESULTS_FILE, parse_dates=["date"])

    required = {"date", "actual_pnl_usd", "var_loss_usd", "breach"}
    missing = required - set(results.columns)

    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    results = results.sort_values("date").copy()

    # Normalize breach values in case CSV booleans were read as strings.
    results["breach"] = (
        results["breach"]
        .astype(str)
        .str.strip()
        .str.lower()
        .map({"true": True, "false": False})
    )

    if results["breach"].isna().any():
        raise ValueError("Unrecognized values in breach column.")

    results["loss_usd"] = -results["actual_pnl_usd"]
    results["excess_loss_usd"] = (
        results["loss_usd"] - results["var_loss_usd"]
    )

    breaches = results.loc[results["breach"]].copy()

    if breaches.empty:
        print("No VaR breaches found.")
        return

    # Identify consecutive breaches in the ordered observations.
    breach_flags = results["breach"]
    results["breach_cluster"] = (
        breach_flags.ne(breach_flags.shift()).cumsum()
    )

    cluster_sizes = (
        results.loc[results["breach"]]
        .groupby("breach_cluster")
        .size()
    )

    print("\nBACKTEST BREACH ANALYSIS")
    print(f"Total observations: {len(results)}")
    print(f"Total breaches: {len(breaches)}")
    print(f"Breach rate: {results['breach'].mean():.4%}")
    print(f"Longest consecutive breach run: {cluster_sizes.max()}")

    print("\nBREACH DETAILS")
    print(
        breaches[
            ["date", "actual_pnl_usd", "var_loss_usd", "excess_loss_usd"]
        ].to_string(index=False)
    )

    output = ROOT / "reports" / "var_breach_analysis.csv"
    breaches[
        ["date", "actual_pnl_usd", "var_loss_usd", "excess_loss_usd"]
    ].to_csv(output, index=False)

    print(f"\nSaved breach details to {output}")


if __name__ == "__main__":
    main()
