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

    if df.empty:
        raise ValueError(f"No price data found in {filename}")

    if df["date"].isna().any():
        raise ValueError(f"Invalid dates found in {filename}")

    # These are daily prices; align timestamps to their calendar date.
    df["date"] = df["date"].dt.normalize()
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
    commodity_prices = {
        filename.removesuffix(".csv"): load_prices(filename)
        for filename in COMMODITY_FILES
    }
    crypto_prices = {
        filename.removesuffix(".csv"): load_prices(filename)
        for filename in CRYPTO_FILES
    }

    all_price_series = [
        *commodity_prices.values(),
        *crypto_prices.values(),
    ]

    # Use only the date range covered by every source.
    common_start = max(series.index.min() for series in all_price_series)
    common_end = min(series.index.max() for series in all_price_series)

    # Build a calendar-day valuation index so BTC/ETH weekend returns remain.
    valuation_dates = pd.date_range(
        start=common_start,
        end=common_end,
        freq="D",
        name="date",
    )

    commodity_price_df = pd.concat(
        commodity_prices.values(), axis=1
    ).sort_index()

    crypto_price_df = pd.concat(
        crypto_prices.values(), axis=1
    ).sort_index()

    # Carry commodity closes over weekends and other non-trading dates.
    commodity_on_calendar = commodity_price_df.reindex(
        valuation_dates
    ).ffill()

    # Keep actual BTC and ETH prices. Do not invent prices for missing dates.
    crypto_on_calendar = crypto_price_df.reindex(valuation_dates)

    # Report any missing crypto dates; returns requiring those prices are dropped.
    missing_crypto_dates = crypto_on_calendar.index[
        crypto_on_calendar.isna().any(axis=1)
    ]
    if len(missing_crypto_dates) > 0:
        print(
            f"Warning: {len(missing_crypto_dates)} calendar dates have "
            "missing crypto prices. Returns requiring those prices will "
            "be excluded."
        )

    valuation_prices = pd.concat(
        [commodity_on_calendar, crypto_on_calendar], axis=1
    )

    returns_df = valuation_prices.pct_change(fill_method=None)
    returns_df = returns_df.dropna(how="any")

    # Save the aligned six-asset return panel.
    aligned_path = RETURNS_DIR / "aligned_returns.csv"
    returns_df.to_csv(aligned_path)

    # Keep the existing output filename for compatibility with the project.
    individual_path = RETURNS_DIR / "individual_returns.csv"
    returns_df.to_csv(individual_path)

    weekend_mask = returns_df.index.dayofweek >= 5

    print("Returns by asset:")
    print(returns_df.count())
    print("\nAligned observations:", len(returns_df))
    print("Weekend return observations:", int(weekend_mask.sum()))
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