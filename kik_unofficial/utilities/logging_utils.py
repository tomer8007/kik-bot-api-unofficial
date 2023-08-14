import logging
import sys

# turn on logging with basic configuration
def set_up_basic_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(logging.Formatter(log_format()))
    logger.addHandler(stream_handler)

def log_format():
    return '[%(asctime)-15s] %(levelname)-6s (thread %(threadName)-10s): %(message)s'