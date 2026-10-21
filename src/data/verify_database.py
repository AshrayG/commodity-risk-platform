
import sqlite3
from pathlib import Path

db_path = Path("database/commodity_risk.db")

if not db_path.exists():
    raise FileNotFoundError(f"Database not found: {db_path}")

with sqlite3.connect(db_path) as conn:
    tables = conn.execute(
        "SELECT name FROM sqlite_master "
        "WHERE type = 'table' ORDER BY name"
    ).fetchall()

    print("DATABASE:", db_path.resolve())
    print("\nTABLES:")

    for (table_name,) in tables:
        print(f"\n{table_name}")

        if table_name in {
            "instruments",
            "prices",
            "daily_returns",
            "portfolio_positions",
            "risk_metrics",
            "ingestion_log",
        }:
            count = conn.execute(
                f"SELECT COUNT(*) FROM {table_name}"
            ).fetchone()[0]
            print("Rows:", count)

    print("\nINSTRUMENTS:")
    for row in conn.execute(
        "SELECT symbol, instrument_name FROM instruments ORDER BY symbol"
    ):
        print(row)
