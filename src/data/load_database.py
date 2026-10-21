
from pathlib import Path
import sqlite3

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DB_DIR = ROOT / "database"
DB_PATH = DB_DIR / "commodity_risk.db"
SCHEMA_PATH = DB_DIR / "schema.sql"
PROCESSED_DIR = ROOT / "data" / "processed"
RETURNS_DIR = PROCESSED_DIR / "returns"

INSTRUMENTS = {
    "brent_proxy": ("Brent crude proxy", "Energy"),
    "wti_proxy": ("WTI crude proxy", "Energy"),
    "natural_gas_proxy": ("Natural gas proxy", "Energy"),
    "coffee_proxy": ("Coffee proxy", "Soft commodity"),
}


def main():
    DB_DIR.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))

        for symbol, (name, asset_class) in INSTRUMENTS.items():
            conn.execute(
                """
                INSERT INTO instruments
                    (symbol, instrument_name, asset_class, data_source)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(symbol) DO UPDATE SET
                    instrument_name = excluded.instrument_name,
                    asset_class = excluded.asset_class,
                    data_source = excluded.data_source
                """,
                (symbol, name, asset_class, "Yahoo Finance via yfinance"),
            )

        ids = dict(
            conn.execute(
                "SELECT symbol, instrument_id FROM instruments"
            ).fetchall()
        )

        for symbol in INSTRUMENTS:
            price_file = PROCESSED_DIR / f"{symbol}.csv"
            return_file = RETURNS_DIR / "individual_returns.csv"

            prices = pd.read_csv(price_file, parse_dates=["date"])
            price_rows = [
                (ids[symbol], row.date.strftime("%Y-%m-%d"), float(row.close))
                for row in prices.itertuples(index=False)
            ]

            conn.executemany(
                """
                INSERT INTO prices (instrument_id, price_date, close_price)
                VALUES (?, ?, ?)
                ON CONFLICT(instrument_id, price_date)
                DO UPDATE SET close_price = excluded.close_price
                """,
                price_rows,
            )

            returns = pd.read_csv(return_file, parse_dates=[0])
            column = symbol
            if column not in returns.columns:
                raise ValueError(f"Missing return column: {column}")

            return_rows = []
            for _, row in returns.iterrows():
                if pd.isna(row[column]) or pd.isna(row.iloc[0]):
                    continue
                return_rows.append(
                    (
                        ids[symbol],
                        pd.Timestamp(row.iloc[0]).strftime("%Y-%m-%d"),
                        float(row[column]),
                    )
                )

            conn.executemany(
                """
                INSERT INTO daily_returns
                    (instrument_id, return_date, daily_return)
                VALUES (?, ?, ?)
                ON CONFLICT(instrument_id, return_date)
                DO UPDATE SET daily_return = excluded.daily_return
                """,
                return_rows,
            )

            print(
                f"{symbol}: loaded {len(price_rows)} prices "
                f"and {len(return_rows)} returns"
            )

        print("Database:", DB_PATH)

        counts = conn.execute(
            """
            SELECT i.symbol, COUNT(p.price_date)
            FROM instruments i
            LEFT JOIN prices p ON p.instrument_id = i.instrument_id
            GROUP BY i.symbol
            ORDER BY i.symbol
            """
        ).fetchall()

        print("Database price counts:")
        for symbol, count in counts:
            print(f"  {symbol}: {count}")


if __name__ == "__main__":
    main()
