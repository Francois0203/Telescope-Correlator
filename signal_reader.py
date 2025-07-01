"""
signal_reader.py
Simulates complex time-domain signals for multiple antennas.
"""
import numpy as np
import logging
from typing import Tuple, List

logger = logging.getLogger(__name__)

class SignalReader:
    """
    Simulates complex time-domain signals for a set of antennas.
    TODO: Add real data ingestion via UDP sockets (from ADC/FPGA).
    """
    def __init__(self, num_antennas: int, sample_rate: float, frame_size: int, frequencies: List[float]):
        self.num_antennas = num_antennas
        self.sample_rate = sample_rate
        self.frame_size = frame_size
        self.frequencies = frequencies
        self.t = np.arange(frame_size) / sample_rate
        logger.info(f"SignalReader initialized for {num_antennas} antennas.")

    def read(self) -> np.ndarray:
        """
        Simulate a frame of complex time-domain data for all antennas.
        Returns:
            np.ndarray: Shape (num_antennas, frame_size), dtype=complex64
        """
        signals = np.zeros((self.num_antennas, self.frame_size), dtype=np.complex64)
        for i, freq in enumerate(self.frequencies):
            phase = np.random.uniform(0, 2 * np.pi)
            signals[i] = np.exp(1j * (2 * np.pi * freq * self.t + phase)).astype(np.complex64)
        logger.debug("Simulated signals generated.")
        return signals 