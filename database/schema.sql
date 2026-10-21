
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS instruments (
    instrument_id INTEGER PRIMARY KEY,
    symbol TEXT NOT NULL UNIQUE,
    instrument_name TEXT NOT NULL,
    asset_class TEXT NOT NULL,
    data_source TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS prices (
    instrument_id INTEGER NOT NULL,
    price_date TEXT NOT NULL,
    close_price REAL NOT NULL CHECK (close_price > 0),
    PRIMARY KEY (instrument_id, price_date),
    FOREIGN KEY (instrument_id)
        REFERENCES instruments(instrument_id)
);

CREATE TABLE IF NOT EXISTS daily_returns (
    instrument_id INTEGER NOT NULL,
    return_date TEXT NOT NULL,
    daily_return REAL NOT NULL,
    PRIMARY KEY (instrument_id, return_date),
    FOREIGN KEY (instrument_id)
        REFERENCES instruments(instrument_id)
);

CREATE TABLE IF NOT EXISTS portfolio_positions (
    position_id INTEGER PRIMARY KEY,
    instrument_id INTEGER NOT NULL,
    notional_usd REAL NOT NULL,
    portfolio_name TEXT NOT NULL,
    FOREIGN KEY (instrument_id)
        REFERENCES instruments(instrument_id)
);

CREATE TABLE IF NOT EXISTS risk_metrics (
    metric_id INTEGER PRIMARY KEY,
    calculation_date TEXT NOT NULL,
    portfolio_name TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    confidence_level REAL,
    metric_value REAL NOT NULL,
    methodology TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ingestion_log (
    ingestion_id INTEGER PRIMARY KEY,
    source_file TEXT NOT NULL,
    ingestion_time_utc TEXT NOT NULL,
    row_count INTEGER NOT NULL,
    status TEXT NOT NULL,
    message TEXT
);
