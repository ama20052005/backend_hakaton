import logging
from pathlib import Path
from typing import Any


try:
    from loguru import logger as logger
except ImportError:
    class CompatibleLogger:
        def __init__(self):
            self._logger = logging.getLogger("demography-api")
            self._logger.setLevel(logging.INFO)
            self._logger.propagate = False
            if not self._logger.handlers:
                handler = logging.StreamHandler()
                handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
                self._logger.addHandler(handler)

        def remove(self):
            for handler in list(self._logger.handlers):
                self._logger.removeHandler(handler)

        def add(self, sink: Any, level: str = "INFO", rotation: str = None):
            handler = (
                logging.StreamHandler(sink)
                if hasattr(sink, "write")
                else logging.FileHandler(self._prepare_file(sink))
            )
            handler.setLevel(getattr(logging, level.upper(), logging.INFO))
            handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
            self._logger.addHandler(handler)

        def _prepare_file(self, sink: str) -> str:
            path = Path(sink)
            path.parent.mkdir(parents=True, exist_ok=True)
            return str(path)

        def info(self, message: str):
            self._logger.info(message)

        def warning(self, message: str):
            self._logger.warning(message)

        def error(self, message: str):
            self._logger.error(message)

    logger = CompatibleLogger()
