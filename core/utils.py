
import math

def round_down(num, digits):
  if digits == 0:
    return round(num)

  factor = 10.0 ** digits
  return math.floor(num * factor) / factor