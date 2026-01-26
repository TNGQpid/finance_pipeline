# run.py
import subprocess
from time import sleep

subprocess.run(["python", "load_prices.py"], check=True)
subprocess.run(["python", "load_news.py"], check=True)
sleep(5)
#subprocess.run(["python", "load_full_articles.py"], check=True)