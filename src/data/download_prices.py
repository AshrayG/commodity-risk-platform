
from pathlib import Path
import yfinance as yf

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

START_DATE = "2018-01-01"

TICKERS = {
    # Commodity futures
    "brent_proxy": "BZ=F",
    "wti_proxy": "CL=F",
    "natural_gas_proxy": "NG=F",
    "coffee_proxy": "KC=F",

    # Cryptocurrency
    "bitcoin": "BTC-USD",
    "ethereum": "ETH-USD",
}


def download_prices(name: str, ticker: str) -> None:
    print(f"\nDownloading {name}: {ticker}")

    try:
        df = yf.download(
            ticker,
            start=START_DATE,
            auto_adjust=False,
            progress=False,
            threads=False,
        )

        if df.empty:
            print(f"No data returned for {ticker}")
            return

        output = RAW_DIR / f"{name}.csv"
        df.to_csv(output)

        print(f"Saved {len(df)} rows to {output}")

    except Exception as error:
        print(f"Download failed for {ticker}: {error}")


def main() -> None:
    for name, ticker in TICKERS.items():
        download_prices(name, ticker)

    print("\nDownload process finished.")


if __name__ == "__main__":
    main()
