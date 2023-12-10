import logging
import os.path
import sys
from logging.handlers import TimedRotatingFileHandler

from colorama import Fore, Style
import datetime


# turn on logging with basic configuration
def set_up_basic_logging(log_level, logger_name, log_file_path, enable_console_output=True):
    """
    Set up basic logging using CustomLogger.

    Args:
        log_level (int): The logging level (1=DEBUG, 2=INFO, etc.).
        logger_name (str): The name of the logger.
        log_file_path (str): If a path is given a TimeRotated log file will be created.
    """
    
    return CustomLogger(log_level, logger_name, log_file_path, enable_console_output)


class ColoredFormatter(logging.Formatter):
    """
        Custom formatter for logging messages with colors.

        Attributes:
            COLOR_CODES (dict): Mapping of logging levels to their respective color codes.
    """

    COLOR_CODES = {
        logging.DEBUG: Fore.CYAN,
        logging.INFO: Fore.GREEN,
        logging.WARNING: Fore.YELLOW,
        logging.ERROR: Fore.RED,
        logging.CRITICAL: Fore.MAGENTA,
    }

    def format(self, record):
        """
               Format the specified record as text.

               Args:
                   record (logging.LogRecord): The record to be formatted.

               Returns:
                   str: The formatted record with colors and icons.
               """
        level_color = self.COLOR_CODES.get(record.levelno, '')
        time = datetime.datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')
        reset = Style.RESET_ALL
        if record.levelno == logging.DEBUG:
            level_icon = f'[{Style.BRIGHT}{Fore.LIGHTCYAN_EX}^{reset}]'
            level_name = 'DEBUG'
            highlight_color = f'{Style.BRIGHT}{Fore.LIGHTCYAN_EX}'
        elif record.levelno == logging.INFO:
            level_icon = f'[{Style.BRIGHT}{Fore.LIGHTGREEN_EX}+{reset}]'
            level_name = 'INFO'
            highlight_color = f'{Style.BRIGHT}{Fore.LIGHTGREEN_EX}'
        elif record.levelno == logging.WARNING:
            level_icon = f'[{Style.BRIGHT}{Fore.LIGHTYELLOW_EX}!{reset}]'
            level_name = 'WARNING'
            highlight_color = f'{Style.BRIGHT}{Fore.LIGHTYELLOW_EX}'
        elif record.levelno == logging.ERROR:
            level_icon = f'[{Style.BRIGHT}{Fore.LIGHTRED_EX}#{reset}]'
            level_name = 'ERROR'
            highlight_color = f'{Style.BRIGHT}{Fore.LIGHTRED_EX}'
        elif record.levelno == logging.CRITICAL:
            level_icon = f'[{Style.BRIGHT}{Fore.LIGHTMAGENTA_EX}*{reset}]'
            level_name = 'CRITICAL'
            highlight_color = f'{Style.BRIGHT}{Fore.LIGHTMAGENTA_EX}'
        else:
            level_icon = ''
            level_name = ''
            highlight_color = ''
        message = super().format(record)
        for word in message.split():
            if word.startswith('<<') and word.endswith('>>'):
                message = message.replace(word, f'{highlight_color}{word[2:-2]}{reset}')
        return f'{time} {level_color}{level_name}:{reset} {level_icon} [Thread-{record.thread}:{record.threadName}] {message.replace(level_name + ": ", "")}'


class CustomLogger:
    """
    Custom logger with colored console output and file logging.

    Attributes:
        logger (logging.Logger): The underlying logger instance.
    """

    def __init__(self, log_level, logger_name, log_file_path, enable_console_output=True):
        """
           Initialize the custom logger.

           Args:
               log_level (int): The logging level (1=DEBUG, 2=INFO, etc.).
               logger_name (str): The name of the logger.
               log_file_path (str): Full path to log file.
        """
        self.logger = logging.getLogger(logger_name)
        level_mapping = {
            1: logging.DEBUG,
            2: logging.INFO,
            3: logging.WARNING,
            4: logging.ERROR,
            5: logging.CRITICAL
        }

        self.logger.setLevel(level_mapping.get(log_level, logging.INFO))

        console_handler = logging.StreamHandler()
        console_handler.setLevel(level_mapping.get(log_level, logging.INFO))

        formatter = ColoredFormatter('%(message)s')
        console_handler.setFormatter(formatter)

        if log_file_path:
            log_dir = os.path.dirname(log_file_path)
            if not os.path.exists(log_dir):
                try:
                    os.makedirs(log_dir)
                except OSError as e:
                    print(f"Could not create log directory: {str(e)}")

            file_handler = TimedRotatingFileHandler(
                log_file_path, when="midnight", backupCount=7
            )

            file_handler.setLevel(level_mapping.get(log_level, logging.INFO))
            file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s [%(thread)d/%(threadName)s]: %(message)s'))

            self.logger.addHandler(file_handler)

        if enable_console_output:
            self.logger.addHandler(console_handler)

    def info(self, msg, *args, **kwargs):
        self.logger.info(msg, *args, **kwargs)

    def debug(self, msg, *args, **kwargs):
        self.logger.debug(msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        self.logger.warning(msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        self.logger.error(msg, *args, **kwargs)

    def critical(self, msg, *args, **kwargs):
        self.logger.critical(msg, *args, **kwargs)