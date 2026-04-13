"""
Centralized logging configuration.
Uses python-json-logger for structured logging.
"""

import logging
import sys
from pythonjsonlogger import jsonlogger
from .config import config


def setup_logger(name: str = "ai_companion") -> logging.Logger:
    """Configure and return a logger with JSON formatting."""
    logger = logging.getLogger(name)

    log_level = getattr(logging, config.logging.LEVEL.upper(), logging.INFO)
    logger.setLevel(log_level)

    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()

    # JSON handler for structured logging
    json_handler = logging.StreamHandler(sys.stdout)
    json_handler.setFormatter(
        jsonlogger.JsonFormatter(fmt="%(timestamp)s %(level)s %(name)s %(message)s")
    )
    logger.addHandler(json_handler)

    return logger


# Global logger instance
logger = setup_logger()
