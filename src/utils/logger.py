
#!/usr/bin/env python3
"""
DataTrust — Logging System
============================
Provides timestamped, colour-coded console + file logging.
"""

import logging
import sys
from datetime import datetime
from pathlib import Path


class DataTrustLogger:
    """Custom logger with console + file output."""

    COLORS = {
        "DEBUG": "\033[90m",      # grey
        "INFO": "\033[36m",       # cyan
        "WARNING": "\033[33m",    # yellow
        "ERROR": "\033[31m",      # red
        "CRITICAL": "\033[91m",   # bright red
        "SUCCESS": "\033[32m",    # green
        "RESET": "\033[0m",
    }

    def __init__(self, name="DataTrust", log_dir="logs"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        self.logger.handlers = []

        # Console handler (coloured)
        console = logging.StreamHandler(sys.stdout)
        console.setLevel(logging.INFO)
        console.setFormatter(self._ColorFormatter())
        self.logger.addHandler(console)

        # File handler
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_handler = logging.FileHandler(
            log_path / f"datatrust_{timestamp}.log", encoding="utf-8"
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(message)s",
            _ = "%Y-%m-%d %H:%M:%S",
        ))
        self.logger.addHandler(file_handler)

    class _ColorFormatter(logging.Formatter):
        """Adds colour codes to console output."""

        COLORS = {
            logging.DEBUG: "\033[90m",
            logging.INFO: "\033[36m",
            logging.WARNING: "\033[33m",
            logging.ERROR: "\033[31m",
            logging.CRITICAL: "\033[91m",
        }
        RESET = "\033[0m"

        def format(self, record):
            color = self.COLORS.get(record.levelno, self.RESET)
            timestamp = datetime.now().strftime("%H:%M:%S")
            return f"{color}[{timestamp}] {record.levelname:<8}{self.RESET} {record.getMessage()}"

    def info(self, msg):
        self.logger.info(msg)

    def debug(self, msg):
        self.logger.debug(msg)

    def warning(self, msg):
        self.logger.warning(msg)

    def error(self, msg):
        self.logger.error(msg)

    def critical(self, msg):
        self.logger.critical(msg)

    def success(self, msg):
        """Log a success message (uses INFO level with prefix)."""
        self.logger.info(f"\033[32m[OK]\033[0m {msg}")

    def header(self, msg):
        """Log a section header."""
        self.logger.info("=" * 60)
        self.logger.info(f"  {msg}")
        self.logger.info("=" * 60)

    def separator(self):
        self.logger.info("-" * 60)
