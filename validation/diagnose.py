"""Classify a Tier 2 disagreement. Run this when pyuvsim_reference.py fails.

    docker compose run --rm validate python diagnose.py

Tier 2 compares two independently developed packages, so most failures are
bookkeeping, not physics. This tool says which:

    constant complex ratio     agreement, differing only in units and sign
    antenna-based residual     phase-centre / w-term / phasing convention
    baseline-based residual    genuine geometry error, look at the correlator

It also prints raw visibilities for a source placed exactly at the phase
centre, where every phase must be zero. That single case is the fastest way to
tell whether the reference is phased at all: it is how the "pyuvsim returns
unprojected data" behaviour was originally found, after a version bump made
pyuvsim silently discard the phase centre it was handed and return raw
drift-scan visibilities. Comparing those against fringe-stopped output produced
a large, structured, entirely spurious disagreement.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from oracle import Scenario, predict                      # noqa: E402
from run_validation import ARRAY_4, unit                  # noqa: E402
import pyuvsim_reference as ref                           # noqa: E402


def build(label, sources_altaz, pc_altaz):
    sc = Scenario(
        name=label,
        ant_positions=ARRAY_4,
        source_directions=[unit(z, a) for z, a, _ in sources_altaz],
        source_amplitudes=[np.sqrt(f) for _, _, f in sources_altaz],
        phase_center=unit(*pc_altaz),
        sky_freq=1.42e9, sample_rate=1024.0, n_channels=64,
        signal_type="noise",
    )
    uv, ref_vis = ref.build_reference(sc, sources_altaz, pc_altaz)
    pred = predict(sc)
    ours = {(i, j): complex(pred[k, 0])
            for k, (i, j) in enumerate(sc.baselines) if i != j}
    return sc, uv, ref_vis, ours


def classify(label, sources_altaz, pc_altaz):
    sc, uv, ref_vis, ours = build(label, sources_altaz, pc_altaz)
    keys = sorted(ref_vis)
    n = sc.n_ants

    print(f"\n{'=' * 70}\n{label}\n{'=' * 70}")

    findings = {}
    for name, r in (
        ("direct", np.array([ours[k] / ref_vis[k] for k in keys])),
        ("conjugated", np.array([ours[k] / np.conj(ref_vis[k]) for k in keys])),
    ):
        amp_spread = float(np.ptp(np.abs(r)) / np.mean(np.abs(r)))
        resid = np.angle(r * np.conj(r[0]))
        arg_spread = float(np.ptp(resid))

        # Least-squares fit of an antenna-based model resid_ij = a_i - a_j.
        # Antenna-based residuals cancel in closure phase and indicate a
        # convention difference; whatever is left over is baseline-based and
        # points at real geometry trouble.
        A = np.zeros((len(keys), n))
        for row, (i, j) in enumerate(keys):
            A[row, i] += 1.0
            A[row, j] -= 1.0
        sol, *_ = np.linalg.lstsq(A, resid, rcond=None)
        leftover = float(np.abs(np.angle(np.exp(1j * (resid - A @ sol)))).max())

        findings[name] = dict(amp=amp_spread, arg=arg_spread, left=leftover,
                              scale=float(np.abs(r).mean()),
                              agrees=amp_spread < 1e-5 and arg_spread < 1e-5)

        print(f"\n  {name}")
        print(f"    |ratio| spread          {amp_spread:.3e}")
        print(f"    arg spread              {arg_spread:.3e}")
        print(f"    after antenna-based fit {leftover:.3e}   <- baseline-based part")

    # One conclusion per scenario. Reporting a per-convention verdict is
    # misleading: whichever convention is wrong shows a large residual by
    # definition, and calling that "a geometry error" would be a false alarm.
    print()
    agreeing = [n for n, f in findings.items() if f["agrees"]]
    if agreeing:
        n0 = agreeing[0]
        extra = " (both, because all phases are zero here)" if len(agreeing) > 1 else ""
        print(f"  => AGREEMENT under '{n0}'{extra}, "
              f"scale {findings[n0]['scale']:.6f}")
    elif min(f["left"] for f in findings.values()) < 1e-5:
        best = min(findings, key=lambda n: findings[n]["left"])
        print(f"  => No convention matches outright, but under '{best}' the")
        print(f"     residual is purely antenna-based ({findings[best]['left']:.1e}).")
        print(f"     That is a phasing or phase-centre convention difference,")
        print(f"     not a geometry error. Check whether the reference is phased.")
    else:
        print("  => A baseline-based residual survives under both conventions:")
        print("     a genuine geometry disagreement. Investigate the correlator.")


def raw_on_source():
    src = [(18.0, 35.0, 1.0)]
    pc = (18.0, 35.0)
    sc, uv, ref_vis, ours = build("raw check", src, pc)

    print(f"\n{'=' * 70}")
    print("Source exactly AT the phase centre: every phase must be zero.")
    print(f"{'=' * 70}")
    print(f"\n  phase_center_catalog: {uv.phase_center_catalog}")
    print(f"\n  {'bl':<8}{'|V| pyuvsim':>14}{'arg pyuvsim':>14}{'arg ours':>12}")
    print("  " + "-" * 48)
    for k in sorted(ref_vis):
        print(f"  {str(k):<8}{abs(ref_vis[k]):>14.6f}"
              f"{np.angle(ref_vis[k]):>14.2e}{np.angle(ours[k]):>12.2e}")

    print(f"\n  pyuvdata uvw for (i,j) vs our baseline r_i - r_j:")
    for row, (a1, a2) in enumerate(zip(uv.ant_1_array, uv.ant_2_array)):
        ours_b = ARRAY_4[a1] - ARRAY_4[a2]
        print(f"    ({a1},{a2})  uvw {np.round(uv.uvw_array[row], 3)}"
              f"   r_i-r_j {np.round(ours_b, 3)}")


if __name__ == "__main__":
    raw_on_source()
    classify("single source, phase centre ON source",
             [(18.0, 35.0, 1.0)], (18.0, 35.0))
    classify("single source, phase centre OFF source",
             [(18.0, 35.0, 1.0)], (21.5, 40.0))
    classify("two sources (closure phase non-trivial)",
             [(18.0, 35.0, 1.00), (34.0, 145.0, 0.35)], (21.5, 40.0))
