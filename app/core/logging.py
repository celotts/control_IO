import logging
import sys

from pythonjsonlogger import jsonlogger


def setup_logging():
    logger = logging.getLogger()
    logger.handlers = []
    handler = logging.StreamHandler(sys.stdout)
    formatter = jsonlogger.JsonFormatter(
        "%(asctime)s %(name)s %(levelname)s %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger
