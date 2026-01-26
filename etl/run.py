# run.py
import subprocess
from time import sleep

print("Starting pipeline...")
print("Running step 1 - Load Prices")
subprocess.run(["python", "load_prices.py"], check=True)
print("Step 1 completed.")
print("Running step 2 - Load News")
subprocess.run(["python", "load_news.py"], check=True)
print("Step 2 completed.")
print("Running step 3 (final step) - Scrape and Load Full Articles")
subprocess.run(["python", "-u", "load_full_articles.py"], check=True)
print("Step 3 completed.")
print("Pipeline completed successfully.")