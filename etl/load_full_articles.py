import requests
import pandas as pd
from sqlalchemy import create_engine, text
from bs4 import BeautifulSoup
import os
from datetime import datetime
import time
from datetime import timezone
from tqdm import tqdm

PG_HOST = os.getenv("POSTGRES_HOST", "")
PG_DB = os.getenv("POSTGRES_DB", "")
PG_USER = os.getenv("POSTGRES_USER", "")
PG_PASS = os.getenv("POSTGRES_PASS", "")

engine = create_engine(
    f"postgresql://{PG_USER}:{PG_PASS}@{PG_HOST}:5432/{PG_DB}"
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0 Safari/537.36"
    )
}

REQUEST_TIMEOUT = 15
SLEEP_SECONDS = 0.4


def scrape_article_text(url: str) -> str | None:
    """Attempt to scrape readable article text from a URL."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
    except Exception as e:
        print(f"❌ Request failed: {url} ({e})")
        return None

    soup = BeautifulSoup(resp.text, "html.parser")

    for tag in soup(["script", "style", "noscript", "header", "footer", "nav"]):
        tag.decompose()

    # Heuristic: grab paragraphs with real text
    paragraphs = [
        p.get_text(" ", strip=True)
        for p in soup.find_all("p")
        if len(p.get_text(strip=True)) > 50
    ]

    if not paragraphs:
        return None

    return "\n\n".join(paragraphs)


# -------------------------
# Main
# -------------------------
def main():
    with engine.begin() as conn:
        # Create table if missing
        conn.execute(text("""CREATE TABLE IF NOT EXISTS raw.news_full_article (
                        hash VARCHAR(64) PRIMARY KEY, url TEXT, full_text TEXT, scraped_at TIMESTAMP
                        );"""))

    # Pull URLs that haven't been scraped yet
    query = """
        SELECT n.hash, n.url
        FROM raw.news n
        LEFT JOIN raw.news_full_article f
          ON n.hash = f.hash
        WHERE f.hash IS NULL
          AND n.url IS NOT NULL
    """

    df = pd.read_sql(query, engine)

    if df.empty:
        print("✅ No new articles to scrape.")
        return

    print(f"📰 Scraping {len(df)} articles...")

    rows = []

    for _, row in tqdm(df.iterrows(), total=len(df), desc="Scraping articles"):
        url = row["url"]
        article_hash = row["hash"]

        #print(f"🔗 Scraping: {url}")
        tqdm.write(f"🔗 Scraping: {url}")

        text_content = scrape_article_text(url)

        if not text_content:
            #print("⚠️ No content extracted")
            tqdm.write("⚠️ No content extracted")
            continue

        rows.append({
            "hash": article_hash,
            "url": url,
            "full_text": text_content,
            "scraped_at": datetime.now(timezone.utc),
        })

        time.sleep(SLEEP_SECONDS)

    if not rows:
        #print("⚠️ Nothing scraped successfully.")
        tqdm.write("⚠️ Nothing scraped successfully.")
        return

    out_df = pd.DataFrame(rows)

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


if __name__ == "__main__":
    main()
