from __future__ import annotations
import logging, sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

def setup_logging(log_dir: str | Path, name: str = "behav-id", level: int = logging.INFO) -> logging.Logger:
    """
    Setup logging configuration
    :param log_dir: Directory where log files will be stored
    :param name: Name of log file
    :param level: Default logging level
    :return: Logger object
    """

    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False

    if not logger.handlers:
        fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
        fh = RotatingFileHandler(log_dir / "app.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8")
        fh.setFormatter(fmt)
        sh = logging.StreamHandler(sys.stdout)
        sh.setFormatter(fmt)
        logger.addHandler(fh)
        logger.addHandler(sh)
    return logger
