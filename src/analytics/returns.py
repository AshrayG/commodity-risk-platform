
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = ROOT / "data" / "processed"
RETURNS_DIR = PROCESSED_DIR / "returns"
RETURNS_DIR.mkdir(parents=True, exist_ok=True)

COMMODITY_FILES = [
    "brent_proxy.csv",
    "wti_proxy.csv",
    "natural_gas_proxy.csv",
    "coffee_proxy.csv",
]

CRYPTO_FILES = [
    "bitcoin.csv",
    "ethereum.csv",
]


def load_prices(filename: str) -> pd.Series:
    path = PROCESSED_DIR / filename

    if not path.exists():
        raise FileNotFoundError(f"Price file not found: {path}")

    df = pd.read_csv(path, parse_dates=["date"])
    df = df.sort_values("date")

    if df["date"].duplicated().any():
        raise ValueError(f"Duplicate dates found in {filename}")

    prices = pd.to_numeric(
        df.set_index("date")["close"], errors="coerce"
    ).sort_index()

    if prices.isna().any() or (prices <= 0).any():
        raise ValueError(f"Invalid prices found in {filename}")

    prices.name = filename.removesuffix(".csv")
    return prices


def main() -> None:
    # Load all prices separately.
    commodity_prices = {
        filename.removesuffix(".csv"): load_prices(filename)
        for filename in COMMODITY_FILES
    }
    crypto_prices = {
        filename.removesuffix(".csv"): load_prices(filename)
        for filename in CRYPTO_FILES
    }

    # Use dates shared by all four commodity price series.
    commodity_price_df = pd.concat(
        commodity_prices.values(), axis=1, join="inner"
    ).sort_index()

    commodity_dates = commodity_price_df.index

    # Calculate commodity returns on the commodity valuation calendar.
    commodity_returns = commodity_price_df.pct_change(
        fill_method=None
    )

    # Align crypto prices to commodity dates BEFORE calculating returns.
    # Forward-fill only the latest known crypto close onto valuation dates.
    crypto_price_df = pd.concat(
        crypto_prices.values(), axis=1
    ).sort_index()

    crypto_on_commodity_dates = crypto_price_df.reindex(
        commodity_dates, method="ffill"
    )

    crypto_returns = crypto_on_commodity_dates.pct_change(
        fill_method=None
    )

    # Combine all six return series on the shared valuation calendar.
    returns_df = pd.concat(
        [commodity_returns, crypto_returns], axis=1
    ).sort_index()

    returns_df = returns_df.dropna(how="any")

    # Save the aligned six-asset return panel.
    aligned_path = RETURNS_DIR / "aligned_returns.csv"
    returns_df.to_csv(aligned_path)

    # Save individual returns on the same valuation calendar for comparison.
    individual_path = RETURNS_DIR / "individual_returns.csv"
    returns_df.to_csv(individual_path)

    print("Returns by asset:")
    print(returns_df.count())
    print("\nAligned observations:", len(returns_df))
    print(
        "Date range:",
        returns_df.index.min(),
        "to",
        returns_df.index.max(),
    )
    print(f"\nSaved: {aligned_path}")
    print(f"Saved: {individual_path}")


if __name__ == "__main__":
    main()

