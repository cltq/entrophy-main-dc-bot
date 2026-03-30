import collections
import logging
from collections import deque
from typing import Any, Optional

LOG_BUFFER_MAX: int = 500
LOG_BUFFER: deque[str] = collections.deque(maxlen=LOG_BUFFER_MAX)


class BufferHandler(logging.Handler):
    def __init__(self, fmt: Optional[logging.Formatter] = None) -> None:
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
