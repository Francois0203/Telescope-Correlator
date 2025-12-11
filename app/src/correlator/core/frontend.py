"""Frontend: Data Ingestion Module

Handles loading antenna time-series data from various sources:
- Batch mode: Load from files (numpy arrays, raw binary)
- Simulated streaming: Generate synthetic antenna signals and stream them
"""
from __future__ import annotations

import numpy as np
from pathlib import Path
from typing import Iterator, Optional, Tuple
import time


class DataSource:
    """Base class for data sources."""
    
    def __init__(self, n_ants: int, sample_rate: float):
        self.n_ants = n_ants
        self.sample_rate = sample_rate
    
    def stream(self, chunk_size: int) -> Iterator[np.ndarray]:
        """Yield chunks of data shape (n_ants, chunk_size)."""
        raise NotImplementedError


class SimulatedStream(DataSource):
    """Simulated streaming data source with synthetic signals.
    
    Generates complex narrowband signals for N antennas observing point sources.
    Simulates real-time streaming by yielding chunks with realistic timing.
    """
    
    def __init__(
        self,
        n_ants: int,
        sample_rate: float,
        source_angles: list[float],
        freq: float = 1.0,
        snr: float = 20.0,
        ant_positions: Optional[np.ndarray] = None,
        seed: int = 0,
    ):
        super().__init__(n_ants, sample_rate)
        self.source_angles = source_angles
        self.freq = freq
        self.snr = snr
        self.seed = seed
        self.rng = np.random.default_rng(seed)
        
        # Generate antenna positions (uniform circle by default)
        if ant_positions is None:
            angles = np.linspace(0, 2 * np.pi, n_ants, endpoint=False)
            self.ant_positions = np.stack([10 * np.cos(angles), 10 * np.sin(angles)], axis=1)
        else:
            self.ant_positions = ant_positions
            
        self.sample_counter = 0
    
    def stream(self, chunk_size: int, max_chunks: Optional[int] = None, realtime: bool = False) -> Iterator[np.ndarray]:
        """Generate and yield data chunks.
        
        Args:
            chunk_size: Number of samples per chunk
            max_chunks: Maximum number of chunks to generate (None = infinite)
            realtime: If True, simulate real-time by sleeping between chunks
        """
        chunk_count = 0
        
        while max_chunks is None or chunk_count < max_chunks:
            # Generate time samples for this chunk
            t_start = self.sample_counter / self.sample_rate
            t = t_start + np.arange(chunk_size) / self.sample_rate
            
            # Initialize signals
            signals = np.zeros((self.n_ants, chunk_size), dtype=np.complex128)
            
            # Add each source
            for angle in self.source_angles:
                sx = np.cos(angle)
                sy = np.sin(angle)
                phases = self.ant_positions[:, 0] * sx + self.ant_positions[:, 1] * sy
                tone = np.exp(2j * np.pi * self.freq * t)
                
                for i in range(self.n_ants):
                    signals[i] += np.exp(-2j * np.pi * phases[i]) * tone
            
            # Add noise
            power = np.mean(np.abs(signals)**2)
            noise_std = np.sqrt(power / self.snr) if self.snr > 0 else 0
            if noise_std > 0:
                noise_real = self.rng.normal(scale=noise_std, size=signals.shape)
                noise_imag = self.rng.normal(scale=noise_std, size=signals.shape)
                signals += (noise_real + 1j * noise_imag) / np.sqrt(2)
            
            self.sample_counter += chunk_size
            chunk_count += 1
            
            # Simulate real-time delay
            if realtime:
                chunk_duration = chunk_size / self.sample_rate
                time.sleep(chunk_duration)
            
            yield signals


class BatchFileSource(DataSource):
    """Load data from batch files.
    
    Supports numpy .npy files with shape (n_ants, n_samples).
    """
    
    def __init__(self, file_path: str | Path, sample_rate: float):
        self.file_path = Path(file_path)
        
        # Load file to get metadata
        data = np.load(self.file_path)
        if data.ndim != 2:
            raise ValueError(f"Expected 2D array (n_ants, n_samples), got shape {data.shape}")
        
        n_ants = data.shape[0]
        super().__init__(n_ants, sample_rate)
        
        self.data = data
        self.n_samples = data.shape[1]
    
    def stream(self, chunk_size: int) -> Iterator[np.ndarray]:
        """Yield chunks from loaded data."""
        n_chunks = self.n_samples // chunk_size
        
        for i in range(n_chunks):
            start_idx = i * chunk_size
            end_idx = start_idx + chunk_size
            yield self.data[:, start_idx:end_idx]
        
        # Yield remaining samples if any
        remaining = self.n_samples % chunk_size
        if remaining > 0:
            yield self.data[:, -remaining:]
