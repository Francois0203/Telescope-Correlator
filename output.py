"""
output.py
Handles saving visibilities and metadata to HDF5 files.
"""
import os
import h5py
import numpy as np
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class OutputWriter:
    """
    Saves visibilities and metadata to HDF5 files in ./output.
    """
    def __init__(self, output_dir: str = "./output"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        logger.info(f"OutputWriter will save files to {self.output_dir}")

    def save(self, vis: np.ndarray, freqs: np.ndarray, metadata: Dict[str, Any], filename: str):
        """
        Save visibilities and metadata to an HDF5 file.
        Args:
            vis (np.ndarray): Shape (num_ant, num_ant, n_freq)
            freqs (np.ndarray): Frequency axis (n_freq,)
            metadata (dict): Metadata to store
            filename (str): Output filename (no path)
        """
        path = os.path.join(self.output_dir, filename)
        logger.info(f"Saving visibilities to {path}")
        with h5py.File(path, "w") as f:
            f.create_dataset("visibilities", data=vis)
            f.create_dataset("frequencies", data=freqs)
            meta_grp = f.create_group("metadata")
            for k, v in metadata.items():
                meta_grp.attrs[k] = v
        logger.info("File saved successfully.") 