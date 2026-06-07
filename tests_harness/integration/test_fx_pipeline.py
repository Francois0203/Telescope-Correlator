"""Integration tests for full FX correlator pipeline."""
import numpy as np
import pytest
from correlator import (
    Config,
    SimulatedStream,
    FEngine,
    XEngine,
    DelayEngine,
)


class TestFXPipeline:
    """Test complete FX correlator pipeline."""

    def test_end_to_end_pipeline(self):
        """Test complete pipeline from simulation to visibilities."""
        n_ants = 4
        n_channels = 256
        chunk_size = 4096
        sample_rate = 1024.0
        integration_time = 1.0

        sim_source = SimulatedStream(
            n_ants=n_ants,
            sample_rate=sample_rate,
            source_angles=[0.0, np.pi / 6],
            freq=1.0,
            snr=20.0,
        )

        fengine = FEngine(n_channels=n_channels, window_type="hanning")

        ant_pos = np.array([[0, 0, 0], [10, 0, 0], [0, 10, 0], [10, 10, 0]], dtype=float)
        delay_engine = DelayEngine(ant_positions=ant_pos, reference_freq=1.0)
        delay_engine.set_phase_center(np.array([1.0, 0.0, 0.0]))

        xengine = XEngine(
            n_ants=n_ants,
            n_channels=n_channels,
            integration_time=integration_time,
            sample_rate=sample_rate,
        )

        data_stream = sim_source.stream(chunk_size=chunk_size, max_chunks=1)
        time_data = next(data_stream)

        channelised = fengine.process_chunk(time_data)
        assert channelised.shape[0] == n_ants
        assert channelised.shape[2] == n_channels

        freq_channels = np.fft.fftfreq(n_channels, 1 / sample_rate)
        corrected = delay_engine.apply_delays(channelised, freq_channels)
        assert corrected.shape == channelised.shape

        n_spectra = channelised.shape[1]
        for spec_idx in range(n_spectra):
            spectrum = corrected[:, spec_idx, :]
            vis = xengine.correlate_spectrum(spectrum)
            xengine.accumulate(vis)
            assert vis.shape == (10, n_channels)  # 4 ants = 10 baselines

        assert xengine.accumulation_count > 0

    def test_pipeline_with_configuration(self):
        """Test pipeline using Config."""
        cfg = Config(
            n_ants=3,
            n_channels=128,
            sample_rate=512.0,
            integration_time=0.5,
            mode="simulate",
            duration=1.0,
            window="hamming",
        )

        assert cfg.n_ants == 3
        assert cfg.n_channels == 128

        sim_source = SimulatedStream(
            n_ants=cfg.n_ants,
            sample_rate=cfg.sample_rate,
            source_angles=[0.0, np.pi / 6],
            snr=cfg.snr,
        )

        fengine = FEngine(n_channels=cfg.n_channels, window_type=cfg.window)

        xengine = XEngine(
            n_ants=cfg.n_ants,
            n_channels=cfg.n_channels,
            integration_time=cfg.integration_time,
            sample_rate=cfg.sample_rate,
        )

        assert sim_source.n_ants == 3
        assert fengine.n_channels == 128
        assert xengine.n_baselines == 6  # 3*(3+1)/2

    def test_pipeline_produces_valid_visibilities(self):
        """Test that pipeline produces physically valid visibilities."""
        n_ants = 2
        n_channels = 64

        sim_source = SimulatedStream(
            n_ants=n_ants,
            sample_rate=256.0,
            source_angles=[0.0],
            freq=1.0,
            snr=30.0,
        )

        fengine = FEngine(n_channels=n_channels, window_type="rectangular")
        xengine = XEngine(
            n_ants=n_ants,
            n_channels=n_channels,
            integration_time=0.5,
            sample_rate=256.0,
        )

        data = next(sim_source.stream(chunk_size=1024, max_chunks=1))
        channelised = fengine.process_chunk(data)

        for spec_idx in range(channelised.shape[1]):
            vis = xengine.correlate_spectrum(channelised[:, spec_idx, :])
            xengine.accumulate(vis)

        integrated = xengine.get_integrated()

        # Autocorrelations must be real and positive
        assert np.all(np.abs(integrated[0, :].imag) < 1e-10)
        assert np.all(integrated[0, :].real > 0)

        # Cross-correlation must have non-zero power
        assert np.mean(np.abs(integrated[1, :])**2) > 0
