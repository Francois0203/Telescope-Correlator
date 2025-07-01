"""
xengine.py
Cross-correlation (X-engine) for radio telescope signals.
"""
import numpy as np
import logging
from typing import Any

logger = logging.getLogger(__name__)

class XEngine:
    """
    Computes full cross-correlation (auto + cross) between antenna FFT outputs.
    """
    def __init__(self, num_antennas: int):
        self.num_antennas = num_antennas
        logger.info(f"XEngine initialized for {num_antennas} antennas.")

    def correlate(self, fft_data: np.ndarray) -> np.ndarray:
        """
        Compute complex visibilities (auto and cross) for all antenna pairs.
        Args:
            fft_data (np.ndarray): Shape (num_antennas, n_freq)
        Returns:
            np.ndarray: Shape (num_antennas, num_antennas, n_freq), complex64
        """
        logger.debug("Computing visibilities (cross-correlation matrix).")
        num_ant, n_freq = fft_data.shape
        vis = np.zeros((num_ant, num_ant, n_freq), dtype=np.complex64)
        for i in range(num_ant):
            for j in range(num_ant):
                vis[i, j] = fft_data[i] * np.conj(fft_data[j])
        return vis 