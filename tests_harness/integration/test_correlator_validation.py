"""Analytic validation of the full FX chain.

These are the tests that answer "does this correlator actually work?".  Each
one compares the correlator's output against a value derived independently —
from closed-form interferometry, from an invariant, or from a second
implementation — rather than against the correlator's own behaviour.

The load-bearing test is :meth:`TestPointSourcePhase.test_off_pointing_phase`.
A correlator whose delay stage does nothing at all still passes a
"source at the phase centre has zero phase" test, because zero is also what
you get by doing nothing.  Deliberately mis-pointing the phase centre by a
known angle and predicting the resulting non-zero phase is what distinguishes
a working delay engine from an absent one.

Conventions are those of :mod:`correlator.core.delay`; see that module's
docstring.  For a point source at ``s_hat`` observed with phase centre ``s0``,
the visibility on baseline ``b_ij = r_i - r_j`` is

    V_ij[k] = A * exp(+2j*pi * (f_sky + f_ch[k]) * b_ij . (s_hat - s0) / c)
"""
import numpy as np
import pytest
from scipy.constants import c as C_LIGHT

from correlator.core.fengine import FEngine
from correlator.core.xengine import XEngine, get_baseline_indices
from correlator.core.delay import DelayEngine
from correlator.core.frontend import (
    SimulatedStream,
    PointSource,
    direction_from_zenith_angle,
)

# ── Fixtures shared by the tests ────────────────────────────────────────────

# A deliberately irregular 3-D array. Integer, symmetric or coplanar layouts
# can make geometric phases vanish by accident and turn a real test into a
# tautology — which is exactly how the original test suite came to pass
# without exercising the delay engine at all.
ANT_POS = np.array([
    [  0.00,   0.00,  0.00],
    [ 23.70,  -8.10,  1.30],
    [ -5.20,  31.40, -2.70],
    [ 14.90,  19.60,  0.80],
])

SKY_FREQ = 1.42e9          # Hz — HI line
SAMPLE_RATE = 1024.0       # Hz
N_CHANNELS = 64
TONE_BIN = 7               # tone lands exactly on this FFT bin
TONE_FREQ = TONE_BIN * SAMPLE_RATE / N_CHANNELS
NOISELESS_DB = 200.0       # effectively noiseless (linear SNR 1e20)


def wrap(phase):
    """Wrap angles to (-pi, pi]."""
    return np.angle(np.exp(1j * np.asarray(phase)))


def channelise(
    sources,
    ant_pos=ANT_POS,
    signal_type="tone",
    window="rectangular",
    snr_db=NOISELESS_DB,
    n_chunks=1,
    n_channels=N_CHANNELS,
    seed=1,
):
    """Run frontend + F-engine, returning (channelised, channel_freqs, voltages).

    Returns:
        channelised: (n_ants, n_spectra, n_channels)
        channel_freqs: (n_channels,) baseband frequencies in Hz
        voltages: (n_ants, n_samples) the raw time-domain chunks, concatenated
    """
    sim = SimulatedStream(
        n_ants=len(ant_pos),
        sample_rate=SAMPLE_RATE,
        ant_positions=ant_pos,
        sources=sources,
        sky_freq=SKY_FREQ,
        snr=snr_db,
        signal_type=signal_type,
        freq=TONE_FREQ,
        seed=seed,
    )
    fengine = FEngine(n_channels=n_channels, window_type=window)

    chunks, spectra = [], []
    for chunk in sim.stream(chunk_size=n_channels * 4, max_chunks=n_chunks):
        chunks.append(chunk)
        spectra.append(fengine.process_chunk(chunk))

    return (
        np.concatenate(spectra, axis=1),
        fengine.get_channel_frequencies(SAMPLE_RATE),
        np.concatenate(chunks, axis=1),
    )


def correlate(channelised, n_ants, n_channels=N_CHANNELS):
    """Push every spectrum through the X-engine and return the integration."""
    xeng = XEngine(
        n_ants=n_ants,
        n_channels=n_channels,
        integration_time=1e9,        # never auto-flushes; we flush manually
        sample_rate=SAMPLE_RATE,
    )
    for spec_idx in range(channelised.shape[1]):
        xeng.accumulate(xeng.correlate_spectrum(channelised[:, spec_idx, :]))
    return xeng.get_integrated(), xeng.baselines


def predicted_phase(b_ij, s_hat, s0, channel_freqs):
    """Closed-form fringe phase for one baseline, per channel."""
    delta_tau = np.dot(b_ij, np.asarray(s_hat) - np.asarray(s0)) / C_LIGHT
    return wrap(2 * np.pi * (SKY_FREQ + channel_freqs) * delta_tau)


# ── 1 & 2: point-source phase, on and off the phase centre ──────────────────

class TestPointSourcePhase:
    """The core end-to-end accuracy tests."""

    def test_source_at_phase_centre_has_zero_phase(self):
        """A source at the phase centre must produce zero phase everywhere.

        Necessary but not sufficient — see test_off_pointing_phase.
        """
        s_hat = direction_from_zenith_angle(np.deg2rad(23.0), azimuth=np.deg2rad(41.0))
        channelised, freqs, _ = channelise([PointSource(s_hat)])

        delay = DelayEngine(ANT_POS, reference_freq=SKY_FREQ)
        delay.set_phase_center(s_hat)
        corrected = delay.apply_delays(channelised, freqs)

        vis, baselines = correlate(corrected, len(ANT_POS))

        for bl_idx, (i, j) in enumerate(baselines):
            if i == j:
                continue
            phase = np.angle(vis[bl_idx, TONE_BIN])
            assert np.abs(phase) < 1e-6, (
                f"baseline ({i},{j}) phase {phase:.3e} rad, expected 0"
            )

    def test_off_pointing_phase(self):
        """Mis-point the phase centre and predict the residual fringe phase.

        This is the test that a no-op delay engine fails. The expected phase
        is computed from geometry alone and never touches correlator code.
        """
        s_hat = direction_from_zenith_angle(np.deg2rad(18.0), azimuth=np.deg2rad(35.0))
        s0 = direction_from_zenith_angle(np.deg2rad(21.5), azimuth=np.deg2rad(35.0))

        channelised, freqs, _ = channelise([PointSource(s_hat)])

        delay = DelayEngine(ANT_POS, reference_freq=SKY_FREQ)
        delay.set_phase_center(s0)
        corrected = delay.apply_delays(channelised, freqs)

        vis, baselines = correlate(corrected, len(ANT_POS))

        checked = 0
        for bl_idx, (i, j) in enumerate(baselines):
            if i == j:
                continue
            b_ij = ANT_POS[i] - ANT_POS[j]
            expected = predicted_phase(b_ij, s_hat, s0, freqs)[TONE_BIN]
            measured = np.angle(vis[bl_idx, TONE_BIN])

            assert np.abs(wrap(measured - expected)) < 1e-6, (
                f"baseline ({i},{j}): measured {measured:+.6f} rad, "
                f"predicted {expected:+.6f} rad"
            )
            checked += 1

        assert checked == 6, "expected 6 cross-correlations for 4 antennas"

    def test_off_pointing_phase_is_actually_nonzero(self):
        """Guard: the off-pointing geometry must produce a real fringe.

        Without this, test_off_pointing_phase could silently degenerate into
        the zero-phase case and stop testing anything.
        """
        s_hat = direction_from_zenith_angle(np.deg2rad(18.0), azimuth=np.deg2rad(35.0))
        s0 = direction_from_zenith_angle(np.deg2rad(21.5), azimuth=np.deg2rad(35.0))

        phases = [
            predicted_phase(ANT_POS[i] - ANT_POS[j], s_hat, s0, np.zeros(1))[0]
            for i, j in get_baseline_indices(len(ANT_POS)) if i != j
        ]
        assert np.max(np.abs(phases)) > 0.5, (
            "test geometry produces negligible fringe — it would pass trivially"
        )

    def test_broadband_source_phase_across_all_channels(self):
        """Same prediction, but with a noise source so every channel carries power."""
        s_hat = direction_from_zenith_angle(np.deg2rad(30.0), azimuth=np.deg2rad(10.0))
        s0 = direction_from_zenith_angle(np.deg2rad(27.0), azimuth=np.deg2rad(10.0))

        channelised, freqs, _ = channelise(
            [PointSource(s_hat)], signal_type="noise", n_chunks=4
        )

        delay = DelayEngine(ANT_POS, reference_freq=SKY_FREQ)
        delay.set_phase_center(s0)
        corrected = delay.apply_delays(channelised, freqs)

        vis, baselines = correlate(corrected, len(ANT_POS))

        for bl_idx, (i, j) in enumerate(baselines):
            if i == j:
                continue
            b_ij = ANT_POS[i] - ANT_POS[j]
            expected = predicted_phase(b_ij, s_hat, s0, freqs)
            measured = np.angle(vis[bl_idx, :])
            residual = np.abs(wrap(measured - expected))

            # Fractional-sample envelope delay is applied circularly over the
            # chunk, so tolerance is looser than the exact tone case.
            assert np.max(residual) < 1e-3, (
                f"baseline ({i},{j}): max phase residual "
                f"{np.max(residual):.2e} rad in channel {np.argmax(residual)}"
            )


# ── 3: closure phase ────────────────────────────────────────────────────────

class TestClosurePhase:
    """Closure phase is zero for a point source and immune to antenna gains."""

    @staticmethod
    def _closure(vis, baselines, i, j, k):
        lookup = {(a, b): idx for idx, (a, b) in enumerate(baselines)}
        return wrap(
            np.angle(vis[lookup[(i, j)], TONE_BIN])
            + np.angle(vis[lookup[(j, k)], TONE_BIN])
            - np.angle(vis[lookup[(i, k)], TONE_BIN])
        )

    def test_closure_phase_is_zero_for_point_source(self):
        s_hat = direction_from_zenith_angle(np.deg2rad(15.0), azimuth=np.deg2rad(70.0))
        s0 = direction_from_zenith_angle(np.deg2rad(25.0), azimuth=np.deg2rad(50.0))

        channelised, freqs, _ = channelise([PointSource(s_hat)])
        delay = DelayEngine(ANT_POS, reference_freq=SKY_FREQ)
        delay.set_phase_center(s0)
        vis, baselines = correlate(delay.apply_delays(channelised, freqs), len(ANT_POS))

        for (i, j, k) in [(0, 1, 2), (0, 1, 3), (0, 2, 3), (1, 2, 3)]:
            closure = self._closure(vis, baselines, i, j, k)
            assert np.abs(closure) < 1e-6, (
                f"closure phase on triangle ({i},{j},{k}) is {closure:.3e} rad"
            )

    def test_closure_phase_survives_antenna_phase_errors(self):
        """Per-antenna phase errors cancel in closure. This is why closure is
        the standard diagnostic: it isolates correlator bugs from calibration
        errors."""
        s_hat = direction_from_zenith_angle(np.deg2rad(15.0), azimuth=np.deg2rad(70.0))
        s0 = direction_from_zenith_angle(np.deg2rad(25.0), azimuth=np.deg2rad(50.0))

        channelised, freqs, _ = channelise([PointSource(s_hat)])
        delay = DelayEngine(ANT_POS, reference_freq=SKY_FREQ)
        delay.set_phase_center(s0)
        corrected = delay.apply_delays(channelised, freqs)

        # Inject arbitrary, large per-antenna phase errors.
        gain_phase = np.array([0.0, 1.9, -2.4, 0.7])
        corrupted = corrected * np.exp(1j * gain_phase)[:, None, None]

        vis, baselines = correlate(corrupted, len(ANT_POS))

        for (i, j, k) in [(0, 1, 2), (0, 1, 3), (0, 2, 3), (1, 2, 3)]:
            closure = self._closure(vis, baselines, i, j, k)
            assert np.abs(closure) < 1e-6, (
                f"closure on ({i},{j},{k}) = {closure:.3e} rad under gain errors"
            )

        # Sanity: the per-baseline phases really were corrupted.
        lookup = {(a, b): idx for idx, (a, b) in enumerate(baselines)}
        clean, _ = correlate(corrected, len(ANT_POS))
        shifted = np.abs(wrap(
            np.angle(vis[lookup[(0, 1)], TONE_BIN])
            - np.angle(clean[lookup[(0, 1)], TONE_BIN])
        ))
        assert shifted > 1.0, "gain errors did not actually perturb the visibilities"


# ── 4: FX versus an independent XF implementation ───────────────────────────

class TestFXvsXF:
    """Cross-check the FX correlator against a lag-domain (XF) correlator.

    XF correlates in the time domain first and Fourier transforms the result.
    It shares no code with FEngine or XEngine, so agreement between the two is
    evidence about the implementation rather than about self-consistency.
    """

    @staticmethod
    def _xf_visibility(x_i, x_j):
        """Lag-domain cross-correlation, then FFT.

        For X[k] = sum_n x[n] exp(-2j*pi*k*n/N):

            X_i[k] * conj(X_j[k]) = FFT(r)[k],
            r[l] = sum_m x_i[(m + l) mod N] * conj(x_j[m])

        Computed here with explicit rolls and sums — no FFT of the inputs.
        """
        n = x_i.size
        lags = np.array([
            np.sum(np.roll(x_i, -l) * np.conj(x_j)) for l in range(n)
        ])
        return np.fft.fft(lags)

    def test_fx_matches_xf_on_all_baselines(self):
        sources = [
            PointSource(direction_from_zenith_angle(np.deg2rad(12.0)), amplitude=1.0),
            PointSource(direction_from_zenith_angle(np.deg2rad(40.0), np.deg2rad(80.0)),
                        amplitude=0.6),
        ]
        # Rectangular window and one spectrum per antenna keeps the identity exact.
        channelised, _, voltages = channelise(
            sources, signal_type="noise", window="rectangular", snr_db=25.0
        )

        n_ants = len(ANT_POS)
        vis_fx = XEngine(
            n_ants=n_ants, n_channels=N_CHANNELS,
            integration_time=1e9, sample_rate=SAMPLE_RATE,
        ).correlate_spectrum(channelised[:, 0, :])

        baselines = get_baseline_indices(n_ants)
        for bl_idx, (i, j) in enumerate(baselines):
            if i == j:
                continue
            vis_xf = self._xf_visibility(
                voltages[i, :N_CHANNELS], voltages[j, :N_CHANNELS]
            )
            rel = np.max(np.abs(vis_fx[bl_idx] - vis_xf)) / np.max(np.abs(vis_xf))
            assert rel < 1e-10, (
                f"FX and XF disagree on baseline ({i},{j}): "
                f"max relative difference {rel:.3e}"
            )


# ── 5: structural invariants ────────────────────────────────────────────────

class TestVisibilityInvariants:

    def test_autocorrelations_are_real_and_positive(self):
        channelised, freqs, _ = channelise(
            [PointSource(direction_from_zenith_angle(np.deg2rad(20.0)))],
            signal_type="noise", snr_db=15.0, n_chunks=2,
        )
        vis, baselines = correlate(channelised, len(ANT_POS))

        for bl_idx, (i, j) in enumerate(baselines):
            if i != j:
                continue
            assert np.all(vis[bl_idx].real > 0), f"autocorr {i} has non-positive power"
            assert np.allclose(vis[bl_idx].imag, 0.0), f"autocorr {i} has imaginary part"

    def test_conjugate_symmetry(self):
        """V_ji must equal conj(V_ij)."""
        channelised, _, _ = channelise(
            [PointSource(direction_from_zenith_angle(np.deg2rad(33.0), np.deg2rad(15.0)))],
            signal_type="noise", snr_db=25.0,
        )
        spectrum = channelised[:, 0, :]

        forward = XEngine(n_ants=2, n_channels=N_CHANNELS, integration_time=1e9,
                          sample_rate=SAMPLE_RATE).correlate_spectrum(spectrum[[0, 1]])
        reverse = XEngine(n_ants=2, n_channels=N_CHANNELS, integration_time=1e9,
                          sample_rate=SAMPLE_RATE).correlate_spectrum(spectrum[[1, 0]])

        # Baseline index 2 is the (0,1) cross-correlation in both orderings.
        assert np.allclose(forward[2], np.conj(reverse[2]), rtol=1e-12, atol=1e-12)

    def test_cauchy_schwarz_bound(self):
        """|V_ij|^2 <= V_ii * V_jj, with equality only for noise-free signals.

        Independent receiver noise adds power to the autocorrelations but not
        to the cross-correlations, so the ratio must sit just below 1. A ratio
        above 1 means the cross-correlations are picking up self-power —
        typically a conjugation or indexing error.
        """
        channelised, _, _ = channelise(
            [PointSource(direction_from_zenith_angle(np.deg2rad(24.0), np.deg2rad(95.0)))],
            signal_type="noise", snr_db=20.0, n_chunks=4,
        )
        vis, baselines = correlate(channelised, len(ANT_POS))
        autos = {i: vis[idx].real for idx, (i, j) in enumerate(baselines) if i == j}

        for bl_idx, (i, j) in enumerate(baselines):
            if i == j:
                continue
            ratio = np.abs(vis[bl_idx]) / np.sqrt(autos[i] * autos[j])
            assert np.all(ratio <= 1.0 + 1e-9), (
                f"baseline ({i},{j}) violates Cauchy-Schwarz: max ratio {ratio.max():.6f}"
            )
            assert ratio.max() > 0.5, (
                f"baseline ({i},{j}) shows no coherence: max ratio {ratio.max():.6f}"
            )

    def test_delay_compensation_preserves_amplitude(self):
        """Fringe stopping is a pure phase rotation; |V| must not change."""
        channelised, freqs, _ = channelise(
            [PointSource(direction_from_zenith_angle(np.deg2rad(28.0)))],
            signal_type="noise",
        )
        delay = DelayEngine(ANT_POS, reference_freq=SKY_FREQ)
        delay.set_phase_center(direction_from_zenith_angle(np.deg2rad(45.0)))
        corrected = delay.apply_delays(channelised, freqs)

        assert np.allclose(np.abs(corrected), np.abs(channelised), rtol=1e-12)


# ── 6: absolute amplitude / window gain ─────────────────────────────────────

class TestAmplitudeScale:
    """Pin the correlator's absolute amplitude scale.

    Windows are normalised to unit coherent gain, so the flux scale must be
    identical for every window. The FFT itself carries no ``1/N``, so
    amplitudes scale as ``n_channels**2`` — a documented convention that flux
    calibration absorbs.
    """

    @pytest.mark.parametrize("window", ["rectangular", "hanning", "hamming", "blackman"])
    def test_amplitude_is_independent_of_window(self, window):
        """A tone of amplitude A on an exact bin gives (A * n_channels)^2.

        The expected value comes from the normalisation convention, not from
        ``FEngine.window`` — deriving it from the object under test would make
        the assertion vacuous.
        """
        amplitude = 2.0
        s_hat = direction_from_zenith_angle(np.deg2rad(19.0), np.deg2rad(60.0))

        channelised, _, _ = channelise(
            [PointSource(s_hat, amplitude=amplitude)],
            signal_type="tone", window=window,
        )
        vis, baselines = correlate(channelised, len(ANT_POS))

        expected = (amplitude * N_CHANNELS) ** 2

        for bl_idx, (i, j) in enumerate(baselines):
            if i != j:
                continue
            measured = vis[bl_idx, TONE_BIN].real
            assert np.abs(measured - expected) / expected < 1e-6, (
                f"{window}: autocorr {i} peak {measured:.4e}, expected {expected:.4e}"
            )

    def test_windows_suppress_spectral_leakage(self):
        """The window must actually taper — check leakage, not just gain.

        Coherent-gain normalisation makes the on-bin amplitude identical for
        every window, so an amplitude test alone can no longer tell whether
        windowing happens at all. Leakage can: drive a tone half a bin off
        centre, where the transform is worst-case, and compare far-from-peak
        power. Sidelobes fall off as 1/d^2 for rectangular, 1/d^3 for Hanning,
        and far faster for Blackman.
        """
        s_hat = direction_from_zenith_angle(np.deg2rad(19.0), np.deg2rad(60.0))
        half_bin_freq = (TONE_BIN + 0.5) * SAMPLE_RATE / N_CHANNELS

        far = np.array([k for k in range(N_CHANNELS // 2)
                        if abs(k - (TONE_BIN + 0.5)) > 8])

        leakage = {}
        for window in ("rectangular", "hanning", "hamming", "blackman"):
            sim = SimulatedStream(
                n_ants=1, sample_rate=SAMPLE_RATE,
                ant_positions=ANT_POS[:1],
                sources=[PointSource(s_hat)],
                sky_freq=SKY_FREQ, snr=NOISELESS_DB,
                signal_type="tone", freq=half_bin_freq, seed=1,
            )
            fengine = FEngine(n_channels=N_CHANNELS, window_type=window)
            spectrum = fengine.process_chunk(
                next(sim.stream(chunk_size=N_CHANNELS * 4, max_chunks=1)))[0, 0]
            power = np.abs(spectrum) ** 2
            leakage[window] = float(power[far].mean() / power.max())

        # Every taper must be far below rectangular.
        assert leakage["hanning"] < leakage["rectangular"] / 1000, leakage
        assert leakage["hamming"] < leakage["rectangular"] / 10, leakage
        assert leakage["blackman"] < leakage["hanning"], leakage
        assert leakage["blackman"] < 1e-6, leakage

        # Hamming leaks *more* than Hanning far from the peak, despite its
        # lower first sidelobe: its far-field rolloff is 1/d^2 against
        # Hanning's 1/d^3. Asserting the counter-intuitive ordering pins the
        # window shapes themselves, not merely "some taper was applied".
        assert leakage["hamming"] > leakage["hanning"], leakage

    def test_cross_amplitude_equals_source_power(self):
        """|V_ij| for a single point source equals the autocorrelation power."""
        amplitude = 1.5
        s_hat = direction_from_zenith_angle(np.deg2rad(22.0), np.deg2rad(5.0))

        channelised, _, _ = channelise(
            [PointSource(s_hat, amplitude=amplitude)], window="rectangular",
        )
        vis, baselines = correlate(channelised, len(ANT_POS))

        expected = (amplitude * N_CHANNELS) ** 2
        for bl_idx, (i, j) in enumerate(baselines):
            if i == j:
                continue
            measured = np.abs(vis[bl_idx, TONE_BIN])
            assert np.abs(measured - expected) / expected < 1e-6, (
                f"baseline ({i},{j}) amplitude {measured:.4e}, expected {expected:.4e}"
            )
