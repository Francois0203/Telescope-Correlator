"""Correlator configuration."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import numpy as np
import yaml


@dataclass
class Config:
    # Array
    n_ants: int = 4
    ant_radius: float = 10.0           # metres, for auto-generated circular array

    # F-engine
    n_channels: int = 256              # FFT size — must be a power of 2
    window: str = "hanning"            # rectangular / hanning / hamming / blackman
    integration_time: float = 1.0      # seconds per output visibility

    # Signal
    sample_rate: float = 1024.0        # Hz
    center_freq: float = 1.42e9        # Hz  (HI line default)

    # Input
    mode: str = "simulate"             # "simulate" or "file"
    input_file: str = ""               # path to .npy file  (mode=file only)
    duration: float = 10.0             # seconds  (mode=simulate only)
    snr: float = 20.0                  # dB       (mode=simulate only)

    # Output
    output_dir: str = "/workspace/outputs"
    output_format: str = "npy"         # npy / hdf5 / fits

    def validate(self):
        if self.n_ants < 2:
            raise ValueError("n_ants must be >= 2")
        if self.n_channels < 2 or (self.n_channels & (self.n_channels - 1)) != 0:
            raise ValueError("n_channels must be a power of 2 (e.g. 64, 128, 256, 512, 1024)")
        if self.window not in ("rectangular", "hanning", "hamming", "blackman"):
            raise ValueError("window must be: rectangular, hanning, hamming, or blackman")
        if self.mode not in ("simulate", "file"):
            raise ValueError("mode must be 'simulate' or 'file'")
        if self.mode == "file" and not self.input_file:
            raise ValueError("input_file must be set when mode='file'")
        if self.output_format not in ("npy", "hdf5", "fits"):
            raise ValueError("output_format must be: npy, hdf5, or fits")

    def ant_positions(self) -> np.ndarray:
        """Return (n_ants, 2) array of antenna positions on a uniform circle."""
        angles = np.linspace(0, 2 * np.pi, self.n_ants, endpoint=False)
        return np.stack([self.ant_radius * np.cos(angles),
                         self.ant_radius * np.sin(angles)], axis=1)

    def to_yaml(self, path: str | Path):
        data = {k: v for k, v in self.__dict__.items()}
        with open(path, "w") as f:
            yaml.dump(data, f, default_flow_style=False)

    @classmethod
    def from_yaml(cls, path: str | Path) -> "Config":
        with open(path) as f:
            data = yaml.safe_load(f) or {}
        valid = {k for k in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in data.items() if k in valid})
