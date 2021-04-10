from datetime import timedelta
from enum import Enum
import os
from dotenv import load_dotenv
from binance.client import Client
from strategies.dualMovingAvgs import DualMovingAvgs

load_dotenv()

BINANCE_API_KEY = os.getenv("BINANCE_API_KEY")
BINANCE_SECRET_KEY = os.getenv("BINANCE_SECRET_KEY")

binance_client = Client(BINANCE_API_KEY, BINANCE_SECRET_KEY)

# pair='ENJUSDT'
str_interval='30s'
interval=timedelta(seconds=30)


FIAT = 'USDT'
COINS = ['ENJ', 'DOGE', 'BTT'] 

pairs = [coin+FIAT for coin in COINS]

bots = []
for pair in pairs:
  bot = DualMovingAvgs(name="DualMovingAvgs_{}_{}".format(pair, str_interval), binance_client=binance_client, pair=pair, initial_capital=100)
  bot.run(interval)
  bots.append(bot)

print('Main:', len(bots), 'bots running')
# s.run(interval)