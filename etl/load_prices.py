import os
import yfinance as yf
import pandas as pd
from sqlalchemy import create_engine, text

# -----------------------
# Database configuration
# -----------------------
PG_HOST = os.getenv("POSTGRES_HOST", "")
PG_DB   = os.getenv("POSTGRES_DB", "")
PG_USER = os.getenv("POSTGRES_USER", "")
PG_PASS = os.getenv("POSTGRES_PASSWORD", "")

engine = create_engine(f"postgresql://{PG_USER}:{PG_PASS}@{PG_HOST}:5432/{PG_DB}")

# -----------------------
# Helpers
# -----------------------
def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize yfinance columns to long-format OHLCV,
    regardless of MultiIndex orientation.
    """

    if isinstance(df.columns, pd.MultiIndex):
        level0 = df.columns.get_level_values(0).astype(str).str.lower()
        level1 = df.columns.get_level_values(1).astype(str).str.lower()

        ohlcv = {"open", "high", "low", "close", "volume"}

        # Decide which level contains OHLCV labels
        if level0.isin(ohlcv).sum() >= level1.isin(ohlcv).sum():
            df.columns = df.columns.get_level_values(0)
        else:
            df.columns = df.columns.get_level_values(1)

    df.columns = (
        pd.Index(df.columns)
        .str.strip()
        .str.lower()
        .str.replace(" ", "_")
        .str.replace(r"[^a-z0-9_]", "", regex=True)
    )

    return df



# -----------------------
# Symbols universe
# -----------------------
symbols = [
    # Tech / Growth
    "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA",
    # Defense / Aerospace
    "LMT", "RTX", "NOC", "GD", "BA",
    # Other major stocks
    "JPM", "XOM", "JNJ", "NVDA", "BRK-B"]

# -----------------------
# Schema setup
# -----------------------
with engine.begin() as conn:
    conn.execute(text("CREATE SCHEMA IF NOT EXISTS raw;"))

# -----------------------
# Load loop
# -----------------------
for symbol in symbols:
    print(f"⬇️  Loading {symbol}...")

    df = yf.download(
        symbol,
        start="2020-01-01",
        end="2025-01-01",
        auto_adjust=True,
        progress=False,
    )

    if df.empty:
        print(f"⚠️  No data for {symbol}, skipping")
        continue

    df.reset_index(inplace=True)

    # Normalize column names BEFORE touching Postgres
    df = normalize_columns(df)

    df["symbol"] = symbol

    # Deduplicate at source (incremental load)
    existing_dates = pd.read_sql(
        """
        SELECT date
        FROM raw.prices
        WHERE symbol = %(symbol)s
        """,
        engine,
        params={"symbol": symbol},
    )

    if not existing_dates.empty:
        df = df[~df["date"].isin(existing_dates["date"])]

    if df.empty:
        print(f"✅ {symbol}: no new rows")
        continue

    # Load
    df.to_sql(
        "prices",
        engine,
        schema="raw",
        if_exists="append",
        index=False,
        method="multi",
        chunksize=1000,
    )

    print(f"✅ {symbol}: loaded {len(df)} rows")

print("🎉 Prices successfully loaded into Postgres.")
