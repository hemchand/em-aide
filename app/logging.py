import logging
from datetime import datetime
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")

class ETFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        dt = datetime.fromtimestamp(record.created, ET)
        if datefmt:
            return dt.strftime(datefmt)
        return dt.strftime("%Y-%m-%d %H:%M:%S %Z")

def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger  # avoid double handlers

    logger.setLevel(logging.INFO)

    handler = logging.StreamHandler()
    formatter = ETFormatter(
        fmt="[%(asctime)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S %Z"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.propagate = False

    return logger
