from typing import Any
import json
import logging
import sys

def setup_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter(
            '%(asctime)s | %(name)s | %(levelname)s | %(message)s'
        )
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger

log = setup_logger("byte_social_agent")

def log_event(event_name: str, payload: dict[str, Any]):
    log.info(f"EVENT: {event_name} | PAYLOAD: {json.dumps(payload)}")
