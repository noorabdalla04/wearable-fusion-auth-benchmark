"""Reproducibility utilities: global seeding, config loading, run logging.

Every experiment script starts by calling `set_seed(cfg["seed"])` and
`get_logger(__name__)` so that runs are deterministic and traceable.
"""
from __future__ import annotations
import logging
import os
import random
from pathlib import Path

import numpy as np
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]


def load_config(path: str | os.PathLike | None = None) -> dict:
    """Load the global config.yaml (repo root by default)."""
    path = Path(path) if path else REPO_ROOT / "config.yaml"
    with open(path) as fh:
        return yaml.safe_load(fh)


def set_seed(seed: int) -> int:
    """Seed Python and NumPy RNGs. Returns the seed for logging."""
    random.seed(seed)
    np.random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    return seed


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Console logger with a consistent, timestamped format."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        h = logging.StreamHandler()
        h.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
        logger.addHandler(h)
        logger.setLevel(level)
    return logger
