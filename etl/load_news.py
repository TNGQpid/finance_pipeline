import requests
import pandas as pd
from sqlalchemy import create_engine, text
import os

API_KEY = os.getenv("NEWS_API_KEY", '')
PG_HOST = os.getenv("POSTGRES_HOST", "")
PG_DB = os.getenv("POSTGRES_DB", "")
PG_USER = os.getenv("POSTGRES_USER", "")
PG_PASS = os.getenv("POSTGRES_PASS", "")

engine = create_engine(f"postgresql://{PG_USER}:{PG_PASS}@{PG_HOST}:5432/{PG_DB}")

with engine.begin() as conn:
    conn.execute(text("DROP TABLE IF EXISTS raw.news;"))
    conn.execute(text("CREATE TABLE IF NOT EXISTS raw.news(symbol VARCHAR(10), headline TEXT, source VARCHAR(100), published_at TIMESTAMP, content TEXT);"))

symbols = [
    # Tech / Growth
    "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA",
    # Defense / Aerospace
    "LMT", "RTX", "NOC", "GD", "BA",
    # Other major stocks
    "JPM", "XOM", "JNJ", "NVDA", "BRK-B"
]
for symbol in symbols:
    print(f"⬇️ Fetching news for {symbol}...")

    url = f"https://newsapi.org/v2/everything?q={symbol}&language=en&sortBy=publishedAt&apiKey={API_KEY}"
    resp = requests.get(url).json()
    articles = resp.get("articles", [])

    if not articles:
        print(f"⚠️ No articles for {symbol}")
        continue

    df = pd.DataFrame([
        {
            "symbol": symbol,
            "headline": a.get("title"),
            "source": a.get("source", {}).get("name"),
            "published_at": pd.to_datetime(a.get("publishedAt")),
            "content": a.get("content")
        } for a in articles
    ])

    if df.empty:
        continue

    # Deduplicate against Postgres
    existing = pd.read_sql(
        """
        SELECT symbol, published_at
        FROM raw.news
        WHERE symbol = %(symbol)s
        """,
        engine,
        params={"symbol": symbol},
    )

    if not existing.empty:
        # Ensure datetime types match
        existing["published_at"] = pd.to_datetime(existing["published_at"])
        df["published_at"] = pd.to_datetime(df["published_at"])

        # Keep only new rows
        df = df[~df[["symbol", "published_at"]].apply(tuple, 1).isin(
            existing[["symbol", "published_at"]].apply(tuple, 1)
        )]

    if df.empty:
        print(f"✅ {symbol}: no new articles")
        continue

    # Insert into Postgres
    df.to_sql("news", engine, schema="raw", if_exists="append", index=False, method="multi", chunksize=500)
    print(f"✅ Loaded {len(df)} new articles for {symbol}")

print("✅ All news loaded into Postgres.")
