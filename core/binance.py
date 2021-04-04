import datetime
import pandas as pd
import numpy as np

def binance_klines_to_df(klines):
  df = pd.DataFrame(np.array(klines).reshape(-1,12),dtype=float, columns = ('Open Time',
                                                                    'Open',
                                                                    'High',
                                                                    'Low',
                                                                    'Close',
                                                                    'Volume',
                                                                    'Close time',
                                                                    'Quote asset volume',
                                                                    'Number of trades',
                                                                    'Taker buy base asset volume',
                                                                    'Taker buy quote asset volume',
                                                                    'Ignore'))

  df['Open Time'] = pd.to_datetime(df['Open Time'], unit='ms')
  df['Close time'] = pd.to_datetime(df['Close time'], unit='ms')

  # change index
  df = df.set_index('Close time')

  return df


def prices_dataframe(binance_client, symbols, interval, start, end=""):
  # get historical data
  klines = {}
  for s in symbols:
    raw_klines = binance_client.get_historical_klines(s, interval, start, end)
    df = binance_klines_to_df(raw_klines)
    klines[s] = df
  
  prices = pd.DataFrame()
  for s in symbols:
    prices[s] = klines[s].Close

  return prices