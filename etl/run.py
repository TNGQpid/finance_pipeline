# run.py
import subprocess

subprocess.run(["python", "load_prices.py"], check=True)
subprocess.run(["python", "load_news.py"], check=True)
