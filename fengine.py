"""
fengine.py
FFT-based channelisation for radio telescope signals.
"""
import numpy as np
import logging
from typing import Any

logger = logging.getLogger(__name__)

class FEngine:
    """
    Frequency channelisation using FFT.
    TODO: Add Polyphase Filter Bank (PFB) support.
    """
    def __init__(self, fft_size: int):
        self.fft_size = fft_size
        logger.info(f"FEngine initialized with FFT size {fft_size}.")

    def channelise(self, signals: np.ndarray) -> np.ndarray:
        """
        Apply FFT to time-domain signals.
        Args:
            signals (np.ndarray): Shape (num_antennas, frame_size)
        Returns:
            np.ndarray: Shape (num_antennas, fft_size), complex64
        """
        logger.debug("Performing FFT channelisation.")
        return np.fft.fft(signals, n=self.fft_size, axis=1).astype(np.complex64) 