"""Unit tests for delay compensation module."""
import numpy as np
import pytest
from correlator.core.delay import DelayEngine, calculate_geometric_delays


class TestGeometricDelays:
    """Test geometric delay calculation."""
    
    def test_zenith_source_no_delay(self):
        """Test that zenith source has zero delays (all antennas equidistant)."""
        ant_positions = np.array([
            [0, 0, 0],
            [10, 0, 0],
            [0, 10, 0]
        ])
        source_direction = np.array([0, 0, 1])  # Zenith
        
        delays = calculate_geometric_delays(ant_positions, source_direction)
        assert np.allclose(delays, 0.0)
    
    def test_horizon_source_has_delays(self):
        """Test that horizon source produces delays."""
        ant_positions = np.array([
            [0, 0, 0],
            [10, 0, 0],
            [0, 10, 0]
        ])
        source_direction = np.array([1, 0, 0])  # Horizon, along x-axis
        
        delays = calculate_geometric_delays(ant_positions, source_direction)
        
        # Second antenna should have different delay than first
        assert not np.allclose(delays[0], delays[1])
    
    def test_delay_proportional_to_baseline(self):
        """Test that delay scales with antenna separation."""
        source_direction = np.array([1, 0, 0])
        
        # Small baseline
        ant_pos_small = np.array([[0, 0, 0], [1, 0, 0]])
        delays_small = calculate_geometric_delays(ant_pos_small, source_direction)
        
        # Large baseline (2x)
        ant_pos_large = np.array([[0, 0, 0], [2, 0, 0]])
        delays_large = calculate_geometric_delays(ant_pos_large, source_direction)
        
        # Delay should double
        assert np.abs(delays_large[1] / delays_small[1] - 2.0) < 0.01


class TestDelayEngine:
    """Test DelayEngine class."""
    
    def test_delay_engine_initialization(self):
        """Test DelayEngine can be created."""
        ant_positions = np.array([[0, 0, 0], [10, 0, 0], [0, 10, 0]])
        engine = DelayEngine(ant_positions=ant_positions, reference_freq=1.0)
        
        assert engine.n_ants == 3
        assert np.array_equal(engine.ant_positions, ant_positions)
    
    def test_set_phase_center(self):
        """Test setting phase center updates delays."""
        ant_positions = np.array([[0, 0, 0], [10, 0, 0]])
        engine = DelayEngine(ant_positions=ant_positions, reference_freq=1.0)
        
        # Set to horizon source
        engine.set_phase_center(np.array([1, 0, 0]))
        
        # Delays should be non-zero
        assert not np.allclose(engine.current_delays, 0.0)
    
    def test_apply_delays_preserves_shape(self):
        """Test that applying delays preserves data shape."""
        ant_positions = np.array([[0, 0, 0], [10, 0, 0], [0, 10, 0]])
        engine = DelayEngine(ant_positions=ant_positions, reference_freq=1.0)
        engine.set_phase_center(np.array([1, 0, 0]))
        
        # Generate test data: (n_ants, n_spectra, n_channels)
        n_ants = 3
        n_spectra = 4
        n_channels = 64
        data = np.random.randn(n_ants, n_spectra, n_channels) + \
               1j * np.random.randn(n_ants, n_spectra, n_channels)
        
        freq_channels = np.fft.fftfreq(n_channels, d=1/1024.0)
        
        corrected = engine.apply_delays(data, freq_channels)
        
        assert corrected.shape == data.shape
        assert corrected.dtype == np.complex128
    
    def test_apply_delays_is_phase_rotation(self):
        """Test that delay correction is a pure phase rotation (preserves amplitude)."""
        ant_positions = np.array([[0, 0, 0], [10, 0, 0]])
        engine = DelayEngine(ant_positions=ant_positions, reference_freq=1.0)
        engine.set_phase_center(np.array([1, 0, 0]))
        
        data = np.ones((2, 1, 128), dtype=np.complex128)
        freq_channels = np.fft.fftfreq(128, d=1/1024.0)
        
        corrected = engine.apply_delays(data, freq_channels)
        
        # Amplitude should be preserved
        assert np.allclose(np.abs(corrected), np.abs(data))
