import logging
import logging.handlers
import os
from pythonjsonlogger import jsonlogger



 
logger.warning('this a serious warning', extra=dict(x=1))
logger.info('hello')

try:
    exit(main())
except Exception:
    logging.exception("Exception in main()")
    exit(1)