"""Delay Compensation and Phasing Module

Implements geometric delay compensation for antenna arrays.
Corrects for path length differences to different antennas when observing
a source at a specific direction.

Key features:
- Geometric delay calculation from antenna positions and source direction
- Phase rotation (fringe stopping) to compensate delays
- Support for tracking sources over time
"""
from __future__ import annotations

import numpy as np
from typing import Optional, Tuple


def calculate_geometric_delays(
    ant_positions: np.ndarray,
    source_direction: np.ndarray,
    wavelength: float = 1.0,
) -> np.ndarray:
    """Calculate geometric delays for each antenna.
    
    Args:
        ant_positions: Array shape (n_ants, 2 or 3) with antenna positions
        source_direction: Unit vector shape (2 or 3) pointing to source
        wavelength: Observing wavelength (arbitrary units matching positions)
    
    Returns:
        Delays in units of wavelength for each antenna shape (n_ants,)
    """
    # Project antenna positions onto source direction
    # Delay = dot(position, direction) / c
    # In units of wavelength: delay_wavelengths = dot(position, direction) / wavelength
    delays = (ant_positions @ source_direction) / wavelength
    
    # Reference to first antenna (or could reference to array center)
    delays = delays - delays[0]
    
    return delays


class DelayEngine:
    """Delay compensation and phasing engine.
    
    Applies phase rotations to channelised data to compensate for geometric delays.
    """
    
    def __init__(
        self,
        ant_positions: np.ndarray,
        reference_freq: float = 1.0,
    ):
        """Initialize delay engine.
        
        Args:
            ant_positions: Antenna positions shape (n_ants, 2 or 3)
            reference_freq: Reference frequency in Hz
        """
        self.ant_positions = ant_positions
        self.n_ants = ant_positions.shape[0]
        self.reference_freq = reference_freq
        
        # Speed of light for wavelength calculation
        self.c = 3e8  # m/s
        
        # Current phase tracking state
        self.current_delays = np.zeros(self.n_ants)
        self.phase_center = np.array([1.0, 0.0, 0.0])  # Default: zenith
    
    def set_phase_center(self, direction: np.ndarray):
        """Set the phase tracking center (source direction).
        
        Args:
            direction: Unit vector pointing to phase center
        """
        self.phase_center = direction / np.linalg.norm(direction)
        
        # Recompute delays
        wavelength = self.c / self.reference_freq  # Wavelength in meters
        self.current_delays = calculate_geometric_delays(
            self.ant_positions,
            self.phase_center,
            wavelength=wavelength
        )
    
    def apply_delays(
        self,
        channelised_data: np.ndarray,
        channel_frequencies: np.ndarray,
    ) -> np.ndarray:
        """Apply delay compensation to channelised data.
        
        Args:
            channelised_data: Shape (n_ants, n_spectra, n_channels)
            channel_frequencies: Frequency of each channel (Hz)
        
        Returns:
            Phase-corrected data with same shape
        """
        n_ants, n_spectra, n_channels = channelised_data.shape
        
        if n_ants != self.n_ants:
            raise ValueError(f"Expected {self.n_ants} antennas, got {n_ants}")
        
        # Compute phase rotation for each antenna and channel
        # phase = 2*pi * delay * frequency
        corrected = np.copy(channelised_data)
        
        for ant_idx in range(n_ants):
            delay = self.current_delays[ant_idx]
            
            # Phase rotation per channel
            phases = 2 * np.pi * delay * channel_frequencies
            phasor = np.exp(-1j * phases)  # Negative to correct delay
            
            # Apply to all spectra for this antenna
            corrected[ant_idx, :, :] *= phasor[np.newaxis, :]
        
        return corrected
