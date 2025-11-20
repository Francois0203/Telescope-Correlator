"""I/O helpers for reading and writing signals.

Supports reading numpy .npy and CSV text files. Keep this small and explicit so
unit tests can exercise simple file formats.
"""
from __future__ import annotations

from typing import Sequence
import numpy as np
import os


def load_signal(path: str) -> np.ndarray:
    """Load a 1-D signal from a file.

    Supports:
    - .npy (numpy binary)
    - .csv or .txt (comma/whitespace separated values)
    """
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    _, ext = os.path.splitext(path)
    ext = ext.lower()
    if ext == ".npy":
        return np.load(path)
    else:
        return np.loadtxt(path, delimiter=None)


def save_signal(path: str, arr: Sequence[float]) -> None:
    """Save a 1-D signal to .npy format (preferred for tests).
    """
    np.save(path, np.asanyarray(arr, dtype=float))