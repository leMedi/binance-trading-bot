import os
from dotenv import load_dotenv
from binance.client import Client
from strategies.dualMovingAvgs import DualMovingAvgs

load_dotenv()

BINANCE_API_KEY = os.getenv("BINANCE_API_KEY")
BINANCE_SECRET_KEY = os.getenv("BINANCE_SECRET_KEY")

binance_client = Client(BINANCE_API_KEY, BINANCE_SECRET_KEY)

pair='ENJUSDT'
interval='1m'
s = DualMovingAvgs(name="DualMovingAvgs_{}_{}".format(pair, interval), binance_client=binance_client, pair=pair, initial_capital=100)

s.run(interval)