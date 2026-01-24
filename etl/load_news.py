import requests
import pandas as pd
from sqlalchemy import create_engine, text
import os

API_KEY = os.getenv("NEWS_API_KEY", '')
PG_HOST = os.getenv("POSTGRES_HOST", "")
PG_DB = os.getenv("POSTGRES_DB", "")
PG_USER = os.getenv("POSTGRES_USER", "")
PG_PASS = os.getenv("POSTGRES_PASSWORD", "")

engine = create_engine(f"postgresql://{PG_USER}:{PG_PASS}@{PG_HOST}:5432/{PG_DB}")

with engine.begin() as conn:
    conn.execute(text("DROP TABLE IF EXISTS raw.news;"))

query = "Apple stock"
url = f"https://newsapi.org/v2/everything?q={query}&language=en&sortBy=publishedAt&apiKey={API_KEY}"
resp = requests.get(url).json()

articles = resp["articles"]
df = pd.DataFrame([
    {
        "symbol": "AAPL",
        "headline": a["title"],
        "source": a["source"]["name"],
        "published_at": a["publishedAt"],
        "content": a["description"]
    } for a in articles
])

df.to_sql("news", engine, schema="raw", if_exists="append", index=False)
print("✅ News loaded into Postgres.")
