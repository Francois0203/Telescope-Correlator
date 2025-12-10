"""Unit tests for X-Engine (correlator) module."""
import numpy as np
import pytest
from correlator.xengine import XEngine, get_baseline_indices


class TestBaselineIndices:
    """Test baseline indexing."""
    
    def test_baseline_count(self):
        """Test correct number of baselines for N antennas."""
        for n_ants in [2, 3, 4, 8]:
            baselines = get_baseline_indices(n_ants)
            expected = n_ants * (n_ants + 1) // 2
            assert len(baselines) == expected
    
    def test_baseline_ordering(self):
        """Test baselines are ordered correctly (i <= j)."""
        baselines = get_baseline_indices(4)
        for i, j in baselines:
            assert i <= j
    
    def test_baseline_includes_autocorr(self):
        """Test that autocorrelations are included."""
        baselines = get_baseline_indices(3)
        autocorr = [(i, i) for i in range(3)]
        for ac in autocorr:
            assert ac in baselines


class TestXEngine:
    """Test X-Engine correlator."""
    
    def test_xengine_initialization(self):
        """Test X-Engine can be created."""
        xengine = XEngine(
            n_ants=4,
            n_channels=256,
            integration_time=1.0,
            sample_rate=1024.0
        )
        assert xengine.n_ants == 4
        assert xengine.n_channels == 256
        assert xengine.n_baselines == 10  # 4*(4+1)/2
    
    def test_correlate_spectrum_shape(self):
        """Test correlation produces correct shape."""
        n_ants = 4
        n_channels = 256
        
        xengine = XEngine(
            n_ants=n_ants,
            n_channels=n_channels,
            integration_time=1.0,
            sample_rate=1024.0
        )
        
        # Generate random channelised data
        spectrum = np.random.randn(n_ants, n_channels) + 1j * np.random.randn(n_ants, n_channels)
        
        # Correlate
        vis = xengine.correlate_spectrum(spectrum)
        
        # Check shape: (n_baselines, n_channels)
        assert vis.shape == (10, n_channels)
        assert vis.dtype == np.complex128
    
    def test_autocorrelation_real(self):
        """Test that autocorrelations are real-valued."""
        n_ants = 3
        n_channels = 128
        
        xengine = XEngine(
            n_ants=n_ants,
            n_channels=n_channels,
            integration_time=1.0,
            sample_rate=1024.0
        )
        
        spectrum = np.random.randn(n_ants, n_channels) + 1j * np.random.randn(n_ants, n_channels)
        vis = xengine.correlate_spectrum(spectrum)
        
        # First 3 baselines are autocorrelations: (0,0), (0,1), (0,2)
        # Wait, with ordering i<=j: (0,0), (0,1), (0,2), (1,1), (1,2), (2,2)
        # Autocorrelations are at indices 0, 3, 5
        autocorr_indices = [0, 3, 5]  # (0,0), (1,1), (2,2)
        
        for idx in autocorr_indices:
            # Imaginary part should be near zero
            assert np.allclose(vis[idx, :].imag, 0.0, atol=1e-10)
    
    def test_hermitian_symmetry(self):
        """Test that V_ij = conj(V_ji)."""
        n_ants = 3
        n_channels = 128
        
        xengine = XEngine(
            n_ants=n_ants,
            n_channels=n_channels,
            integration_time=1.0,
            sample_rate=1024.0
        )
        
        spectrum = np.random.randn(n_ants, n_channels) + 1j * np.random.randn(n_ants, n_channels)
        vis = xengine.correlate_spectrum(spectrum)
        
        # Get baseline index for (0,1)
        baselines = xengine.baselines
        idx_01 = baselines.index((0, 1))
        
        # Manually compute (1,0) = conj((0,1))
        v_10 = spectrum[1, :] * np.conj(spectrum[0, :])
        v_01 = vis[idx_01, :]
        
        assert np.allclose(v_10, np.conj(v_01))
    
    def test_accumulation(self):
        """Test visibility accumulation."""
        xengine = XEngine(
            n_ants=2,
            n_channels=64,
            integration_time=1.0,
            sample_rate=256.0
        )
        
        # Should need 4 spectra for 1 second integration
        assert xengine.spectra_per_integration == 4
        
        # Add spectra
        for i in range(3):
            spectrum = np.ones((2, 64), dtype=np.complex128)
            vis = xengine.correlate_spectrum(spectrum)
            xengine.accumulate(vis)
            assert not xengine.is_ready()
        
        # Fourth spectrum should complete integration
        spectrum = np.ones((2, 64), dtype=np.complex128)
        vis = xengine.correlate_spectrum(spectrum)
        xengine.accumulate(vis)
        assert xengine.is_ready()
        
        # Get integrated result
        integrated = xengine.get_integrated()
        assert integrated.shape == (3, 64)  # 2 ants = 3 baselines
        
        # Should reset after getting result
        assert not xengine.is_ready()
