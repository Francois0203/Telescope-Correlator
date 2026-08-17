"""End-to-end accuracy validation with astronomical test cases.

These tests use non-degenerate array geometry and a physically consistent
simulator, so that the delay engine is genuinely exercised.

Earlier revisions of this file did not. They constructed ``SimulatedStream``
without passing ``ant_positions``, which fell back to a 10 m radius circle at
integer coordinates; the old simulator's geometric term was
``exp(-2j*pi*x)``, which is identically 1 for integer ``x``. Every antenna
therefore received the same signal, the phase centre was set to a direction
orthogonal to a planar array so the delay stage was a no-op, and the tests
asserted that the phase was zero. They could not fail. Keep the geometry here
irregular and the phase centre off-source, or the same trap reopens.

Broader analytic coverage lives in ``test_correlator_validation.py``.
"""
import numpy as np
import pytest
from scipy.constants import c as C_LIGHT

from correlator import (
    SimulatedStream, FEngine, XEngine, DelayEngine,
    PointSource, direction_from_zenith_angle,
)


# These tests assert deterministic physics to ~1e-5 rad, so they run
# effectively noiseless (linear SNR 1e20). Behaviour under realistic noise is
# covered by TestVisibilityInvariants in test_correlator_validation.py.
NOISELESS_DB = 200.0


def _wrap(x):
    return np.angle(np.exp(1j * np.asarray(x)))


class TestAstronomicalAccuracy:
    """Realistic astronomical scenarios, checked against closed-form values."""

    def test_point_source_visibility(self):
        """A tracked point source must phase up coherently on a real baseline."""
        n_channels = 128
        sample_rate = 256.0
        sky_freq = 1.42e9
        tone_bin = 11
        tone_freq = tone_bin * sample_rate / n_channels

        # 50 m East-West baseline with a small vertical offset, so the
        # geometry is not degenerate for an off-zenith source.
        ant_pos = np.array([[0.0, 0.0, 0.0], [50.0, 0.0, 3.5]])
        s_hat = direction_from_zenith_angle(np.deg2rad(25.0), azimuth=np.deg2rad(15.0))

        sim = SimulatedStream(
            n_ants=2, sample_rate=sample_rate, ant_positions=ant_pos,
            sources=[PointSource(s_hat, amplitude=1.0)],
            sky_freq=sky_freq, snr=NOISELESS_DB, signal_type="tone", freq=tone_freq,
        )
        fengine = FEngine(n_channels=n_channels, window_type="rectangular")
        delay_engine = DelayEngine(ant_pos, reference_freq=sky_freq)
        delay_engine.set_phase_center(s_hat)
        xengine = XEngine(n_ants=2, n_channels=n_channels,
                          integration_time=1e9, sample_rate=sample_rate)

        chunk = next(sim.stream(chunk_size=n_channels * 4, max_chunks=1))
        channelised = fengine.process_chunk(chunk)
        corrected = delay_engine.apply_delays(
            channelised, fengine.get_channel_frequencies(sample_rate))

        for spec_idx in range(corrected.shape[1]):
            xengine.accumulate(xengine.correlate_spectrum(corrected[:, spec_idx, :]))
        integrated = xengine.get_integrated()

        # Autocorrelations must be real and positive at the tone.
        for ant in (0, 1):
            assert integrated[ant, tone_bin].real > 0
            assert np.allclose(integrated[ant, :].imag, 0, atol=1e-9)

        cross = integrated[2, tone_bin]

        # The delay engine must have removed a fringe that was genuinely there.
        advance = np.dot(ant_pos[1] - ant_pos[0], s_hat) / C_LIGHT
        uncorrected_phase = 2 * np.pi * (sky_freq + tone_freq) * advance
        assert np.abs(_wrap(uncorrected_phase)) > 0.5, (
            "geometry produces no fringe, so this test would pass trivially"
        )

        # Having removed it, the residual phase must be zero.
        assert np.abs(np.angle(cross)) < 1e-5

        # And the amplitude must equal the source power times the FFT gain.
        assert np.abs(np.abs(cross) - n_channels ** 2) / n_channels ** 2 < 1e-3

    def test_baseline_independent_accuracy(self):
        """Every baseline must reproduce its own predicted fringe phase.

        A correlator that mixes up baseline indexing, or applies one antenna's
        delay to another, passes a single-baseline test and fails this one.
        """
        n_channels = 64
        sample_rate = 128.0
        sky_freq = 1.42e9
        tone_bin = 9
        tone_freq = tone_bin * sample_rate / n_channels

        ant_pos = np.array([
            [  0.00,   0.00,  0.00],
            [100.30,  -4.70,  2.10],
            [ -7.40, 100.90, -1.60],
            [ 61.20,  38.50,  4.90],
        ])
        s_hat = direction_from_zenith_angle(np.deg2rad(12.0), azimuth=np.deg2rad(200.0))
        s0 = direction_from_zenith_angle(np.deg2rad(16.0), azimuth=np.deg2rad(200.0))

        sim = SimulatedStream(
            n_ants=4, sample_rate=sample_rate, ant_positions=ant_pos,
            sources=[PointSource(s_hat)],
            sky_freq=sky_freq, snr=NOISELESS_DB, signal_type="tone", freq=tone_freq,
        )
        fengine = FEngine(n_channels=n_channels, window_type="rectangular")
        delay_engine = DelayEngine(ant_pos, reference_freq=sky_freq)
        delay_engine.set_phase_center(s0)
        xengine = XEngine(n_ants=4, n_channels=n_channels,
                          integration_time=1e9, sample_rate=sample_rate)

        chunk = next(sim.stream(chunk_size=n_channels * 4, max_chunks=1))
        corrected = delay_engine.apply_delays(
            fengine.process_chunk(chunk),
            fengine.get_channel_frequencies(sample_rate))

        for spec_idx in range(corrected.shape[1]):
            xengine.accumulate(xengine.correlate_spectrum(corrected[:, spec_idx, :]))
        integrated = xengine.get_integrated()

        for idx in range(4):
            assert np.allclose(integrated[idx, :].imag, 0, atol=1e-9)
            assert integrated[idx, tone_bin].real > 0

        checked = 0
        for bl_idx, (i, j) in enumerate(xengine.baselines):
            if i == j:
                continue
            delta_tau = np.dot(ant_pos[i] - ant_pos[j], s_hat - s0) / C_LIGHT
            expected = _wrap(2 * np.pi * (sky_freq + tone_freq) * delta_tau)
            measured = np.angle(integrated[bl_idx, tone_bin])

            assert np.abs(_wrap(measured - expected)) < 1e-5, (
                f"baseline ({i},{j}): measured {measured:+.6f}, expected {expected:+.6f}"
            )
            checked += 1

        assert checked == 6

    def test_frequency_channel_accuracy(self):
        """Two tones must land in their own channels and correlate there only."""
        n_channels = 256
        sample_rate = 512.0
        sky_freq = 1.42e9
        # Both bins must be below Nyquist (n_channels/2). A tone above Nyquist
        # aliases, and the correlator then de-rotates the aliased channel
        # frequency while the source sits at the un-aliased one. That leaves
        # a residual phase of 2*pi*sample_rate*advance, which is correct
        # behaviour for an invalid input, not a correlator bug.
        bins = (37, 101)

        ant_pos = np.array([[0.0, 0.0, 0.0], [40.0, 12.0, 1.1]])
        s_hat = direction_from_zenith_angle(np.deg2rad(20.0))

        # Two point sources at the same direction but different baseband
        # frequencies is not physical; instead run two separate simulations
        # at different tone frequencies and sum the voltages, which is what a
        # two-line spectrum looks like at the antenna.
        chunks = []
        for b, amp in zip(bins, (2.0, 0.5)):
            sim = SimulatedStream(
                n_ants=2, sample_rate=sample_rate, ant_positions=ant_pos,
                sources=[PointSource(s_hat, amplitude=amp)],
                sky_freq=sky_freq, snr=NOISELESS_DB, signal_type="tone",
                freq=b * sample_rate / n_channels,
            )
            chunks.append(next(sim.stream(chunk_size=n_channels * 2, max_chunks=1)))
        voltages = sum(chunks)

        fengine = FEngine(n_channels=n_channels, window_type="rectangular")
        delay_engine = DelayEngine(ant_pos, reference_freq=sky_freq)
        delay_engine.set_phase_center(s_hat)
        xengine = XEngine(n_ants=2, n_channels=n_channels,
                          integration_time=1e9, sample_rate=sample_rate)

        corrected = delay_engine.apply_delays(
            fengine.process_chunk(voltages),
            fengine.get_channel_frequencies(sample_rate))
        for spec_idx in range(corrected.shape[1]):
            xengine.accumulate(xengine.correlate_spectrum(corrected[:, spec_idx, :]))
        cross = xengine.get_integrated()[2, :]

        strong, weak = np.abs(cross[bins[0]]), np.abs(cross[bins[1]])
        empty = np.abs(np.delete(cross, list(bins))).max()

        # Amplitudes follow the source powers: 2.0^2 vs 0.5^2, a 16:1 ratio.
        assert np.abs(strong / weak - 16.0) / 16.0 < 1e-3
        # Everything else is empty to numerical precision.
        assert empty < 1e-6 * strong
        # Both tones are phased up, since the phase centre is on-source.
        assert np.abs(np.angle(cross[bins[0]])) < 1e-5
        assert np.abs(np.angle(cross[bins[1]])) < 1e-5
