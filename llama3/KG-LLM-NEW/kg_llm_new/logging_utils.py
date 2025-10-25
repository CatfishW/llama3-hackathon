"""Logging setup helpers."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional


def setup_logging(logs_dir: Path, level: int = logging.INFO) -> None:
    """Configure application logging with console and file handlers."""

    logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = logs_dir / "kg_llm_new.log"

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Avoid duplicate handlers if setup is invoked twice
    if not any(isinstance(h, logging.FileHandler) and h.baseFilename == str(log_path) for h in root_logger.handlers):
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    if not any(isinstance(h, logging.StreamHandler) for h in root_logger.handlers):
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        root_logger.addHandler(stream_handler)


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Return a module-level logger."""

    return logging.getLogger(name or "kg_llm_new")
