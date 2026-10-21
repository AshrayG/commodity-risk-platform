
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

FILES = {
    # Commodities
    "brent_proxy": "brent_proxy.csv",
    "wti_proxy": "wti_proxy.csv",
    "natural_gas_proxy": "natural_gas_proxy.csv",
    "coffee_proxy": "coffee_proxy.csv",

    # Cryptocurrency
    "bitcoin": "bitcoin.csv",
    "ethereum": "ethereum.csv",
}


def clean_file(instrument: str, filename: str) -> None:
    path = RAW_DIR / filename

    if not path.exists():
        print(f"SKIP: Missing file {path}")
        return

    # First try yfinance's two-level CSV header.
    try:
        df = pd.read_csv(path, header=[0, 1], index_col=0)

        close_cols = [
            col for col in df.columns
            if isinstance(col, tuple)
            and str(col[0]).lower() == "close"
        ]

        if close_cols:
            date_values = pd.to_datetime(
                df.index, errors="coerce", utc=True
            )
            prices = pd.to_numeric(
                df[close_cols[0]], errors="coerce"
            )
        else:
            raise ValueError("No Close column in two-row header")

    except (ValueError, IndexError, pd.errors.ParserError):
        # Fallback for a conventional single-row CSV header.
        df = pd.read_csv(path)

        close_cols = [
            col for col in df.columns
            if str(col).lower() == "close"
        ]

        if not close_cols:
            raise ValueError(
                f"No Close column found in {filename}. "
                f"Columns: {list(df.columns)}"
            )

        if len(df.columns) == 0:
            raise ValueError(f"No columns found in {filename}")

        date_values = pd.to_datetime(
            df.iloc[:, 0], errors="coerce", utc=True
        )
        prices = pd.to_numeric(
            df[close_cols[0]], errors="coerce"
        )

    clean = pd.DataFrame({
        "date": date_values,
        "instrument": instrument,
        "close": prices.to_numpy(),
    })

    clean = clean.dropna(subset=["date", "close"])
    clean["date"] = clean["date"].dt.strftime("%Y-%m-%d")
    clean = clean[clean["close"] > 0]
    clean = clean.drop_duplicates(
        subset=["date", "instrument"], keep="last"
    )
    clean = clean.sort_values("date")

    if clean.empty:
        raise ValueError(f"No valid rows remain for {instrument}")

    output = PROCESSED_DIR / f"{instrument}.csv"
    clean.to_csv(output, index=False)

    print(
        f"{instrument}: {len(clean)} valid rows | "
        f"{clean['date'].min()} to {clean['date'].max()} | "
        f"saved to {output}"
    )


def main() -> None:
    for instrument, filename in FILES.items():
        clean_file(instrument, filename)

    print("Cleaning finished.")


if __name__ == "__main__":
    main()
