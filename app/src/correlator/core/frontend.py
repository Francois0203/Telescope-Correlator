"""Frontend: antenna data ingestion.

Two sources:
- Batch: load from files (numpy arrays, raw binary)
- Simulated: generate synthetic antenna voltages and stream them

The simulator produces **complex baseband voltages**, what a receiver gives
after mixing down from ``sky_freq``. Sign and unit conventions match
:mod:`correlator.core.delay`; see that module's docstring. For a point source
at ``s_hat`` with per-antenna advance ``a_i = (r_i . s_hat) / c`` seconds::

    x_i(t) = s(t + a_i) * exp(+2j*pi * f_sky * a_i)

``s(t)`` is the baseband envelope shared by all antennas. The
``exp(2j*pi*f_sky*a_i)`` factor is the fringe term the delay engine removes.
Without it, fringe stopping has nothing to do and no end-to-end test of the
delay stage means anything.

Receiver noise is added **independently per antenna**, so it correlates only
on the autocorrelations. That is what makes cross-correlation a measurement.
"""
from __future__ import annotations

import numpy as np
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator, Optional, Sequence
import time

from scipy.constants import c as C_LIGHT


@dataclass
class PointSource:
    """An unresolved source at a fixed direction.

    Attributes:
        direction: 3-vector pointing from the array toward the source.
            Normalised on construction.  Zenith is ``[0, 0, 1]``.
        amplitude: Voltage amplitude (arbitrary units).  Visibility amplitude
            for this source is ``amplitude**2``.
    """
    direction: np.ndarray
    amplitude: float = 1.0

    def __post_init__(self):
        d = np.asarray(self.direction, dtype=float).ravel()
        if d.size == 2:                       # accept 2-D, assume horizontal
            d = np.array([d[0], d[1], 0.0])
        if d.size != 3:
            raise ValueError(f"direction must have 2 or 3 components, got {d.size}")
        norm = np.linalg.norm(d)
        if norm == 0:
            raise ValueError("direction must be a non-zero vector")
        self.direction = d / norm

    def advances(self, ant_positions: np.ndarray) -> np.ndarray:
        """Geometric advance (seconds) of each antenna for this source."""
        return (ant_positions @ self.direction) / C_LIGHT


def direction_from_zenith_angle(theta: float, azimuth: float = 0.0) -> np.ndarray:
    """Unit vector at zenith angle ``theta`` (radians), measured from +z.

    ``theta=0`` is zenith; ``theta=pi/2`` is the horizon.  ``azimuth`` rotates
    within the x-y plane from +x toward +y.
    """
    return np.array([
        np.sin(theta) * np.cos(azimuth),
        np.sin(theta) * np.sin(azimuth),
        np.cos(theta),
    ])


def _as_3d(positions: np.ndarray) -> np.ndarray:
    """Promote (n, 2) antenna positions to (n, 3) by appending z = 0."""
    positions = np.asarray(positions, dtype=float)
    if positions.ndim != 2:
        raise ValueError(f"ant_positions must be 2D, got shape {positions.shape}")
    if positions.shape[1] == 2:
        positions = np.hstack([positions, np.zeros((positions.shape[0], 1))])
    if positions.shape[1] != 3:
        raise ValueError(f"ant_positions must have 2 or 3 columns, got {positions.shape[1]}")
    return positions


class DataSource:
    """Base class for data sources."""

    def __init__(self, n_ants: int, sample_rate: float):
        self.n_ants = n_ants
        self.sample_rate = sample_rate

    def stream(self, chunk_size: int) -> Iterator[np.ndarray]:
        """Yield chunks of data shape (n_ants, chunk_size)."""
        raise NotImplementedError


class SimulatedStream(DataSource):
    """Simulated streaming data source with synthetic antenna voltages.

    Generates complex baseband voltages for N antennas observing one or more
    point sources, with physically correct geometric delays.
    """

    def __init__(
        self,
        n_ants: int,
        sample_rate: float,
        source_angles: Optional[Sequence[float]] = None,
        freq: float = 1.0,
        snr: float = 20.0,
        ant_positions: Optional[np.ndarray] = None,
        seed: int = 0,
        sources: Optional[Sequence[PointSource]] = None,
        sky_freq: float = 0.0,
        signal_type: str = "tone",
    ):
        """Initialise the simulator.

        Args:
            n_ants: Number of antennas.
            sample_rate: Baseband sample rate in Hz.
            source_angles: Convenience alternative to ``sources``: a list of
                zenith angles in radians, each becoming a unit-amplitude point
                source in the x-z plane.  ``0.0`` is zenith.  Ignored if
                ``sources`` is given.
            freq: Baseband frequency of the tone, in Hz (``signal_type="tone"``).
            snr: Signal-to-noise ratio in **decibels**, matching the units
                documented for ``Config.snr``.  Use ``snr <= 0`` semantics via
                ``add_noise=False``-style by passing a very large value for a
                noiseless run.
            ant_positions: Antenna positions in metres, shape (n_ants, 2 or 3).
                Defaults to a 10 m radius circle in the z=0 plane.
            seed: RNG seed for receiver noise and the noise envelope.
            sources: Explicit list of :class:`PointSource`.  Takes precedence
                over ``source_angles``.
            sky_freq: Sky (RF) frequency in Hz that baseband was mixed down
                from.  Must match the ``reference_freq`` given to
                :class:`~correlator.core.delay.DelayEngine`. Defaults to 0,
                which produces no fringe term. Useful for isolating the
                channeliser, but not a meaningful end-to-end test.
            signal_type: ``"tone"`` for a monochromatic baseband tone (exact,
                good for analytic tests) or ``"noise"`` for band-limited
                complex Gaussian noise (realistic, exercises all channels).
        """
        super().__init__(n_ants, sample_rate)

        self.freq = freq
        self.snr_db = snr
        self.seed = seed
        self.sky_freq = sky_freq
        self.signal_type = signal_type
        self.rng = np.random.default_rng(seed)

        if ant_positions is None:
            angles = np.linspace(0, 2 * np.pi, n_ants, endpoint=False)
            ant_positions = np.stack([10 * np.cos(angles), 10 * np.sin(angles)], axis=1)
        self.ant_positions = _as_3d(ant_positions)

        if self.ant_positions.shape[0] != n_ants:
            raise ValueError(
                f"ant_positions has {self.ant_positions.shape[0]} rows "
                f"but n_ants is {n_ants}"
            )

        if sources is not None:
            self.sources = list(sources)
        else:
            angles = [0.0] if source_angles is None else list(source_angles)
            self.sources = [
                PointSource(direction_from_zenith_angle(theta)) for theta in angles
            ]

        if signal_type not in ("tone", "noise"):
            raise ValueError(f"signal_type must be 'tone' or 'noise', got {signal_type!r}")

        # A tone above Nyquist aliases. The delay applied here would use the
        # un-aliased frequency while the correlator de-rotates the aliased
        # channel, leaving a spurious residual phase of
        # 2*pi*sample_rate*advance. Real receivers band-limit before sampling,
        # so reject the input rather than silently producing it.
        if signal_type == "tone" and abs(freq) > sample_rate / 2:
            raise ValueError(
                f"tone frequency {freq} Hz exceeds Nyquist ({sample_rate / 2} Hz) "
                f"for sample_rate {sample_rate} Hz"
            )

        # Pre-compute per-source geometric advances (seconds), shape (n_ants,).
        self._advances = [src.advances(self.ant_positions) for src in self.sources]

        self.sample_counter = 0

    # ── envelope generation ─────────────────────────────────────────────────
    def _sky_signal(self, t: np.ndarray, chunk_size: int) -> np.ndarray:
        """Sky contribution at every antenna for this chunk.

        Returns:
            Complex array shape (n_ants, chunk_size).
        """
        signals = np.zeros((self.n_ants, chunk_size), dtype=np.complex128)

        if self.signal_type == "noise":
            # Baseband frequency grid for this chunk, used to delay the
            # envelope exactly in the frequency domain.
            f_bb = np.fft.fftfreq(chunk_size, d=1 / self.sample_rate)

        for src, advance in zip(self.sources, self._advances):
            # Fringe term: exp(+2j*pi*f_sky*a_i). Dominant term when the array
            # observes at RF and the delays are sub-sample.
            fringe = np.exp(2j * np.pi * self.sky_freq * advance)      # (n_ants,)

            if self.signal_type == "tone":
                # s(t + a) = exp(2j*pi*f_bb*(t + a)). Closed form, exact.
                envelope = np.exp(2j * np.pi * self.freq * t)          # (chunk,)
                tone_delay = np.exp(2j * np.pi * self.freq * advance)  # (n_ants,)
                contribution = np.outer(src.amplitude * fringe * tone_delay, envelope)
            else:
                # Band-limited complex Gaussian envelope, shared by all
                # antennas, delayed per antenna in the frequency domain.
                envelope = (
                    self.rng.normal(size=chunk_size)
                    + 1j * self.rng.normal(size=chunk_size)
                ) / np.sqrt(2)
                spectrum = np.fft.fft(envelope)                        # (chunk,)
                # exp(+2j*pi*f*a) advances the envelope by a seconds.
                shift = np.exp(2j * np.pi * np.outer(advance, f_bb))   # (n_ants, chunk)
                delayed = np.fft.ifft(spectrum[np.newaxis, :] * shift, axis=1)
                contribution = src.amplitude * fringe[:, np.newaxis] * delayed

            signals += contribution

        return signals

    def stream(
        self,
        chunk_size: int,
        max_chunks: Optional[int] = None,
        realtime: bool = False,
    ) -> Iterator[np.ndarray]:
        """Generate and yield data chunks.

        Args:
            chunk_size: Number of samples per chunk.
            max_chunks: Maximum number of chunks to generate (None = infinite).
            realtime: If True, sleep between chunks to mimic real-time capture.

        Yields:
            Complex arrays of shape (n_ants, chunk_size).
        """
        chunk_count = 0
        snr_linear = 10 ** (self.snr_db / 10.0)

        while max_chunks is None or chunk_count < max_chunks:
            t_start = self.sample_counter / self.sample_rate
            t = t_start + np.arange(chunk_size) / self.sample_rate

            signals = self._sky_signal(t, chunk_size)

            # Receiver noise: independent per antenna, so it does not
            # correlate between antennas.
            signal_power = np.mean(np.abs(signals) ** 2)
            if snr_linear > 0 and signal_power > 0:
                noise_std = np.sqrt(signal_power / snr_linear)
                noise = (
                    self.rng.normal(scale=noise_std, size=signals.shape)
                    + 1j * self.rng.normal(scale=noise_std, size=signals.shape)
                ) / np.sqrt(2)
                signals = signals + noise

            self.sample_counter += chunk_size
            chunk_count += 1

            if realtime:
                time.sleep(chunk_size / self.sample_rate)

            yield signals


class BatchFileSource(DataSource):
    """Load data from batch files.

    Supports numpy .npy files with shape (n_ants, n_samples).
    """

    def __init__(self, file_path: str | Path, sample_rate: float):
        self.file_path = Path(file_path)

        # Load file to get metadata
        data = np.load(self.file_path)
        if data.ndim != 2:
            raise ValueError(f"Expected 2D array (n_ants, n_samples), got shape {data.shape}")

        n_ants = data.shape[0]
        super().__init__(n_ants, sample_rate)

        self.data = data
        self.n_samples = data.shape[1]

    def stream(self, chunk_size: int) -> Iterator[np.ndarray]:
        """Yield chunks from loaded data."""
        n_chunks = self.n_samples // chunk_size

        for i in range(n_chunks):
            start_idx = i * chunk_size
            end_idx = start_idx + chunk_size
            yield self.data[:, start_idx:end_idx]

        # Yield remaining samples if any
        remaining = self.n_samples % chunk_size
        if remaining > 0:
            yield self.data[:, -remaining:]
