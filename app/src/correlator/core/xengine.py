"""X-Engine: Cross-Correlation and Accumulation Module

Implements the correlator core (X-engine) of an FX correlator.
Computes cross-correlations (visibilities) between all antenna pairs for each
frequency channel and accumulates over integration time.

Key features:
- Efficient baseline indexing for N(N-1)/2 + N cross-products
- Time integration with configurable accumulation length
- Vectorized operations for performance
"""
from __future__ import annotations

import numpy as np
from typing import Tuple


def get_baseline_indices(n_ants: int) -> list[Tuple[int, int]]:
    """Generate list of baseline pairs (i, j) where i <= j.
    
    For N antennas, produces N(N+1)/2 baselines including autocorrelations.
    
    Args:
        n_ants: Number of antennas
    
    Returns:
        List of (ant_i, ant_j) tuples
    """
    baselines = []
    for i in range(n_ants):
        for j in range(i, n_ants):
            baselines.append((i, j))
    return baselines


class XEngine:
    """X-Engine: Cross-correlation and accumulation.
    
    Computes visibilities V_ij = <E_i * conj(E_j)> for all antenna pairs
    across all frequency channels, with time averaging.
    """
    
    def __init__(
        self,
        n_ants: int,
        n_channels: int,
        integration_time: float,
        sample_rate: float,
    ):
        """Initialize X-engine.
        
        Args:
            n_ants: Number of antennas
            n_channels: Number of frequency channels
            integration_time: Integration time in seconds
            sample_rate: Sample rate in Hz
        """
        self.n_ants = n_ants
        self.n_channels = n_channels
        self.integration_time = integration_time
        self.sample_rate = sample_rate
        
        # Get baseline pairs
        self.baselines = get_baseline_indices(n_ants)
        self.n_baselines = len(self.baselines)
        
        # Compute number of spectra to accumulate
        # Each spectrum represents (FFT_size / sample_rate) seconds
        # We need (integration_time * sample_rate / FFT_size) spectra
        self.spectra_per_integration = max(1, int(integration_time * sample_rate / n_channels))
        
        # Accumulation buffer
        self.accumulated_vis = np.zeros((self.n_baselines, self.n_channels), dtype=np.complex128)
        self.accumulation_count = 0
    
    def correlate_spectrum(self, channelised_data: np.ndarray) -> np.ndarray:
        """Compute cross-correlations for one time sample (one spectrum per antenna).
        
        Args:
            channelised_data: Shape (n_ants, n_channels) - one spectrum per antenna
        
        Returns:
            Visibilities shape (n_baselines, n_channels)
        """
        vis = np.zeros((self.n_baselines, self.n_channels), dtype=np.complex128)
        
        for bl_idx, (i, j) in enumerate(self.baselines):
            # V_ij = E_i * conj(E_j)
            vis[bl_idx, :] = channelised_data[i, :] * np.conj(channelised_data[j, :])
        
        return vis
    
    def accumulate(self, vis: np.ndarray):
        """Add visibilities to the accumulation buffer.
        
        Args:
            vis: Visibilities shape (n_baselines, n_channels) from correlate_spectrum
        """
        self.accumulated_vis += vis
        self.accumulation_count += 1
    
    def is_ready(self) -> bool:
        """Check if integration is complete."""
        return self.accumulation_count >= self.spectra_per_integration
    
    def get_integrated(self) -> np.ndarray:
        """Get integrated visibilities and reset accumulation.
        
        Returns:
            Averaged visibilities shape (n_baselines, n_channels)
        """
        avg_vis = self.accumulated_vis / self.accumulation_count
        
        # Reset accumulation
        self.accumulated_vis.fill(0)
        self.accumulation_count = 0
        
        return avg_vis
    
    def get_baseline_info(self) -> list[dict]:
        """Get metadata for each baseline.
        
        Returns:
            List of dicts with keys: 'baseline_id', 'ant1', 'ant2', 'autocorr'
        """
        info = []
        for bl_id, (i, j) in enumerate(self.baselines):
            info.append({
                'baseline_id': bl_id,
                'ant1': i,
                'ant2': j,
                'autocorr': (i == j)
            })
        return info
