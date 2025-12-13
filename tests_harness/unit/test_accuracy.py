"""Accuracy validation tests using known analytical solutions."""
import numpy as np
import pytest
from correlator.core.fengine import FEngine
from correlator.core.xengine import XEngine
from correlator.core.delay import DelayEngine


class TestCorrelatorAccuracy:
    """Test correlator accuracy against analytical solutions."""

    def test_delay_accuracy(self):
        """Test delay compensation accuracy with known geometry."""
        # Simple 2-antenna case with known baseline
        ant_pos = np.array([[0, 0, 0], [100, 0, 0]], dtype=float)  # 100m baseline
        delay_engine = DelayEngine(ant_pos, reference_freq=1.0)

        # Point source at zenith (delay = 0 for both antennas)
        source_dir = np.array([0, 0, 1])  # zenith
        delay_engine.set_phase_center(source_dir)

        # Test delays at reference frequency
        delays = delay_engine.get_delays(1.0)
        assert np.allclose(delays, 0.0, atol=1e-10)

        # Point source at 45 degrees east
        # For 100m baseline, geometric delay should be ~0.33ns
        source_dir = np.array([1, 0, 1]) / np.sqrt(2)  # 45 deg elevation, 0 deg azimuth
        delay_engine.set_phase_center(source_dir)
        delays = delay_engine.get_delays(1.0)  # 1 GHz = 1e9 Hz

        # Expected delay for antenna 1 relative to antenna 0
        # Delay = (baseline · source_vector) / c
        c = 3e8  # speed of light
        expected_delay = (100 * np.cos(np.pi/4)) / c  # projection onto source direction
        assert np.abs(delays[1] - expected_delay) < 1e-12

    def test_fft_accuracy(self):
        """Test FFT accuracy with known sinusoidal input."""
        n_channels = 256
        fengine = FEngine(n_channels=n_channels, window_type="rectangular")

        # Create pure tone at channel 10
        freq_idx = 10
        freq = freq_idx / n_channels  # Normalized frequency
        t = np.arange(n_channels)
        signal = np.exp(2j * np.pi * freq * t)

        # Process single antenna
        input_data = signal.reshape(1, -1)  # Shape: (1, n_channels)
        output = fengine.process_chunk(input_data)

        # Should have peak at channel 10
        spectrum = output[0, 0, :]  # First antenna, first spectrum, all channels
        peak_idx = np.argmax(np.abs(spectrum))
        assert peak_idx == freq_idx

        # Phase should be zero at peak (input was real exponential)
        peak_phase = np.angle(spectrum[peak_idx])
        assert np.abs(peak_phase) < 1e-10

    def test_correlation_known_signals(self):
        """Test correlation with analytically computable signals."""
        n_ants = 2
        n_channels = 64

        # Create identical signals on both antennas (perfect correlation)
        signal = np.random.randn(n_channels) + 1j * np.random.randn(n_channels)
        spectrum = np.array([signal, signal])  # Same signal on both antennas

        xengine = XEngine(n_ants=n_ants, n_channels=n_channels,
                         integration_time=1.0, sample_rate=256.0)

        vis = xengine.correlate_spectrum(spectrum)

        # Autocorrelations should equal power spectrum
        expected_auto_power = np.sum(np.abs(signal)**2)
        actual_auto_0 = np.sum(vis[0, :].real)  # (0,0) autocorrelation
        actual_auto_1 = np.sum(vis[1, :].real)  # (1,1) autocorrelation

        assert np.abs(actual_auto_0 - expected_auto_power) / expected_auto_power < 1e-10
        assert np.abs(actual_auto_1 - expected_auto_power) / expected_auto_power < 1e-10

        # Cross-correlation should equal autocorrelation (identical signals)
        cross_corr = vis[2, :]  # (0,1) baseline
        expected_cross = signal * np.conj(signal)
        assert np.allclose(cross_corr, expected_cross, rtol=1e-10)

    def test_correlation_phase_accuracy(self):
        """Test correlation phase accuracy with delayed signals."""
        n_ants = 2
        n_channels = 64

        # Create signal with known delay
        delay_samples = 5
        freq = 0.1  # Normalized frequency
        t = np.arange(n_channels)
        signal0 = np.exp(2j * np.pi * freq * t)
        signal1 = np.roll(signal0, delay_samples)  # Delay antenna 1

        spectrum = np.array([signal0, signal1])

        xengine = XEngine(n_ants=n_ants, n_channels=n_channels,
                         integration_time=1.0, sample_rate=256.0)

        vis = xengine.correlate_spectrum(spectrum)

        # Cross-correlation should show phase delay
        cross_corr = vis[2, :]  # (0,1) baseline
        expected_phase = 2 * np.pi * freq * delay_samples
        actual_phase = np.angle(cross_corr[0])  # Phase at DC (freq=0 component)

        # Phase should match expected delay
        phase_diff = np.abs(actual_phase - expected_phase)
        phase_diff = np.min([phase_diff, 2*np.pi - phase_diff])  # Handle wraparound
        assert phase_diff < 0.1  # Within 0.1 radians

    def test_visibility_amplitude_accuracy(self):
        """Test visibility amplitude accuracy with known SNR."""
        n_ants = 2
        n_channels = 128

        # Create signals with known cross-correlation amplitude
        amplitude = 2.0
        noise_std = 0.1

        # Base signal
        signal = amplitude * (np.random.randn(n_channels) + 1j * np.random.randn(n_channels))

        # Antenna 1: base signal + noise
        ant0 = signal + noise_std * (np.random.randn(n_channels) + 1j * np.random.randn(n_channels))

        # Antenna 2: base signal + noise
        ant1 = signal + noise_std * (np.random.randn(n_channels) + 1j * np.random.randn(n_channels))

        spectrum = np.array([ant0, ant1])

        xengine = XEngine(n_ants=n_ants, n_channels=n_channels,
                         integration_time=1.0, sample_rate=512.0)

        vis = xengine.correlate_spectrum(spectrum)

        # Cross-correlation amplitude should be approximately |amplitude|^2
        cross_corr = vis[2, :]  # (0,1) baseline
        measured_amplitude = np.mean(np.abs(cross_corr))

        expected_amplitude = amplitude**2
        relative_error = np.abs(measured_amplitude - expected_amplitude) / expected_amplitude

        # Should be accurate to within noise limits
        assert relative_error < 0.1  # 10% relative error acceptable with noise