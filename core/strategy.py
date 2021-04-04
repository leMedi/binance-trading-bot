from abc import ABC, abstractmethod
from enum import Enum
from termcolor import cprint
from binance.websockets import BinanceSocketManager
from pythonjsonlogger import jsonlogger
import logging
import logging.handlers
import logging
import os
import sys

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
  interval = '1m'
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

    
  def run(self, interval: str = '1m'):
    self.interval = interval
    
    self.bm = BinanceSocketManager(self.binance_client)
    ticks_conn_key = self.bm.start_kline_socket(self.pair, self.rootine, interval=interval)
    orders_conn_key = self.bm.start_user_socket(self.track_orders)
    
    self.setup()
    self.bm.start()
    
    self.logger.info('TRADING BOT STARTED')


  def stop(self):
    self.bm.close()

  def place_order(self, order_type: OrderType, limit_price: float, order_by: OrderBy, value: float):

    qty = value
    if order_by == OrderBy.VALUE:
      qty = value/limit_price

    qty = round(qty, 1)
    limit_price = round(limit_price, self.precision)
    # self.logger.info('[ORDER] New:', order_type, 'qty', qty, 'at_price', limit_price)
    self.logger.info('[ORDER] New: {} qty {} at_price {}'.format(order_type, qty, limit_price))
    if order_type is OrderType.BUY:
      self.open_order = self.binance_client.order_limit_buy(symbol=self.pair, quantity=qty, price=limit_price)
    elif order_type is OrderType.SELL:
      self.open_order = self.binance_client.order_limit_sell(symbol=self.pair, quantity=value, price=limit_price)
    else:
      self.logger.error('Unknow order type:', order_type)
      raise Exception('Unknow order type', order_type)
      
    print('end place_order', self.open_order)

  def track_orders(self, msg: any):
    # orders docs https://docs.binance.org/api-reference/dex-api/ws-streams.html
    print('track_orders: ', msg)
    print('track_orders: ', msg['e'])
    if msg['e'] != 'executionReport' or msg['s'] != self.pair:
      print('not my order')
      return False

    print('track_orders 2', msg)
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
      qty: qty,
      entry_price: entry_price
    }

    # self.logger.info('[POSITION] OPENED', self.position)
    self.logger.info('[POSITION] OPENED {}'.format(self.position))

  def _close_position(self, sold_at):
    self.position = None
    self._capital = sold_at
    # self.logger.info('[POSITION] CLOSED', 'capital:', self._capital)
    self.logger.info('[POSITION] CLOSED', 'capital: {}'.format(self._capital))

  def get_position_returns(self):
    if self.position is None:
      raise Exception()

    return self.last_price/self.position['entry_price'] - 1

  #region Logger

  def init_logger(self, save_to_file: bool = False):
    self.logger = logging.getLogger()

    handler = logging.StreamHandler()
    formatter = logging.Formatter(logging.BASIC_FORMAT)
    handler.setFormatter(formatter)
    self.logger.addHandler(handler)

    if(save_to_file):
      supported_keys = [
        'asctime',
        'levelname',
        'filename',
        'lineno',
        'message',
        'name',
      ]

      log_format = lambda x: ['%({0:s})s'.format(i) for i in x]
      custom_format = ' '.join(log_format(supported_keys))
      jsonLogHandler = logging.handlers.TimedRotatingFileHandler(os.environ.get("LOGFILE", "./yourapp.log"), when="m",interval=1,backupCount=2)
      # jsonLogHandler = logging.handlers.WatchedFileHandler(os.environ.get("LOGFILE", "./yourapp.log"))
      jsonLogFormater = jsonlogger.JsonFormatter(custom_format)
      jsonLogHandler.setFormatter(jsonLogFormater)
      self.logger.addHandler(jsonLogHandler)
    

  # def log(self, log_type: LogType = LogType.INFO, *args):
  #   _prefix = '[+]'
  #   _color = 'green'
  #   _attrs = []
  #   _file = sys.stdout
  #   if log_type is LogType.ERROR:
  #     _prefix = '[!]'
  #     _color= 'red'
  #     _attrs = ['bold']
  #     _file = sys.stderr

  #   _prefix += ' ' + self.name + ' ' + self.pair 
  #   msg = _prefix + ' ' +  ' '.join(map(str, args))
  #   cprint(msg, _color, attrs=_attrs, file=_file)

  # def info(self, *args):
  #   self.log(LogType.INFO, *args)

  # def error(self, *args):
  #   self.log(LogType.ERROR, *args)
  #endregion

  def _rootine(self, msg):
    self.last_price = float(msg['k']['c'])
    self.rootine(msg)


  @abstractmethod
  def setup(self):
    pass

  @abstractmethod
  def rootine(self, msg):
    pass

  @abstractmethod
  def order_execution_hook(self, order):
    pass