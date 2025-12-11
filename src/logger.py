"""
Logging configuration for CraftLauncher
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
import platform
import os


def get_log_dir() -> Path:
    """Get the log directory based on OS."""
    system = platform.system()
    
    if system == "Windows":
        base = Path(os.environ.get("APPDATA", Path.home()))
    elif system == "Darwin":  # macOS
        base = Path.home() / "Library" / "Application Support"
    else:  # Linux
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    
    log_dir = base / "CraftLauncher" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def setup_logger(name: str = "CraftLauncher") -> logging.Logger:
    """Set up and return the application logger."""
    logger = logging.getLogger(name)
    
    # Avoid adding handlers multiple times
    if logger.handlers:
        return logger
    
    logger.setLevel(logging.DEBUG)
    
    # Log format
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # File handler with rotation (5 MB max, keep 3 backups)
    log_file = get_log_dir() / "launcher.log"
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=3,
        encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Console handler (less verbose)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(
        fmt="%(levelname)s: %(message)s"
    ))
    logger.addHandler(console_handler)
    
    logger.info(f"Log file: {log_file}")
    
    return logger


# Global logger instance
logger = setup_logger()

