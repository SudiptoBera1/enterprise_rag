import logging
from pythonjsonlogger.json import JsonFormatter


def setup_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Avoid duplicate handlers during reload/import cycles.
    if logger.handlers:
        return

    logHandler = logging.StreamHandler()

    formatter = JsonFormatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s"
    )

    logHandler.setFormatter(formatter)
    logger.addHandler(logHandler)
