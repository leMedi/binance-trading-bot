from datetime import timedelta
from enum import Enum
from core.strategy import OrderType
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
interval=timedelta(minutes=1)


FIAT = 'USDT'
COINS = [
  # {'name': 'ATOM', 'price_precision': 3, 'qty_precision': 3},
  # {'name': 'DOGE', 'price_precision': 7, 'qty_precision': 0},
  # {'name': 'NEO', 'price_precision': 3, 'qty_precision': 3},
  {'name': 'VET', 'price_precision': 6, 'qty_precision': 0},
  # {'name': 'MTL', 'price_precision': 4, 'qty_precision': 2},
  # {'name': 'UNI', 'price_precision': 4, 'qty_precision': 2},

]
# COINS = ['DOGE', 'BTT'] 

# pairs = [coin+FIAT for coin in COINS]

bots = []
for coin in COINS:
  pair = '{}{}'.format(coin['name'], FIAT)
  bot = DualMovingAvgs(name="DualMovingAvgs_{}_{}".format(pair, str_interval), binance_client=binance_client, pair=pair, initial_capital=33, price_precision=coin['price_precision'], qty_precision=coin['qty_precision'])
  bot.run(interval)
  bots.append(bot)

print('Main:', len(bots), 'bots running')
# s.run(interval)