import collections
import logging
from typing import Deque

# Simple in-memory ring buffer for recent log lines
LOG_BUFFER_MAX = 500
LOG_BUFFER: Deque[str] = collections.deque(maxlen=LOG_BUFFER_MAX)


class BufferHandler(logging.Handler):
    def __init__(self, fmt=None):
        super().__init__()
        if fmt is None:
            fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
        self.setFormatter(fmt)

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            LOG_BUFFER.append(msg)
        except Exception:
            self.handleError(record)
