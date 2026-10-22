
from pathlib import Path
from datetime import datetime, timezone

import yfinance as yf

ROOT = Path(__file__).resolve().parent
RAW_DIR = ROOT / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

INSTRUMENTS = {
    "brent_proxy": "BZ=F",
    "wti_proxy": "CL=F",
    "natural_gas_proxy": "NG=F",
    "coffee_proxy": "KC=F",
}

def download_prices(name: str, ticker: str) -> None:
    print(f"Downloading {name} ({ticker})...")

    data = yf.download(
        ticker,
        start="2018-01-01",
        auto_adjust=False,
        progress=False,
        threads=False,
    )

    if data.empty:
        print(f"WARNING: No data returned for {ticker}. Skipping.")
        return

    output_file = RAW_DIR / f"{name}.csv"
    data.to_csv(output_file)

    print(f"Saved: {output_file}")
    print(f"Rows: {len(data)}")
    print(f"First date: {data.index.min()}")
    print(f"Last date: {data.index.max()}")

if __name__ == "__main__":
    print("Retrieval time (UTC):", datetime.now(timezone.utc).isoformat())

    for name, ticker in INSTRUMENTS.items():
        try:
            download_prices(name, ticker)
        except Exception as exc:
            print(f"ERROR downloading {ticker}: {exc}")

    print("Download attempt finished. Check the warnings above.")
