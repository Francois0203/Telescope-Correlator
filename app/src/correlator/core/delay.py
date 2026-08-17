"""Geometric delay compensation (fringe stopping).

Conventions
-----------
Stated explicitly, because getting them wrong is the most common source of
silent correlator errors.

* Antenna positions ``r_i``: metres, shape ``(n_ants, 3)``, right-handed
  local frame (x=East, y=North, z=Up).
* Source direction ``s_hat``: unit vector from the array toward the source.
  Zenith is ``[0, 0, 1]``.
* Geometric advance of antenna *i*, in seconds::

      a_i(s_hat) = (r_i . s_hat) / c

  How far ahead of the array origin the wavefront reaches antenna *i*.
  Positive when the antenna is displaced toward the source.
* At sky frequency ``f_sky``, mixed to baseband channel ``f_ch``::

      X_i[k] = S[k] * exp(+2j*pi * (f_sky + f_ch) * a_i)

  Both terms appear. At 1.42 GHz over 1 kHz of bandwidth, ``f_sky`` beats
  ``f_ch`` by six orders of magnitude. Dropping it discards the whole
  fringe, not a small correction.
* Fringe stopping toward phase centre ``s0`` multiplies each antenna by
  ``exp(-2j*pi * (f_sky + f_ch) * a_i(s0))``.

For a point source at ``s_hat``, the visibility on baseline
``b_ij = r_i - r_j`` after stopping toward ``s0`` is::

    V_ij[k] = |S[k]|^2 * exp(+2j*pi * (f_sky + f_ch) * b_ij . (s_hat - s0) / c)

Zero phase when ``s_hat == s0``. That closed form is what
``tests_harness/integration/test_correlator_validation.py`` asserts against.
"""
from __future__ import annotations

import numpy as np
from typing import Optional
from scipy.constants import c as C_LIGHT


def calculate_geometric_delays(
    ant_positions: np.ndarray,
    source_direction: np.ndarray,
    wavelength: float = 1.0,
) -> np.ndarray:
    """Geometric advance of each antenna, in units of ``wavelength``.

    Args:
        ant_positions: Array shape (n_ants, 2 or 3) with antenna positions.
        source_direction: Vector shape (2 or 3) pointing toward the source.
        wavelength: Divisor applied to the projected path length.  Pass the
            observing wavelength in metres to get advances in wavelengths, or
            ``scipy.constants.c`` to get advances in seconds.

    Returns:
        Advances shape (n_ants,), referenced to antenna 0.

    Note:
        Referencing to antenna 0 is a convenience that keeps the numbers small.
        It has no effect on visibilities: a common offset subtracted from every
        antenna cancels in every baseline difference ``a_i - a_j``.
    """
    advances = (ant_positions @ source_direction) / wavelength
    return advances - advances[0]


class DelayEngine:
    """Delay compensation and phasing engine.

    Applies per-antenna, per-channel phase rotations to channelised data so
    that a source at the phase centre appears with zero phase on every
    baseline.
    """

    def __init__(
        self,
        ant_positions: np.ndarray,
        reference_freq: float = 1.0,
    ):
        """Initialize delay engine.

        Args:
            ant_positions: Antenna positions in metres, shape (n_ants, 3).
            reference_freq: Sky (RF) frequency in Hz that baseband was mixed
                down from. Sets the dominant term in the fringe phase, so it
                is not optional. Pass ``Config.center_freq``.
        """
        self.ant_positions = np.asarray(ant_positions, dtype=float)
        self.n_ants = self.ant_positions.shape[0]
        self.reference_freq = reference_freq

        self.c = C_LIGHT

        # Geometric advance per antenna, in seconds. See module docstring.
        self.current_delays = np.zeros(self.n_ants)
        self.phase_center = np.array([0.0, 0.0, 1.0])   # default: zenith
        self.set_phase_center(self.phase_center)

    def set_phase_center(self, direction: np.ndarray):
        """Set the phase tracking centre (source direction).

        Args:
            direction: Vector pointing toward the phase centre.  Normalised
                internally, so it need not be a unit vector.
        """
        direction = np.asarray(direction, dtype=float)
        self.phase_center = direction / np.linalg.norm(direction)

        projected = self.ant_positions @ self.phase_center      # metres
        projected = projected - projected[0]                    # ref to ant 0

        self.current_delays = projected / self.c                # seconds

        # Same quantity expressed in wavelengths at the reference frequency.
        wavelength = self.c / self.reference_freq
        self.current_delays_wavelengths = projected / wavelength

    def get_delays(self, freq_hz: Optional[float] = None) -> np.ndarray:
        """Return the geometric advance of each antenna in seconds.

        The optional ``freq_hz`` argument is accepted for API compatibility.
        Geometric advances are times and do not depend on frequency; the
        frequency dependence enters in :meth:`apply_delays`.
        """
        return self.current_delays

    def apply_delays(
        self,
        channelised_data: np.ndarray,
        channel_frequencies: np.ndarray,
    ) -> np.ndarray:
        """Apply fringe-stopping phase rotation to channelised data.

        Args:
            channelised_data: Shape (n_ants, n_spectra, n_channels).
            channel_frequencies: Baseband frequency of each channel (Hz), as
                returned by ``FEngine.get_channel_frequencies``.  These are
                offsets from ``reference_freq``, not absolute sky frequencies.

        Returns:
            Phase-corrected data, same shape and dtype.
        """
        n_ants, _, n_channels = channelised_data.shape

        if n_ants != self.n_ants:
            raise ValueError(f"Expected {self.n_ants} antennas, got {n_ants}")
        if channel_frequencies.shape[0] != n_channels:
            raise ValueError(
                f"Expected {n_channels} channel frequencies, "
                f"got {channel_frequencies.shape[0]}"
            )

        # Absolute sky frequency of each channel.
        sky_freqs = self.reference_freq + channel_frequencies       # (n_chan,)

        # phase[ant, chan] = 2*pi * f_sky_chan * advance_ant
        phases = 2 * np.pi * np.outer(self.current_delays, sky_freqs)
        phasor = np.exp(-1j * phases)                               # (n_ant, n_chan)

        # Broadcast over the spectrum axis.
        return channelised_data * phasor[:, np.newaxis, :]
