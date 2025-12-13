"""End-to-end accuracy validation with astronomical test cases."""
import numpy as np
import pytest
from correlator import CorrelatorConfig, SimulatedStream, FEngine, XEngine, DelayEngine


class TestAstronomicalAccuracy:
    """Test accuracy with realistic astronomical scenarios."""

    def test_point_source_visibility(self):
        """Test visibility accuracy for a point source at known position."""
        # Setup for simple case: 2 antennas, point source
        n_ants = 2
        n_channels = 128
        sample_rate = 256.0

        # Antenna positions (simple east-west baseline)
        ant_pos = np.array([[0, 0, 0], [50, 0, 0]], dtype=float)  # 50m baseline

        # Point source at zenith (no geometric delay)
        source_angles = [0.0]  # Zenith angle = 0

        # Create simulation
        sim = SimulatedStream(
            n_ants=n_ants,
            sample_rate=sample_rate,
            source_angles=source_angles,
            freq=1.0,  # 1 GHz
            snr=50.0  # High SNR for accuracy test
        )

        # Setup correlator components
        fengine = FEngine(n_channels=n_channels, window_type="hanning")
        delay_engine = DelayEngine(ant_pos, reference_freq=1.0)
        delay_engine.set_phase_center(np.array([0, 0, 1]))  # Zenith

        xengine = XEngine(
            n_ants=n_ants,
            n_channels=n_channels,
            integration_time=1.0,
            sample_rate=sample_rate
        )

        # Process one integration period
        chunk_size = int(sample_rate)  # 1 second
        data = next(sim.stream(chunk_size=chunk_size, max_chunks=1))

        # F-engine
        channelised = fengine.process_chunk(data)

        # Apply delays (should be minimal for zenith source)
        freq_channels = np.fft.fftfreq(n_channels, 1/sample_rate)
        corrected = delay_engine.apply_delays(channelised, freq_channels)

        # Correlate
        for spec_idx in range(corrected.shape[1]):
            spectrum = corrected[:, spec_idx, :]
            vis = xengine.correlate_spectrum(spectrum)
            xengine.accumulate(vis)

        # Get integrated visibilities
        integrated = xengine.get_integrated()

        # For zenith point source with high SNR:
        # 1. Autocorrelations should be real and positive
        assert np.all(integrated[0, :].real > 0)  # Auto 0
        assert np.all(integrated[1, :].real > 0)  # Auto 1
        assert np.allclose(integrated[0, :].imag, 0, atol=1e-6)
        assert np.allclose(integrated[1, :].imag, 0, atol=1e-6)

        # 2. Cross-correlation should be complex with reasonable amplitude
        cross_corr = integrated[2, :]  # (0,1) baseline
        cross_power = np.mean(np.abs(cross_corr)**2)
        assert cross_power > 0

        # 3. Phase should be near zero (zenith source, no geometric delay)
        mean_phase = np.mean(np.angle(cross_corr))
        assert np.abs(mean_phase) < 0.1  # Within 0.1 radians

    def test_baseline_independent_accuracy(self):
        """Test that accuracy is maintained across different baselines."""
        # Test with 3 antennas to get different baseline lengths
        n_ants = 3
        n_channels = 64

        # Different antenna positions
        ant_pos = np.array([
            [0, 0, 0],      # Reference
            [100, 0, 0],    # 100m east
            [0, 100, 0]     # 100m north
        ], dtype=float)

        # Zenith source (no geometric delay)
        sim = SimulatedStream(
            n_ants=n_ants,
            sample_rate=128.0,
            source_angles=[0.0],
            freq=1.0,
            snr=40.0
        )

        fengine = FEngine(n_channels=n_channels, window_type="rectangular")
        delay_engine = DelayEngine(ant_pos, reference_freq=1.0)
        delay_engine.set_phase_center(np.array([0, 0, 1]))

        xengine = XEngine(n_ants=n_ants, n_channels=n_channels,
                         integration_time=0.5, sample_rate=128.0)

        # Process data
        data = next(sim.stream(chunk_size=64, max_chunks=1))
        channelised = fengine.process_chunk(data)

        freq_channels = np.fft.fftfreq(n_channels, 1/128.0)
        corrected = delay_engine.apply_delays(channelised, freq_channels)

        for spec_idx in range(corrected.shape[1]):
            spectrum = corrected[:, spec_idx, :]
            vis = xengine.correlate_spectrum(spectrum)
            xengine.accumulate(vis)

        integrated = xengine.get_integrated()

        # All autocorrelations should be real and positive
        autocorr_indices = [0, 3, 5]  # (0,0), (1,1), (2,2)
        for idx in autocorr_indices:
            assert np.all(integrated[idx, :].real > 0)
            assert np.allclose(integrated[idx, :].imag, 0, atol=1e-6)

        # Cross-correlations should have reasonable amplitudes
        cross_indices = [1, 2, 4]  # (0,1), (0,2), (1,2)
        for idx in cross_indices:
            mean_power = np.mean(np.abs(integrated[idx, :])**2)
            assert mean_power > 0.1  # Should have significant signal

    def test_frequency_channel_accuracy(self):
        """Test that different frequency channels are processed correctly."""
        n_ants = 2
        n_channels = 256

        # Create signal with frequency-dependent amplitude
        freq_channels = np.fft.fftfreq(n_channels, 1/512.0)
        amplitude_spectrum = np.ones(n_channels, dtype=complex)

        # Add some frequency structure
        amplitude_spectrum[50:60] = 2.0  # Boost channels 50-59
        amplitude_spectrum[100:110] = 0.5  # Attenuate channels 100-109

        # Create time-domain signal
        noise = 0.01 * (np.random.randn(n_channels) + 1j * np.random.randn(n_channels))
        signal_td = np.fft.ifft(amplitude_spectrum) + noise
        signal_td = signal_td * np.sqrt(n_channels)  # Normalize

        # Same signal on both antennas
        spectrum = np.array([signal_td, signal_td])

        xengine = XEngine(n_ants=n_ants, n_channels=n_channels,
                         integration_time=1.0, sample_rate=512.0)

        vis = xengine.correlate_spectrum(spectrum)

        # Cross-correlation should match the known amplitude spectrum squared
        cross_corr = vis[2, :]
        expected_cross = amplitude_spectrum * np.conj(amplitude_spectrum)

        # Check that peaks and nulls are in right places
        peak_region = np.mean(np.abs(cross_corr[50:60]))
        null_region = np.mean(np.abs(cross_corr[100:110]))
        normal_region = np.mean(np.abs(cross_corr[150:160]))

        assert peak_region > 3 * normal_region  # Peak region much stronger
        assert null_region < 0.3 * normal_region  # Null region much weaker