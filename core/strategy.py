from abc import ABC, abstractmethod
from datetime import datetime, timedelta

from enum import Enum
from termcolor import cprint
from core.utils import round_down
from binance.websockets import BinanceSocketManager
from pythonjsonlogger import jsonlogger
import logging.handlers
import pickle
import logging
import json
import os

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
  interval = None
  last_tick_datetime = None
  open_order = None
  position = None

  price_precision=5
  qty_precision=5

  order_history = list()
  last_price = None
  

  def __init__(self, name, binance_client, pair: str, initial_capital: float, price_precision = 5, qty_precision = 5) -> None:
    self.name = name
    self.binance_client = binance_client
    self.pair = pair
    self.initial_capital = initial_capital
    self._capital = initial_capital

    self.price_precision = price_precision
    self.qty_precision = qty_precision

    self.checkpoint_file = os.path.join(os.getcwd(), 'checkpoints', "{}_checkpoint.pickle".format(name))

    self.init_logger(save_to_file=True)
    self.load_checkpoint()

  def save_checkpoint(self):
    self.logger.debug("checkpoint: saving")
    try:
      checkpoint = {
        'position': self.position,
        'open_order': self.open_order
      }
      with open(self.checkpoint_file, 'w') as outfile:
        pickle.dump(checkpoint, outfile)
    except:
      self.logger.error("checkpoint: error loading {}".format(self.checkpoint_file))
      self.logger.exception("File not accessible")


  def load_checkpoint(self):
    self.logger.info('loading check point {}'.format(self.checkpoint_file))
    try:
      with open(self.checkpoint_file) as json_file:
        checkpoint = pickle.load(json_file)
        self.position = checkpoint['position']
        self.open_order = checkpoint['open_order']
        self.logger.info('checkpoint loaded - position: {}'.format(self.position))
        self.logger.info('checkpoint loaded - open_order: {}'.format(self.open_order))
    except IOError:
        self.logger.error("checkpoint: error loading {}".format(self.checkpoint_file))
        self.logger.exception("File not accessible")
    # self._open_postion(40.2, 2.48504)
    # self.place_order(OrderType.SELL, 2.50989, OrderBy.QUANTITY, 40.2)
    
  def run(self, interval: str = '1m'):
    self.interval = interval
    
    self.bm = BinanceSocketManager(self.binance_client)
    _interval = '1m'
    ticks_conn_key = self.bm.start_kline_socket(self.pair, self._rootine, interval=_interval)
    orders_conn_key = self.bm.start_user_socket(self.track_orders)
    
    self.setup()
    self.bm.start()
    
    self.logger.info('TRADING BOT STARTED')

  def stop(self):
    self.bm.close()

  def place_real_order(self, order_type: OrderType, limit_price: float, qty: float):
    self.logger.info('[ORDER] New: {} qty {} at_price {}'.format(order_type, qty, limit_price))
    if order_type is OrderType.BUY:
      order = self.binance_client.order_limit_buy(symbol=self.pair, quantity=qty, price=limit_price)
      # self.update_order(None)
    elif order_type is OrderType.SELL:
      order = self.binance_client.order_limit_sell(symbol=self.pair, quantity=qty, price=limit_price)
      # self.update_order(None)
    else:
      self.logger.error('Unknow order type:', order_type)
      raise Exception('Unknow order type', order_type)
    logging.info('order placed: {}'.format(json.dumps(self.open_order)))
    print('end place_order', self.open_order)

  
  # TODO: function to format binance order to my orders


  def place_fake_order(self, order_type: OrderType, limit_price: float, qty: float):
    if order_type is OrderType.BUY or order_type is OrderType.SELL:
      # self.open_order = {
      #   'qty': qty,
      #   'price': limit_price,
      #   'type': order_type
      # }
      self.update_order({
        'qty': qty,
        'price': limit_price,
        'type': order_type
      })

      
    else:
      self.logger.error('Unknow order type:', order_type)
      raise Exception('Unknow order type', order_type)

    self.logger.info('fake order placed')

  def place_order(self, order_type: OrderType, limit_price: float, order_by: OrderBy, value: float):
    qty = value
    if order_by == OrderBy.VALUE:
      qty = value/limit_price

    qty = round_down(qty, self.qty_precision)
    limit_price = round_down(limit_price, self.price_precision)

    self.logger.info('[ORDER] new order: {} qty {} at_price {}'.format(order_type, qty,limit_price))
    # self.place_fake_order(order_type, limit_price, qty)
    self.place_real_order(order_type, limit_price, qty)

  def track_orders(self, msg: any):
    # orders docs https://docs.binance.org/api-reference/dex-api/ws-streams.html
    self.logger.debug('track_orders: {}'.format(json.dumps(msg)))
    print('track_orders - STATUS', msg['e'])
    if msg['e'] != 'executionReport' or msg['s'] != self.pair:
      print('not my order')
      return False
    
    
    self.logger.debug('get till here: {}'.format(msg['X']))

    if msg['X'] == 'NEW':
      #  CHECK IF "X": "Ack",
      print('NEW', msg)
      # self.logger.info('[ORDER] Created: id', msg['i'], msg['S'], msg['q'], 'for', msg['p'])
      self.logger.info('[ORDER] Created: id {} {} {} for {}'.format( msg['i'], msg['S'], msg['q'], msg['p']))
      self.update_order({
        'id': msg['i'],
        'qty': float(msg['q']),
        'price': float(msg['p']),
        'type': OrderType.BUY if msg['S'] == 'BUY' else OrderType.SELL
      })
      # self.open_order = {
      #   'id': msg['i'],
      #   'qty': float(msg['q']),
      #   'price': float(msg['p']),
      #   'type': OrderType.BUY if msg['S'] == 'BUY' else OrderType.SELL
      # }
      
      return True

    # TODO handle partial fills 'PartialFill'
    print('new order filled', msg)
    # if msg['X'] == 'FullyFill':
    # if msg['x'] == 'Trade' and msg['X'] == 'FILLED':
    if msg['x'] == 'TRADE' and msg['X'] == 'FILLED':
      print('order is here')
      # update position
      if msg['S'] == 'BUY':
        self._open_postion(float(msg['z']), float(msg['p']))
      elif msg['S'] == 'SELL':
        self._close_position(float(msg['p']))
      else:
        self.logger.exception('what the fuck is this order')
      self.update_order(None)
      # self.open_order = None
      print('track_orders filled', 'self.open_order', self.open_order)
      print('track_orders filled', 'self.position', self.position)
      self.order_execution_hook(msg)
      
  def _open_postion(self, qty: float, entry_price: float):
    self.position = {
      'qty': qty,
      'entry_price': entry_price
    }

    # self.logger.info('[POSITION] OPENED', self.position)
    self.logger.info('[POSITION] OPENED {}'.format(self.position))
    self.save_checkpoint()

  def _close_position(self, sold_at):
    returns = self.calc_roi(self.position['entry_price'], sold_at)
    new_capital = sold_at*self.position['qty']
    self.position = None
    self._capital = new_capital
    self.logger.info('[POSITION] CLOSED => sold at: {} with gains of {}'.format(sold_at, returns))
    self.logger.info('[POSITION] CLOSED => new capital {}'.format(self._capital))
    self.save_checkpoint()

  def update_order(self, order):
    self.open_order = order
    self.save_checkpoint()
    # {
    #   'id': msg['i'],
    #   'qty': float(msg['q']),
    #   'price': float(msg['p']),
    #   'type': OrderType.BUY if msg['S'] == 'BUY' else OrderType.SELL
    # }

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

    if self.last_tick_datetime is not None and now - self.last_tick_datetime < self.interval:
      print('tick interval is less than', self.interval, ':',now - self.last_tick_datetime)
      print('skip routine: not in interval')
      return False

    if self.position != None:
      self.logger.debug('postion is open - qty: {} returns: {}'.format(self.position['qty'], self.get_position_returns()))

    try:
      self.last_tick_datetime = now
      self.last_price = float(msg['k']['c'])

      # self.track_fake_orders()

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
      # self.open_order = None
      self.update_order(None)
      self.order_execution_hook()
      return True

    if self.open_order['type'] is OrderType.SELL and self.last_price >= self.open_order['price']:
      self.logger.debug('yes fake sell')
      self._close_position(self.last_price)
      # self.open_order = None
      self.update_order(None)
      self.order_execution_hook(msg={})
      return True

    return False
      
      
      

  @abstractmethod
  def setup(self):
    pass

  @abstractmethod
  def rootine(self, msg):
    pass

  @abstractmethod
  def order_execution_hook(self, msg):
    pass