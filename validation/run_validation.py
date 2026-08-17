"""Validate the correlator against independent references.

Usage
-----
    python validation/run_validation.py                # analytic oracle only
    python validation/run_validation.py --with-pyuvsim # add the pyuvsim tier
    python validation/run_validation.py --json out.json

Exits 0 if every scenario passes, 1 otherwise, so it can be wired into CI.

This directory is entirely optional. Nothing under ``app/src/correlator``
imports it; deleting ``validation/`` leaves the correlator and its test suite
working unchanged.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, asdict
from pathlib import Path

import numpy as np

# Make the correlator importable when run from a source checkout without
# `pip install -e app/src/`.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app" / "src"))

from correlator.core.fengine import FEngine                       # noqa: E402
from correlator.core.xengine import XEngine, get_baseline_indices  # noqa: E402
from correlator.core.delay import DelayEngine                     # noqa: E402
from correlator.core.frontend import SimulatedStream, PointSource  # noqa: E402

from oracle import Scenario, predict, expected_noise_floor        # noqa: E402


def unit(zenith_deg: float, azimuth_deg: float = 0.0) -> np.ndarray:
    """Unit direction vector from zenith angle and azimuth, in degrees."""
    th, az = np.deg2rad(zenith_deg), np.deg2rad(azimuth_deg)
    return np.array([np.sin(th) * np.cos(az), np.sin(th) * np.sin(az), np.cos(th)])


# An irregular, genuinely 3-D array. Regular or integer layouts can make
# geometric phases cancel by accident and turn a validation into a tautology.
ARRAY_4 = np.array([
    [  0.00,   0.00,  0.00],
    [ 23.70,  -8.10,  1.30],
    [ -5.20,  31.40, -2.70],
    [ 14.90,  19.60,  0.80],
])

ARRAY_6 = np.vstack([ARRAY_4, [[-31.05, -17.40, 3.60], [ 42.15,   6.85, -1.95]]])


def scenarios() -> list[Scenario]:
    """The validation set. Each entry probes a different failure mode."""
    return [
        Scenario(
            name="on-axis point source",
            ant_positions=ARRAY_4,
            source_directions=[unit(23.0, 41.0)],
            source_amplitudes=[1.0],
            phase_center=unit(23.0, 41.0),
            sky_freq=1.42e9, sample_rate=1024.0, n_channels=64,
        ),
        Scenario(
            name="off-axis by 3.5 deg (fringe must survive)",
            ant_positions=ARRAY_4,
            source_directions=[unit(18.0, 35.0)],
            source_amplitudes=[1.0],
            phase_center=unit(21.5, 35.0),
            sky_freq=1.42e9, sample_rate=1024.0, n_channels=64,
        ),
        Scenario(
            name="two sources, hanning window",
            ant_positions=ARRAY_4,
            source_directions=[unit(10.0, 0.0), unit(35.0, 120.0)],
            source_amplitudes=[1.0, 0.4],
            phase_center=unit(10.0, 0.0),
            sky_freq=1.42e9, sample_rate=1024.0, n_channels=64,
            window="hanning",
        ),
        Scenario(
            name="6 antennas, 15 baselines, blackman",
            ant_positions=ARRAY_6,
            source_directions=[unit(27.0, 210.0)],
            source_amplitudes=[1.3],
            phase_center=unit(24.0, 205.0),
            sky_freq=1.42e9, sample_rate=1024.0, n_channels=128,
            window="blackman", tone_bin=13,
        ),
        Scenario(
            name="broadband noise source, all channels",
            ant_positions=ARRAY_4,
            source_directions=[unit(30.0, 10.0)],
            source_amplitudes=[1.0],
            phase_center=unit(27.0, 10.0),
            sky_freq=1.42e9, sample_rate=1024.0, n_channels=64,
            signal_type="noise", n_chunks=64,
        ),
        Scenario(
            name="low elevation, long baselines (many fringe turns)",
            ant_positions=ARRAY_6 * 8.0,
            source_directions=[unit(72.0, 300.0)],
            source_amplitudes=[1.0],
            phase_center=unit(70.0, 297.0),
            sky_freq=1.42e9, sample_rate=1024.0, n_channels=64,
        ),
    ]


def run_correlator(sc: Scenario) -> np.ndarray:
    """Run the full FX chain for a scenario and return integrated visibilities."""
    sim = SimulatedStream(
        n_ants=sc.n_ants,
        sample_rate=sc.sample_rate,
        ant_positions=sc.ant_positions,
        sources=[PointSource(d, a) for d, a
                 in zip(sc.source_directions, sc.source_amplitudes)],
        sky_freq=sc.sky_freq,
        snr=sc.snr_db,
        signal_type=sc.signal_type,
        freq=sc.tone_freq if sc.signal_type == "tone" else 1.0,
        seed=1,
    )
    fengine = FEngine(n_channels=sc.n_channels, window_type=sc.window)
    delay = DelayEngine(sc.ant_positions, reference_freq=sc.sky_freq)
    delay.set_phase_center(sc.phase_center)
    xeng = XEngine(n_ants=sc.n_ants, n_channels=sc.n_channels,
                   integration_time=1e9, sample_rate=sc.sample_rate)

    # The oracle assumes the correlator's baseline ordering. Check it rather
    # than trust it. A silent reordering would look like a phase error.
    if xeng.baselines != sc.baselines:
        raise AssertionError(
            "baseline ordering mismatch between correlator and oracle:\n"
            f"  correlator: {xeng.baselines}\n  oracle:     {sc.baselines}"
        )

    freqs = fengine.get_channel_frequencies(sc.sample_rate)
    for chunk in sim.stream(chunk_size=sc.n_channels * 4, max_chunks=sc.n_chunks):
        corrected = delay.apply_delays(fengine.process_chunk(chunk), freqs)
        for spec_idx in range(corrected.shape[1]):
            xeng.accumulate(xeng.correlate_spectrum(corrected[:, spec_idx, :]))
    return xeng.get_integrated()


@dataclass
class Result:
    scenario: str
    n_baselines: int
    max_phase_error_rad: float
    amplitude_bias: float           # mean(|V_meas| / |V_pred|) - 1
    amplitude_scatter: float        # std of that ratio
    scatter_expected: float         # theoretical scatter, 1/sqrt(n_spectra)
    fringe_range_rad: float
    decisive: bool                  # does this scenario contain a real fringe?
    passed: bool
    note: str = ""


def compare(sc: Scenario, measured: np.ndarray, expected: np.ndarray) -> Result:
    """Compare correlator output to the oracle over the channels that matter.

    Amplitude is judged by **bias and scatter**, not by a max-error threshold.
    With N averaged spectra the visibility amplitude has an irreducible
    relative scatter of ~1/sqrt(N); the maximum over many baselines and
    channels is then several sigma by construction, so a max-error tolerance
    either has to be set absurdly loose or it flags correct behaviour. Testing
    that the mean ratio is 1 (no systematic scale error) and that the scatter
    matches theory (no excess variance) is both stricter and honest.
    """
    n_spectra = sc.n_chunks * 4          # each chunk holds 4 FFT windows

    if sc.signal_type == "tone":
        chans = [sc.tone_bin]
        tol_phase = 1e-6
        scatter_expected = 0.0
    else:
        chans = list(range(sc.n_channels))
        # Phase is exact even for a random envelope (a real, positive |S[k]|^2
        # factors out), so the only phase error is the circular fractional
        # delay applied per chunk.
        tol_phase = 2e-3
        scatter_expected = 1.0 / np.sqrt(n_spectra)

    cross = [k for k, (i, j) in enumerate(sc.baselines) if i != j]
    m = measured[np.ix_(cross, chans)]
    e = expected[np.ix_(cross, chans)]

    max_phase = float(np.abs(np.angle(m * np.conj(e))).max())

    ratio = np.abs(m) / np.maximum(np.abs(e), 1e-300)
    bias = float(ratio.mean() - 1.0)
    scatter = float(ratio.std())

    # Is there a fringe to detect at all?
    fringe = float(np.ptp(np.angle(e)))
    decisive = fringe > 1e-6

    if sc.signal_type == "tone":
        amp_ok = abs(bias) < 1e-6 and scatter < 1e-6
        note = "" if decisive else "not decisive on its own: on-axis, zero fringe by construction"
    else:
        n_samples = ratio.size
        # Bias must vanish faster than the per-sample scatter.
        amp_ok = (abs(bias) < 4 * scatter_expected / np.sqrt(n_samples)
                  and 0.5 * scatter_expected < scatter < 2.0 * scatter_expected)
        note = f"statistical: {n_spectra} spectra, expected scatter {scatter_expected:.3f}"

    return Result(
        scenario=sc.name,
        n_baselines=len(cross),
        max_phase_error_rad=max_phase,
        amplitude_bias=bias,
        amplitude_scatter=scatter,
        scatter_expected=scatter_expected,
        fringe_range_rad=fringe,
        decisive=decisive,
        passed=bool(max_phase < tol_phase and amp_ok),
        note=note,
    )


def print_report(results: list[Result]) -> None:
    print()
    print("Tier 1: analytic oracle (independent implementation of the")
    print("         measurement equation; shares no code with the correlator)")
    print()
    header = (f"{'scenario':<48}{'bl':>4}{'max dphase':>12}"
              f"{'amp bias':>11}{'scatter':>9}{'fringe':>8}  result")
    print(header)
    print("-" * len(header))
    for r in results:
        status = "pass" if r.passed else "FAIL"
        if r.passed and not r.decisive:
            status = "pass*"
        scatter = (f"{r.amplitude_scatter:>9.4f}" if r.scatter_expected
                   else f"{r.amplitude_scatter:>9.1e}")
        print(f"{r.scenario:<48}{r.n_baselines:>4}"
              f"{r.max_phase_error_rad:>12.1e}{r.amplitude_bias:>+11.2e}{scatter}"
              f"{r.fringe_range_rad:>8.2f}  {status}")
    print()

    n_pass = sum(r.passed for r in results)
    n_dec = sum(r.passed and r.decisive for r in results)
    print(f"{n_pass}/{len(results)} scenarios passed; "
          f"{n_dec} of them contain a real fringe and are individually decisive")
    print()
    print("  fringe    spread of predicted phase across baselines. Near zero means")
    print("            the scenario cannot tell a working delay engine from a no-op;")
    print("            such rows are marked pass*: necessary, not sufficient.")
    print("  amp bias  mean(|V_measured| / |V_predicted|) - 1. A systematic scale")
    print("            error shows up here even when the scatter looks healthy.")
    print("  scatter   std of that ratio. For noise scenarios it must match the")
    print("            theoretical 1/sqrt(N_spectra). Too small is as suspicious")
    print("            as too large.")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--with-pyuvsim", action="store_true",
                    help="also run the pyuvsim cross-check (requires pyuvsim)")
    ap.add_argument("--json", type=Path, help="write machine-readable results here")
    args = ap.parse_args()

    results = []
    for sc in scenarios():
        measured = run_correlator(sc)
        results.append(compare(sc, measured, predict(sc)))
    print_report(results)

    ok = all(r.passed for r in results)

    if args.with_pyuvsim:
        import pyuvsim_reference
        ok = pyuvsim_reference.run() and ok

    if args.json:
        args.json.write_text(json.dumps([asdict(r) for r in results], indent=2))
        print(f"wrote {args.json}")

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
