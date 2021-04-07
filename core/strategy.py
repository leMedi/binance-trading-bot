from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from enum import Enum
from termcolor import cprint
from binance.websockets import BinanceSocketManager
from pythonjsonlogger import jsonlogger
import logging
import logging.handlers
import logging

class OrderType(Enum):
  SELL = "BUY"
  BUY = "SELL"

class OpenPositionType(Enum):
  OPEN = "OPEN"
  CLOSE = "CLOSE"

class OrderBy(Enum):
  QUANTITY = 'QTY'
  VALUE = 'PRICE'

class LogType(Enum):
  INFO = '[+]'
  ERROR = '[!]'

class Strategy(ABC):
  interval_timedelta = None
  last_tick_datetime = None
  open_order = None
  position = None

  order_history = list()
  last_price = None

  def __init__(self, name, binance_client, pair: str, initial_capital: float, precision = 5) -> None:
    self.name = name
    self.binance_client = binance_client
    self.pair = pair
    self.initial_capital = initial_capital
    self._capital = initial_capital

    self.precision = precision

    self.init_logger(save_to_file=True)
    # self.load_checkpoint()


  def load_checkpoint(self):
    print('loading check point')
    self._open_postion(40.2, 2.48504)
    self.place_order(OrderType.SELL, 2.50989, OrderBy.QUANTITY, 40.2)
    print('check point loaded')
    
  def run(self, interval: str = '1m'):
    self.interval_timedelta = timedelta(minutes=1)
    
    self.bm = BinanceSocketManager(self.binance_client)
    ticks_conn_key = self.bm.start_kline_socket(self.pair, self._rootine, interval=interval)
    orders_conn_key = self.bm.start_user_socket(self.track_orders)
    
    self.setup()
    self.bm.start()
    
    self.logger.info('TRADING BOT STARTED')

  def stop(self):
    self.bm.close()


  def place_real_order(self, order_type: OrderType, limit_price: float, qty: float):
    self.logger.info('[ORDER] New: {} qty {} at_price {}'.format(order_type, qty, limit_price))
    if order_type is OrderType.BUY:
      self.open_order = self.binance_client.order_limit_buy(symbol=self.pair, quantity=qty, price=limit_price)
    elif order_type is OrderType.SELL:
      self.open_order = self.binance_client.order_limit_sell(symbol=self.pair, quantity=qty, price=limit_price)
    else:
      self.logger.error('Unknow order type:', order_type)
      raise Exception('Unknow order type', order_type)
    print('end place_order', self.open_order)


  def place_fake_order(self, order_type: OrderType, limit_price: float, qty: float):
    if order_type is OrderType.BUY or order_type is OrderType.SELL:
      # self._open_postion(qty, limit_price)
      self.open_order = {
        'qty': qty,
        'price': limit_price,
        'type': order_type
      }
      
    else:
      self.logger.error('Unknow order type:', order_type)
      raise Exception('Unknow order type', order_type)

    self.logger.info('fake order placed')

  def place_order(self, order_type: OrderType, limit_price: float, order_by: OrderBy, value: float):
    qty = value
    if order_by == OrderBy.VALUE:
      qty = value/limit_price

    qty = round(qty, 1)
    limit_price = round(limit_price, self.precision)

    self.logger.info('[ORDER] new order: {} qty {} at_price {}'.format(order_type, qty,limit_price))
    self.place_fake_order(order_type, limit_price, qty)

  def track_orders(self, msg: any):
    # orders docs https://docs.binance.org/api-reference/dex-api/ws-streams.html
    self.logger.debug('track_orders: ', extra={'msg': msg})
    print('track_orders: ', msg['e'])
    if msg['e'] != 'executionReport' or msg['s'] != self.pair:
      print('not my order')
      return False

    print('new order filled', msg)
    if msg['X'] == 'NEW':
      print('NEW', msg)
      # self.logger.info('[ORDER] Created: id', msg['i'], msg['S'], msg['q'], 'for', msg['p'])
      self.logger.info('[ORDER] Created: id {} {} {} for {}'.format( msg['i'], msg['S'], msg['q'], msg['p']))
      self.open_order = True
      return True

    # TODO handle partial fills 'PartialFill'
    if msg['X'] == 'FullyFill':
      # update position
      if msg['S'] == 'BUY':
        self._open_postion(msg['z'], msg['p'])
      elif msg['S'] == 'SELL':
        self._close_position(msg['p'])
      self.order_execution_hook(msg)
      
  def _open_postion(self, qty: float, entry_price: float):
    self.position = {
      'qty': qty,
      'entry_price': entry_price
    }

    # self.logger.info('[POSITION] OPENED', self.position)
    self.logger.info('[POSITION] OPENED {}'.format(self.position))

  def _close_position(self, sold_at):
    returns = self.calc_roi(self.position['entry_price'], sold_at)
    new_capital = sold_at*self.position['qty']
    self.position = None
    self._capital = new_capital
    self.logger.info('[POSITION] CLOSED => sold at: {} with gains of {}'.format(sold_at, returns))
    self.logger.info('[POSITION] CLOSED => new capital {}'.format(self._capital))

  def calc_roi(self, entry_price, exit_price):
    return exit_price/entry_price - 1

  def get_position_returns(self):
    if self.position is None:
      raise Exception('get_position_returns')

    return self.calc_roi(self.position['entry_price'], self.last_price)
    # return self.last_price/self.position['entry_price'] - 1
  #region Logger

  def init_logger(self, save_to_file: bool = False):
    self.logger = logging.getLogger(self.name)
    self.logger.setLevel(logging.DEBUG)

    handler = logging.StreamHandler()
    formatter = logging.Formatter(logging.BASIC_FORMAT)
    handler.setFormatter(formatter)
    self.logger.addHandler(handler)

    supported_keys = [
      'asctime',
      'levelname',
      'filename',
      'lineno',
      'message',
      'name',
    ]
    log_format = lambda x: ['%({0:s})s'.format(i) for i in x]
    custom_json_format = ' '.join(log_format(supported_keys))

    if save_to_file == True:
      # all logs
      log_file_name = 'log.{}'.format(self.name)
      jsonLogHandler = logging.handlers.TimedRotatingFileHandler(log_file_name, when="midnight", interval=1)
      jsonLogHandler.suffix = "%Y-%m-%d"
      jsonLogFormater = jsonlogger.JsonFormatter(custom_json_format)
      jsonLogHandler.setFormatter(jsonLogFormater)
      self.logger.addHandler(jsonLogHandler)

    if save_to_file == True:
      # info logs
      info_log_file_name = 'info.{}'.format(self.name)
      jsonInfoLogFormater = jsonlogger.JsonFormatter(custom_json_format)
      jsonInfoLogHandler = logging.handlers.TimedRotatingFileHandler(info_log_file_name, when="midnight", interval=1)
      jsonInfoLogHandler.suffix = "%Y-%m-%d"
      jsonInfoLogHandler.setFormatter(jsonInfoLogFormater)
      jsonInfoLogHandler.setLevel(logging.INFO)
      self.logger.addHandler(jsonInfoLogHandler)
    
  def _rootine(self, msg):
    now = datetime.now()

    if self.last_tick_datetime is not None and now - self.last_tick_datetime < self.interval_timedelta:
      print('tick interval is less that 1m', now - self.last_tick_datetime)
      print('skip routine: not in interval')
      return False

    try:
      self.last_tick_datetime = now
      self.last_price = float(msg['k']['c'])

      self.track_fake_orders()

      self.rootine(msg)
    except Exception:
      self.logger.exception("Fatal error in rootine")


  def track_fake_orders(self):
    if self.open_order is None:
      return False

    self.logger.debug('check fake order status: {} {} current price {}'.format(self.open_order['type'], self.open_order['price'], self.last_price))
    if self.open_order['type'] is OrderType.BUY and self.last_price <= self.open_order['price']:
      self.logger.debug('yes fake buy')
      self._open_postion(self.open_order['qty'], self.last_price)
      self.order_execution_hook()
      self.open_order = None
      return True

    if self.open_order['type'] is OrderType.SELL and self.last_price >= self.open_order['price']:
      self.logger.debug('yes fake sell')
      self._close_position(self.last_price)
      self.order_execution_hook()
      self.open_order = None
      return True

    return False
      
      
      

  @abstractmethod
  def setup(self):
    pass

  @abstractmethod
  def rootine(self, msg):
    pass

  @abstractmethod
  def order_execution_hook(self):
    pass