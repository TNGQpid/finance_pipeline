import requests
import pandas as pd
from sqlalchemy import create_engine, text
from bs4 import BeautifulSoup
import os
from datetime import datetime, timezone
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

PG_HOST = os.getenv("POSTGRES_HOST", "")
PG_DB = os.getenv("POSTGRES_DB", "")
PG_USER = os.getenv("POSTGRES_USER", "")
PG_PASS = os.getenv("POSTGRES_PASS", "")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0 Safari/537.36"
    )
}

REQUEST_TIMEOUT = 15
SLEEP_SECONDS = 0.3 
MAX_THREADS = 3

# -------------------------
# Database
# -------------------------
engine = create_engine(
    f"postgresql://{PG_USER}:{PG_PASS}@{PG_HOST}:5432/{PG_DB}"
)

# -------------------------
# Scraper
# -------------------------
def scrape_article_text(url: str) -> str | None:
    """Attempt to scrape readable article text from a URL."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
    except Exception as e:
        tqdm.write(f"❌ Request failed: {url} ({e})")
        return None

    soup = BeautifulSoup(resp.text, "html.parser")

    for tag in soup(["script", "style", "noscript", "header", "footer", "nav"]):
        tag.decompose()

    paragraphs = [
        p.get_text(" ", strip=True)
        for p in soup.find_all("p")
        if len(p.get_text(strip=True)) > 50
    ]

    if not paragraphs:
        return None

    return "\n\n".join(paragraphs)


def scrape_row(row):
    url = row["url"]
    article_hash = row["hash"]

    tqdm.write(f"🔗 Scraping: {url}")
    text_content = scrape_article_text(url)

    if not text_content:
        tqdm.write("⚠️ No content extracted")
        return None

    time.sleep(SLEEP_SECONDS)  

    return {
        "hash": article_hash,
        "url": url,
        "full_text": text_content,
        "scraped_at": datetime.now(timezone.utc),
    }


def main():
    # Ensure table exists
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS raw.news_full_article (
                hash VARCHAR(64) PRIMARY KEY,
                url TEXT,
                full_text TEXT,
                scraped_at TIMESTAMP
            );
        """))

    # Pull URLs not yet scraped
    query = """
        SELECT n.hash, n.url
        FROM raw.news n
        LEFT JOIN raw.news_full_article f
          ON n.hash = f.hash
        WHERE f.hash IS NULL
          AND n.url IS NOT NULL
    """
    df = pd.read_sql(query, engine)
    df = df.iloc[0:20] 

    if df.empty:
        print("✅ No new articles to scrape.")
        return

    print(f"📰 Scraping {len(df)} articles with {MAX_THREADS} threads...")

    rows = []

    # Use ThreadPoolExecutor for parallel scraping
    with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        future_to_row = {executor.submit(scrape_row, row): row for _, row in df.iterrows()}

        for future in tqdm(as_completed(future_to_row), total=len(df), desc="Articles completed"):
            result = future.result()
            if result:
                rows.append(result)

    if not rows:
        tqdm.write("⚠️ Nothing scraped successfully.")
        return

    out_df = pd.DataFrame(rows)
    out_df = out_df.drop_duplicates(subset="hash")  # safe guard

    # Write all results at once
    out_df.to_sql(
        "news_full_article",
        engine,
        schema="raw",
        if_exists="append",
        index=False,
        method="multi",
        chunksize=100,
    )

    print(f"✅ Stored {len(out_df)} full articles.")

# -------------------------
# Entry point
# -------------------------
if __name__ == "__main__":
    main()
