# Unified logger for the wuwacalc project
import logging
import os
from logging.handlers import RotatingFileHandler

# Determine log directory (relative to project root)
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE = os.path.join(LOG_DIR, "wuwacalc.log")

# Create logger instance
logger = logging.getLogger("wuwacalc")
logger.setLevel(logging.INFO)

# Prevent duplicate handlers if this module is reloaded
if not logger.handlers:
    # File handler with rotation (5 MB per file, keep 5 backups)
    file_handler = RotatingFileHandler(LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8")
    file_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # Console handler for development
    console_handler = logging.StreamHandler()
    console_formatter = logging.Formatter("%(levelname)s - %(message)s")
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

# Export the logger for import elsewhere
__all__ = ["logger"]
