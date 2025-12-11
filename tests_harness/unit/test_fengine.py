"""Unit tests for F-Engine (channeliser) module."""
import numpy as np
import pytest
from correlator.core.fengine import FEngine, get_window, quantize_signal


class TestWindowFunctions:
    """Test window function generation."""
    
    def test_hanning_window(self):
        """Test Hanning window generation."""
        window = get_window("hanning", 128)
        assert len(window) == 128
        assert np.allclose(window[0], 0.0, atol=1e-10)
        assert np.allclose(window[-1], 0.0, atol=1e-10)
        assert window[64] > 0.99  # Peak at center
    
    def test_rectangular_window(self):
        """Test rectangular (no) window."""
        window = get_window("rectangular", 128)
        assert len(window) == 128
        assert np.allclose(window, 1.0)


class TestQuantization:
    """Test quantization emulation."""
    
    def test_no_quantization(self):
        """Test that 0 bits = no quantization."""
        signal = np.random.randn(100) + 1j * np.random.randn(100)
        quantized = quantize_signal(signal, n_bits=0)
        assert np.allclose(signal, quantized)
    
    def test_quantization_reduces_dynamic_range(self):
        """Test that quantization reduces unique values."""
        signal = np.random.randn(1000) + 1j * np.random.randn(1000)
        quantized = quantize_signal(signal, n_bits=4)
        
        # Quantized signal should have fewer unique values
        unique_original = len(np.unique(signal.real))
        unique_quantized = len(np.unique(quantized.real))
        assert unique_quantized < unique_original


class TestFEngine:
    """Test F-Engine channeliser."""
    
    def test_fengine_initialization(self):
        """Test F-Engine can be created."""
        fengine = FEngine(n_channels=256, window_type="hanning")
        assert fengine.n_channels == 256
        assert fengine.window_type == "hanning"
    
    def test_fengine_output_shape(self):
        """Test F-Engine produces correct output shape."""
        n_ants = 4
        n_channels = 256
        chunk_size = 4096
        
        fengine = FEngine(n_channels=n_channels, window_type="hanning")
        
        # Generate random input
        signals = np.random.randn(n_ants, chunk_size) + 1j * np.random.randn(n_ants, chunk_size)
        
        # Process
        channelised = fengine.process_chunk(signals)
        
        # Check shape: (n_ants, n_spectra, n_channels)
        assert channelised.shape[0] == n_ants
        assert channelised.shape[2] == n_channels
        assert channelised.dtype == np.complex128
    
    def test_fengine_parseval_theorem(self):
        """Test that FFT preserves power (Parseval's theorem)."""
        n_channels = 256
        fengine = FEngine(n_channels=n_channels, window_type="rectangular")
        
        # Single antenna, single spectrum
        signal = np.random.randn(1, n_channels) + 1j * np.random.randn(1, n_channels)
        
        # Power in time domain
        time_power = np.mean(np.abs(signal)**2)
        
        # Process
        channelised = fengine.process_chunk(signal)
        
        # Power in frequency domain (normalized by FFT size)
        freq_power = np.mean(np.abs(channelised)**2) / n_channels
        
        # Should be approximately equal
        assert np.abs(time_power - freq_power) / time_power < 0.01
    
    def test_fengine_with_quantization(self):
        """Test F-Engine with quantization enabled."""
        fengine = FEngine(n_channels=256, quantize_bits=8)
        signals = np.random.randn(2, 512) + 1j * np.random.randn(2, 512)
        
        channelised = fengine.process_chunk(signals)
        assert channelised.shape[0] == 2
        assert channelised.shape[2] == 256
