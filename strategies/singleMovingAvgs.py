from core.binance import binance_klines_to_df
from core.strategy import OrderBy, Strategy, OrderType
from datetime import datetime


class SingleMovingAvgs(Strategy):

  ma_window = 5
  time_unit = 'day'
  _col_name = 'Close'

  _prices_df = None

  is_price_under_ma = False

  def setup(self):
    # get prices
    period = "{} {} ago UTC".format(self.ma_window, self.time_unit)
    _prices = self.binance_client.get_historical_klines(self.pair, '1d', period)
    _prices_df = binance_klines_to_df(_prices)
    self._prices_df = _prices_df[self._col_name].copy()

  def get_moving_avg(self, window: float) -> float:
    _ma_df = self._prices_df.rolling(window=window).mean()
    _last_row_df = _ma_df.iloc[[-1]]
    return _last_row_df[0]

  def update_prices_df(self, last_kline_msg):
    index = datetime.now()
    # inject new price in df
    self._prices_df[index] = float(last_kline_msg['c'])
    # get last window elements
    self._prices_df = self._prices_df[-self.ma_window:]
  
  def calc_price(self, price: float, percentage: float) -> float:
    return (percentage + 1)*price

  def rootine(self, msg):
    self.logger.debug('new tick {}'.format(float(msg['k']['c'])))
    
    last_recorded_price = self._prices_df[-1]

    if self.last_price == last_recorded_price:
      self.logger.debug('skip rootine')
      return False

    self.update_prices_df(msg['k'])

    if self.open_order != None:
      # TODO: cancle unreachable orders
      self.logger.debug('waiting for order to execute: type {} price {} qty {}'.format(self.open_order['type'].value, self.open_order['price'], self.open_order['qty']))
      return False
    
    if self.position == None:
      # i want to buy something: listen to me man listen to me
      self.looking_for_buy()
      return True

  def looking_for_buy(self):
    ma  = self.get_moving_avg(window=self.ma_window)
    self.logger.debug('looking_for_buy -> current_price: {} ma: {}'.format(self.last_price, ma), extra={'ma': ma})

    if self.last_price < ma:
      self.is_price_under_ma = True
      self.logger.debug('in golden zone', extra={'ma': ma})
      return False

    if self.last_price > ma and self.is_price_under_ma:
      self.is_price_under_ma = False
      buy_at = self.calc_price(price=self.last_price, percentage=0.002)
      self.logger.info('buying at {}'.format(buy_at), extra={'buy_at': buy_at})

  def order_execution_hook(self, msg):
    # orders docs https://docs.binance.org/api-reference/dex-api/ws-streams.html
    if self.position != None:
      sell_at = self.calc_price(price=self.last_price , percentage=0.05)
      self.place_order(order_type=OrderType.SELL, limit_price=sell_at, order_by=OrderBy.QUANTITY, value=self.position['qty'])