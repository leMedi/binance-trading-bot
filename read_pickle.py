from enum import Enum
import sys
import pickle

class OrderType(Enum):
  SELL = "SELL"
  BUY = "BUY"


# with open('/Users/elmehdielhaij/workspace/blue-beard-capital/binance-trading-bot/checkpoints/DualMovingAvgs_DOGEUSDT_30s_checkpoint.pickle', 'wb') as outfile:
#   pickle.dump(checkpoint, outfile)

pickle_file_path = sys.argv[1]
print(pickle_file_path)
with open(pickle_file_path, 'rb') as pickle_file:
  x = pickle.load(pickle_file)
  print(x)