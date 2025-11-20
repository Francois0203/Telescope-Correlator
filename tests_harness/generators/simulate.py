"""Synthetic signal generator used in the test harness."""
from __future__ import annotations

import numpy as np
from pathlib import Path


def generate_delayed_sine(freq: float = 50.0, sample_rate: int = 1024, duration: float = 0.1, delay_samples: int = 5, noise_std: float = 0.0):
    t = np.arange(0, duration, 1.0 / sample_rate)
    x = np.sin(2 * np.pi * freq * t)
    y = np.roll(x, delay_samples)
    if noise_std > 0:
        y = y + np.random.normal(scale=noise_std, size=y.shape)
    return x, y


def save_pair(out_dir: str | Path, name: str, x, y):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    np.save(out_dir / f"{name}_a.npy", x)
    np.save(out_dir / f"{name}_b.npy", y)
