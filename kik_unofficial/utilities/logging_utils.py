import logging
import sys

from kik_unofficial.client import KikClient

# turn on logging with basic configuration
def set_up_basic_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(logging.Formatter(KikClient.log_format()))
    logger.addHandler(stream_handler)