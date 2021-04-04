from core.binance import binance_klines_to_df
from core.strategy import OrderBy, Strategy, OrderType
from datetime import datetime
from numpy import percentile
import pandas as pd

class DualMovingAvgs(Strategy):

  short_ma_period = 7
  long_ma_period = 25
  time_unit = 'minutes'
  _col_name = 'Close'

  _prices_df = None

  _waiting_for_buy_signal = False

  def setup(self):
    # get prices
    period = self.long_ma_period
    period = str(period) + " minutes ago UTC"
    _prices = self.binance_client.get_historical_klines(self.pair, '1m', period)
    _prices_df = binance_klines_to_df(_prices)
    self._prices_df = _prices_df[self._col_name].copy()

    short_ma = self.get_moving_avg(window=self.short_ma_period)
    long_ma = self.get_moving_avg(window=self.long_ma_period)

    print(_prices_df.iloc[[-1]].index[0])

    print(self._prices_df.iloc[[-1]].index[0], long_ma, short_ma)

  def get_moving_avg(self, window: float) -> float:
    _ma_df = self._prices_df.rolling(window=window).mean()
    _last_row_df = _ma_df.iloc[[-1]]
    return _last_row_df[0]

  def update_prices_df(self, last_kline_msg):
    # add row
    # index = pd.to_datetime(last_kline_msg['T'], unit='ms')
    index = datetime.now()
    self._prices_df[index] = float(last_kline_msg['c'])
    if self._prices_df.shape[0] > self.long_ma_period:
      # take last long_ma_period rows
      _end = 1+self.long_ma_period
      # self._prices_df = self._prices_df.iloc[[1, _end]]
      self._prices_df = self._prices_df[1:_end]
  
  def calc_price(self, price: float, percentage: float) -> float:
    return (percentage + 1)*price

  def rootine(self, msg):
    # self.logger.error('new tick', float(msg['k']['c']))
    self.logger.info('new tick'.format(float(msg['k']['c'])))
    
    last_price = float(msg['k']['c'])
    last_recorded_price = self._prices_df[-1]

    if last_price == last_recorded_price:
      print('skip rootine')
      return False

    self.update_prices_df(msg['k'])

    if self.open_order != None:
      # TODO: cancle unreachable orders
      print('waiting for order to execute')
      return False
    
    if self.position == None:
      self.looking_for_buy()
      return True

    if self.position != None:
      print('postion is open - ', 'qty:', self.position.qty, 'returns: ', self.get_position_returns())
      return True

  def looking_for_buy(self):
    short_ma = self.get_moving_avg(window=self.short_ma_period)
    long_ma  = self.get_moving_avg(window=self.long_ma_period)
    print('looking_for_buy', short_ma, long_ma)

    if short_ma < long_ma:
      self._waiting_for_buy_signal = True
      print('in golden zone', short_ma, long_ma)

      returns = self._prices_df.pct_change(5)
      last_return = returns.tail(1)[0]
      
      if last_return > 0:
        # price is on the rise
        print('price is on the rise', last_return, 'for the last', self.short_ma_period, 'ticks')
        if short_ma/long_ma > 0.998:
          buy_at = self.calc_price(price=long_ma, percentage=0)
          print('buying at', buy_at)
          self.place_order(order_type=OrderType.BUY, limit_price=buy_at, order_by=OrderBy.VALUE, value=self._capital)
      return False

    if short_ma > long_ma:
      self._waiting_for_buy_signal = False

  # def looking_for_sell(self):
  #   # TODO: find sell signal
  #   returns = self.get_position_returns()
  #   if returns >= 0.2:
      

  def order_execution_hook(self, order):
    # orders docs https://docs.binance.org/api-reference/dex-api/ws-streams.html
    if self.position != None:
      sell_at = self.calc_price(price=self.last_price , percentage=0.03)
      self.open_order(order_type=OrderType.SELL, limit_price=sell_at, order_by=OrderBy.QUANTITY, value=self.position.qty)