from enum import Enum
import pickle

class OrderType(Enum):
  SELL = "SELL"
  BUY = "BUY"


open_order = {
  'type': OrderType.SELL,
  'price': 0.0761263,
  'qty': 146.0
}

position = {'qty': 146.0, 'entry_price': 0.0755233}

checkpoint = {
  'position': position,
  'open_order': open_order
}

print(checkpoint)


with open('/Users/elmehdielhaij/workspace/blue-beard-capital/binance-trading-bot/checkpoints/DualMovingAvgs_DOGEUSDT_30s_checkpoint.pickle', 'wb') as outfile:
  pickle.dump(checkpoint, outfile)


with open('/Users/elmehdielhaij/workspace/blue-beard-capital/binance-trading-bot/checkpoints/DualMovingAvgs_DOGEUSDT_30s_checkpoint.pickle', 'rb') as pickle_file:
  x = pickle.load(pickle_file)
  print(x)