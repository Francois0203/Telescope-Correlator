"""Independent analytic oracle for interferometer visibilities.

This module is deliberately written from the measurement equation alone. It
imports nothing from ``correlator`` and shares no code with it. If the
correlator and this oracle agree, that is evidence about the implementation;
if the oracle imported correlator internals, agreement would prove nothing.

Measurement equation
--------------------
An antenna at ``r_i`` observing a point source at unit direction ``s`` sees a
geometric advance ``a_i(s) = (r_i . s) / c`` seconds. After channelisation the
antenna voltage in the channel at absolute sky frequency ``f`` carries a phase
``exp(+2j*pi*f*a_i(s))``; fringe stopping toward ``s0`` removes
``exp(+2j*pi*f*a_i(s0))``. Writing ``d_i(s) = a_i(s) - a_i(s0)``:

    V_ij[k] = G * sum_s sum_s' A_s A_s'
                  exp(2j*pi*f_k * (d_i(s) - d_j(s')))

For mutually independent sources the ``s != s'`` terms average to zero over
many spectra, leaving the familiar

    V_ij[k] = G * sum_s A_s^2 exp(2j*pi*f_k * b_ij . (s - s0) / c)

``G`` is the channeliser's power gain, which depends on the signal statistics:

* a coherent tone that lands exactly on a bin accumulates as ``sum(w)**2``
* white noise accumulates as ``sum(w**2)``

Conflating those two is a common way to get visibility amplitudes wrong by a
constant factor, so both are modelled explicitly here.
"""
from __future__ import annotations

import numpy as np
from dataclasses import dataclass, field
from typing import Literal, Sequence

C_LIGHT = 299792458.0          # m/s, exact by SI definition

WINDOWS = {
    "rectangular": np.ones,
    "hanning": np.hanning,
    "hamming": np.hamming,
    "blackman": np.blackman,
}


@dataclass
class Scenario:
    """A complete, self-describing observation to validate against.

    Everything the correlator and the oracle both need lives here, so the two
    can never silently disagree about the setup they are comparing.
    """
    name: str
    ant_positions: np.ndarray           # (n_ants, 3) metres, ENU
    source_directions: np.ndarray       # (n_sources, 3) unit vectors
    source_amplitudes: np.ndarray       # (n_sources,) voltage amplitudes
    phase_center: np.ndarray            # (3,) unit vector
    sky_freq: float                     # Hz
    sample_rate: float                  # Hz
    n_channels: int
    window: str = "rectangular"
    signal_type: Literal["tone", "noise"] = "tone"
    tone_bin: int = 7                   # tone lands exactly on this FFT bin
    n_chunks: int = 1
    snr_db: float = 200.0

    def __post_init__(self):
        self.ant_positions = np.atleast_2d(np.asarray(self.ant_positions, float))
        dirs = np.atleast_2d(np.asarray(self.source_directions, float))
        self.source_directions = dirs / np.linalg.norm(dirs, axis=1, keepdims=True)
        self.source_amplitudes = np.atleast_1d(
            np.asarray(self.source_amplitudes, float))
        pc = np.asarray(self.phase_center, float)
        self.phase_center = pc / np.linalg.norm(pc)

        if self.window not in WINDOWS:
            raise ValueError(f"unknown window {self.window!r}")
        if self.signal_type == "tone" and self.tone_bin >= self.n_channels // 2:
            raise ValueError(
                f"tone_bin {self.tone_bin} is at or above Nyquist "
                f"(n_channels/2 = {self.n_channels // 2}); it would alias"
            )

    @property
    def n_ants(self) -> int:
        return self.ant_positions.shape[0]

    @property
    def tone_freq(self) -> float:
        return self.tone_bin * self.sample_rate / self.n_channels

    @property
    def channel_freqs(self) -> np.ndarray:
        """Baseband frequency of each channel (Hz), FFT bin order."""
        return np.fft.fftfreq(self.n_channels, d=1.0 / self.sample_rate)

    @property
    def baselines(self) -> list[tuple[int, int]]:
        """Autocorrelations first, then i<j cross-correlations.

        Must match the correlator's ordering. Verified in
        ``run_validation.py`` rather than assumed.
        """
        n = self.n_ants
        return [(i, i) for i in range(n)] + [
            (i, j) for i in range(n) for j in range(i + 1, n)
        ]

    def advances(self, direction: np.ndarray) -> np.ndarray:
        """Geometric advance (seconds) of each antenna toward ``direction``."""
        return (self.ant_positions @ direction) / C_LIGHT


def normalised_window(name: str, n: int) -> np.ndarray:
    """Window scaled to unit coherent gain, matching the F-engine convention.

    Derived here from NumPy directly rather than imported from the correlator,
    so this stays an independent implementation of the same stated convention
    rather than a mirror of the code under test.
    """
    w = WINDOWS[name](n)
    return w * (n / np.sum(w))


def channel_gain(scenario: Scenario) -> float:
    """Power gain the channeliser applies, given the signal statistics."""
    w = normalised_window(scenario.window, scenario.n_channels)
    if scenario.signal_type == "tone":
        return float(np.sum(w) ** 2)        # coherent: amplitudes add
    return float(np.sum(w ** 2))            # incoherent: powers add


def predict(scenario: Scenario) -> np.ndarray:
    """Analytic visibilities for a scenario.

    Returns:
        Complex array (n_baselines, n_channels) in the scenario's baseline
        order, directly comparable to the correlator's integrated output.
    """
    sc = scenario
    gain = channel_gain(sc)
    f_abs = sc.sky_freq + sc.channel_freqs                    # (n_chan,)

    # d[s, i] = advance of antenna i toward source s, minus its advance
    # toward the phase centre.
    a_pc = sc.advances(sc.phase_center)                        # (n_ants,)
    d = np.stack([sc.advances(s) - a_pc for s in sc.source_directions])

    n_bl = len(sc.baselines)
    vis = np.zeros((n_bl, sc.n_channels), dtype=np.complex128)

    coherent = sc.signal_type == "tone"

    for bl_idx, (i, j) in enumerate(sc.baselines):
        if coherent:
            # All sources share one envelope, so s != s' cross terms survive.
            # E_i = sum_s A_s exp(2j pi f d[s,i]); V_ij = G * E_i * conj(E_j)
            e_i = np.sum(
                sc.source_amplitudes[:, None]
                * np.exp(2j * np.pi * np.outer(d[:, i], f_abs)), axis=0)
            e_j = np.sum(
                sc.source_amplitudes[:, None]
                * np.exp(2j * np.pi * np.outer(d[:, j], f_abs)), axis=0)
            vis[bl_idx] = gain * e_i * np.conj(e_j)
        else:
            # Independent envelopes per source: only s == s' survives averaging.
            delta = d[:, i] - d[:, j]                          # (n_sources,)
            vis[bl_idx] = gain * np.sum(
                (sc.source_amplitudes ** 2)[:, None]
                * np.exp(2j * np.pi * np.outer(delta, f_abs)), axis=0)

    return vis


def expected_noise_floor(scenario: Scenario) -> float:
    """Fractional visibility error expected from receiver noise alone.

    Used to set comparison tolerances honestly: a residual below this is
    consistent with noise, not evidence of a correlator error.
    """
    snr_linear = 10 ** (scenario.snr_db / 10.0)
    n_spectra = scenario.n_chunks * 4          # chunk is 4 FFT windows
    if not np.isfinite(snr_linear) or snr_linear <= 0:
        return np.inf
    return float(np.sqrt(2.0 / (snr_linear * n_spectra)))
