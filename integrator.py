"""
integrator.py
Time-averaging (integration) for radio telescope visibilities.
"""
import numpy as np
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class Integrator:
    """
    Integrates (averages) visibilities over multiple frames.
    """
    def __init__(self, n_integrate: int):
        self.n_integrate = n_integrate
        self._sum = None
        self._count = 0
        logger.info(f"Integrator initialized for {n_integrate} frames.")

    def add(self, vis: np.ndarray) -> Optional[np.ndarray]:
        """
        Add visibilities for integration. Returns integrated result if ready.
        Args:
            vis (np.ndarray): Shape (num_ant, num_ant, n_freq)
        Returns:
            Optional[np.ndarray]: Integrated visibilities or None if not ready.
        """
        if self._sum is None:
            self._sum = np.zeros_like(vis, dtype=np.complex64)
        self._sum += vis
        self._count += 1
        logger.debug(f"Added frame {self._count}/{self.n_integrate} to integrator.")
        if self._count >= self.n_integrate:
            result = self._sum / self._count
            self._sum = None
            self._count = 0
            logger.info("Integration complete.")
            return result
        return None 