"""FX correlator pipeline.

Stages
------
1. Frontend   — generate or load time-domain antenna signals
2. F-engine   — windowed FFT → frequency channels
3. Delay      — geometric delay compensation (fringe stopping)
4. X-engine   — cross-multiply → visibilities, integrate over time
5. Output     — save visibility products
"""
from __future__ import annotations
from pathlib import Path

import numpy as np

from correlator.config import Config
from correlator.core.frontend import SimulatedStream, BatchFileSource
from correlator.core.fengine import FEngine
from correlator.core.xengine import XEngine
from correlator.core.delay import DelayEngine

_CHUNK_MULTIPLIER = 4   # process this many FFT windows per chunk


def run(cfg: Config) -> int:
    """Execute the FX pipeline. Returns 0 on success."""
    cfg.validate()

    output_dir = Path(cfg.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    chunk_size = cfg.n_channels * _CHUNK_MULTIPLIER

    print(f"Antennas        : {cfg.n_ants}")
    print(f"Channels        : {cfg.n_channels}  (window: {cfg.window})")
    print(f"Sample rate     : {cfg.sample_rate} Hz")
    print(f"Centre freq     : {cfg.center_freq / 1e6:.3f} MHz")
    print(f"Integration     : {cfg.integration_time} s")
    print(f"Mode            : {cfg.mode}")
    print(f"Output          : {output_dir}/")
    print()

    # ── Frontend ────────────────────────────────────────────────────────────
    ant_pos_2d = cfg.ant_positions()

    if cfg.mode == "simulate":
        total_samples = int(cfg.duration * cfg.sample_rate)
        max_chunks = max(1, total_samples // chunk_size)
        source = SimulatedStream(
            n_ants=cfg.n_ants,
            sample_rate=cfg.sample_rate,
            ant_positions=ant_pos_2d,
            source_angles=[0.0, np.pi / 6],   # two point sources
            snr=cfg.snr,
        ).stream(chunk_size=chunk_size, max_chunks=max_chunks)
    else:
        source = BatchFileSource(cfg.input_file, cfg.sample_rate).stream(chunk_size)

    # ── F-engine ─────────────────────────────────────────────────────────────
    fengine = FEngine(n_channels=cfg.n_channels, window_type=cfg.window)
    freq_channels = fengine.get_channel_frequencies(cfg.sample_rate)

    # ── Delay engine ─────────────────────────────────────────────────────────
    ant_pos_3d = np.hstack([ant_pos_2d, np.zeros((cfg.n_ants, 1))])
    delay_engine = DelayEngine(ant_positions=ant_pos_3d, reference_freq=cfg.center_freq)
    delay_engine.set_phase_center(np.array([1.0, 0.0, 0.0]))

    # ── X-engine ─────────────────────────────────────────────────────────────
    xengine = XEngine(
        n_ants=cfg.n_ants,
        n_channels=cfg.n_channels,
        integration_time=cfg.integration_time,
        sample_rate=cfg.sample_rate,
    )

    n_integrations = 0

    # ── Processing loop ──────────────────────────────────────────────────────
    for chunk in source:
        # F-engine: time domain → frequency channels
        channelised = fengine.process_chunk(chunk)          # (n_ants, n_spectra, n_channels)

        # Delay compensation: fringe stopping
        channelised = delay_engine.apply_delays(channelised, freq_channels)

        # X-engine: cross-multiply and integrate
        for spec_idx in range(channelised.shape[1]):
            vis = xengine.correlate_spectrum(channelised[:, spec_idx, :])
            xengine.accumulate(vis)

            if xengine.is_ready():
                integrated = xengine.get_integrated()
                n_integrations += 1
                _save(integrated, output_dir / f"visibility_{n_integrations:04d}", cfg.output_format)
                print(f"  Integration {n_integrations:4d}  saved")

    cfg.to_yaml(output_dir / "config.yaml")
    print(f"\nComplete: {n_integrations} integrations written to {output_dir}/")
    return 0


def _save(vis: np.ndarray, path: Path, fmt: str):
    if fmt == "npy":
        np.save(f"{path}.npy", vis)
    elif fmt in ("hdf5", "h5"):
        try:
            import h5py
            with h5py.File(f"{path}.h5", "w") as f:
                f.create_dataset("visibilities", data=vis)
                f.attrs["shape"] = vis.shape
        except ImportError:
            print("Warning: h5py not installed, saving as .npy")
            np.save(f"{path}.npy", vis)
    elif fmt == "fits":
        try:
            from astropy.io import fits
            hdul = fits.HDUList([
                fits.PrimaryHDU(),
                fits.ImageHDU(vis.real, name="REAL"),
                fits.ImageHDU(vis.imag, name="IMAG"),
            ])
            hdul.writeto(f"{path}.fits", overwrite=True)
        except ImportError:
            print("Warning: astropy not installed, saving as .npy")
            np.save(f"{path}.npy", vis)
    else:
        np.save(f"{path}.npy", vis)
