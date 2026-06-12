"""Logging a archivo rotativo — para poder depurar en cualquier PC sin ver la consola."""
import logging
import os
from logging.handlers import RotatingFileHandler

from config import BASE_DIR

LOG_PATH = os.path.join(BASE_DIR, "tutor.log")
log = logging.getLogger("tutor")
_configured = False


def setup_logging():
    """Configura el log a fichero (1 MB x 3) + consola. Idempotente."""
    global _configured
    if _configured:
        return
    _configured = True
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")

    file_handler = RotatingFileHandler(LOG_PATH, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    file_handler.setFormatter(fmt)
    console = logging.StreamHandler()
    console.setFormatter(fmt)

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    if not any(isinstance(h, RotatingFileHandler) for h in root.handlers):
        root.addHandler(file_handler)
        root.addHandler(console)
    log.info("Logging iniciado -> %s", LOG_PATH)
