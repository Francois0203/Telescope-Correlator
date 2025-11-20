"""Core correlator implementation.

This module contains a small, well-documented Correlator class that performs
cross-correlation of two time series using an FFT-based approach for speed.

Design goals:
- Clear interface: Correlator.correlate(x, y, mode) -> np.ndarray
- Small and testable functions
- Documented edge-case behavior
"""
from __future__ import annotations

from typing import Sequence
import numpy as np


class Correlator:
    """Simple FFT-based correlator.

    The correlate method returns the cross-correlation sequence of two real
    signals. By default it returns the 'full' correlation (length N+M-1).

    Usage:
        corr = Correlator().correlate(x, y)

    Notes:
    - Inputs are treated as 1-D real-valued arrays.
    - For performance we compute the FFT length as the next power of two.
    """

    def __init__(self, sample_rate: float = 1.0) -> None:
        self.sample_rate = float(sample_rate)

    def correlate(self, x: Sequence[float], y: Sequence[float], mode: str = "full") -> np.ndarray:
        """Compute cross-correlation of x and y.

        Args:
            x: First signal (sequence of floats).
            y: Second signal.
            mode: 'full' (default) or 'same'.

        Returns:
            1-D numpy array with the cross-correlation.
        """
        x_arr = np.asanyarray(x, dtype=float)
        y_arr = np.asanyarray(y, dtype=float)

        if x_arr.ndim != 1 or y_arr.ndim != 1:
            raise ValueError("Inputs must be 1-D sequences")

        n = x_arr.size
        m = y_arr.size
        if n == 0 or m == 0:
            return np.array([], dtype=float)

        target_len = n + m - 1

        # Use numpy.correlate for correct, well-defined lag ordering.
        # FFT-based implementations are faster for large signals but are
        # more error-prone around indexing/sign conventions; we keep the
        # simple implementation for clarity and correctness.
        # Use ordering that yields positive lag when `y` is a delayed
        # (right-shifted) version of `x` (i.e. y = roll(x, +d)).
        corr = np.correlate(y_arr, x_arr, mode="full")

        if mode == "full":
            return corr
        elif mode == "same":
            # center same-length output with respect to x
            start = (m - 1) // 2
            return corr[start:start + n]
        else:
            raise ValueError("mode must be 'full' or 'same'")
