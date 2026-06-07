"""End-to-end accuracy validation with astronomical test cases."""
import numpy as np
import pytest
from correlator import SimulatedStream, FEngine, XEngine, DelayEngine


class TestAstronomicalAccuracy:
    """Test accuracy with realistic astronomical scenarios."""

    def test_point_source_visibility(self):
        """Test visibility accuracy for a point source at known position."""
        n_ants = 2
        n_channels = 128
        sample_rate = 256.0

        ant_pos = np.array([[0, 0, 0], [50, 0, 0]], dtype=float)

        sim = SimulatedStream(
            n_ants=n_ants,
            sample_rate=sample_rate,
            source_angles=[0.0],
            freq=1.0,
            snr=50.0,
        )

        fengine = FEngine(n_channels=n_channels, window_type="hanning")
        delay_engine = DelayEngine(ant_pos, reference_freq=1.0)
        delay_engine.set_phase_center(np.array([0, 0, 1]))

        xengine = XEngine(
            n_ants=n_ants,
            n_channels=n_channels,
            integration_time=1.0,
            sample_rate=sample_rate,
        )

        chunk_size = int(sample_rate)
        data = next(sim.stream(chunk_size=chunk_size, max_chunks=1))
        channelised = fengine.process_chunk(data)

        freq_channels = np.fft.fftfreq(n_channels, 1 / sample_rate)
        corrected = delay_engine.apply_delays(channelised, freq_channels)

        for spec_idx in range(corrected.shape[1]):
            spectrum = corrected[:, spec_idx, :]
            vis = xengine.correlate_spectrum(spectrum)
            xengine.accumulate(vis)

        integrated = xengine.get_integrated()

        # Autocorrelations must be real and positive
        assert np.all(integrated[0, :].real > 0)
        assert np.all(integrated[1, :].real > 0)
        assert np.allclose(integrated[0, :].imag, 0, atol=1e-6)
        assert np.allclose(integrated[1, :].imag, 0, atol=1e-6)

        # Cross-correlation must have non-zero power
        cross_corr = integrated[2, :]
        assert np.mean(np.abs(cross_corr)**2) > 0

        # Phase should be near zero for zenith source (no geometric delay)
        assert np.abs(np.mean(np.angle(cross_corr))) < 0.1

    def test_baseline_independent_accuracy(self):
        """Test that accuracy is maintained across different baselines."""
        n_ants = 3
        n_channels = 64

        ant_pos = np.array([
            [0,   0,   0],
            [100, 0,   0],
            [0,   100, 0],
        ], dtype=float)

        sim = SimulatedStream(
            n_ants=n_ants,
            sample_rate=128.0,
            source_angles=[0.0],
            freq=1.0,
            snr=40.0,
        )

        fengine = FEngine(n_channels=n_channels, window_type="rectangular")
        delay_engine = DelayEngine(ant_pos, reference_freq=1.0)
        delay_engine.set_phase_center(np.array([0, 0, 1]))

        xengine = XEngine(n_ants=n_ants, n_channels=n_channels,
                          integration_time=0.5, sample_rate=128.0)

        data = next(sim.stream(chunk_size=64, max_chunks=1))
        channelised = fengine.process_chunk(data)

        freq_channels = np.fft.fftfreq(n_channels, 1 / 128.0)
        corrected = delay_engine.apply_delays(channelised, freq_channels)

        for spec_idx in range(corrected.shape[1]):
            vis = xengine.correlate_spectrum(corrected[:, spec_idx, :])
            xengine.accumulate(vis)

        integrated = xengine.get_integrated()

        # All autocorrelations must be real
        for idx in range(n_ants):
            assert np.allclose(integrated[idx, :].imag, 0, atol=1e-6)
            peak_channels = np.argsort(np.abs(integrated[idx, :]))[-10:]
            assert np.all(integrated[idx, peak_channels].real > 0)

        # Cross-correlations must have signal
        for idx in [3, 4, 5]:  # cross-correlation baseline indices for 3 antennas
            assert np.mean(np.abs(integrated[idx, :])**2) > 0.1

    def test_frequency_channel_accuracy(self):
        """Test that different frequency channels are processed correctly."""
        n_ants = 2
        n_channels = 256

        amplitude_spectrum = np.ones(n_channels, dtype=complex)
        amplitude_spectrum[50:60] = 2.0    # boosted region
        amplitude_spectrum[100:110] = 0.5  # attenuated region

        noise = 0.01 * (np.random.randn(n_channels) + 1j * np.random.randn(n_channels))
        spectrum_with_noise = amplitude_spectrum + noise
        spectrum = np.array([spectrum_with_noise, spectrum_with_noise])

        xengine = XEngine(n_ants=n_ants, n_channels=n_channels,
                          integration_time=1.0, sample_rate=512.0)

        vis = xengine.correlate_spectrum(spectrum)
        cross_corr = vis[2, :]  # (0,1) baseline

        peak_region   = np.mean(np.abs(cross_corr[50:60]))
        null_region   = np.mean(np.abs(cross_corr[100:110]))
        normal_region = np.mean(np.abs(cross_corr[150:160]))

        assert peak_region > 3 * normal_region
        assert null_region < 0.3 * normal_region
