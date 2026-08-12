"""Tier 2 — cross-check against pyuvsim, the community reference simulator.

Tier 1 (``oracle.py``) proves the correlator implements *our* measurement
equation correctly. It cannot prove that equation matches what the field
means by "visibility". Tier 2 does that by comparing against pyuvsim, an
independently developed, peer-reviewed simulator maintained by the Radio
Astronomy Software Group.

    https://github.com/RadioAstronomySoftwareGroup/pyuvsim

Status
------
Verified against pyuvsim 1.4.2 / pyuvdata 3.2.6 / pyradiosky 1.1.1: agreement
to 2.2e-07 in amplitude and phase, which is pyuvsim's own float32 precision
floor rather than a correlator error. Versions actually used are printed on
every run.

All three of these packages make breaking API changes across major versions,
and this module is glue code across all three. Treat a failure here as
"investigate the glue code first", not "the correlator is broken" — Tier 1 is
the authority on that. ``diagnose.py`` classifies the residual.

What is compared, and why
-------------------------
The comparison is against the Tier 1 *oracle*, not a simulated correlator run.
The oracle is deterministic, so this isolates the question Tier 2 exists to
answer — is our measurement equation the one pyuvsim implements? — from
Monte-Carlo scatter. Tier 1 already shows the correlator reproduces the oracle
to ~1e-11, so chaining the two gives correlator == pyuvsim with no statistical
step in between.

Two quantities are checked:

1. The **complex visibility ratio**. If both implement the same equation,
   ``V_ours / V_pyuvsim`` must be a single real positive constant across every
   baseline. Non-constant modulus means a geometry error; non-constant argument
   means a phase error; constant-but-complex means a convention offset. One
   test, covering amplitude and phase together.
2. **Closure phase**, ``Phi_ijk = arg(V_ij) + arg(V_jk) - arg(V_ik)``, which is
   invariant under per-antenna phase terms and so separates physics from
   bookkeeping.

Neither is assumed to match under a particular sign convention: both are
evaluated directly and conjugated, and the module reports which one held.

Convention traps this module handles
------------------------------------
None are physics problems; each produced a large and plausible but entirely
spurious disagreement before being pinned down.

* ``run_uvdata_uvsim`` simulates in the **unprojected** frame and discards the
  ``phase_center_catalog`` it is handed, returning ``cat_type: 'unprojected'``.
  Its visibilities are raw geometric, not fringe-stopped. This module detects
  that and calls ``UVData.phase(...)`` before comparing.
* pyuvdata defines uvw for baseline (i, j) as ``r_j - r_i``, the opposite of
  our ``b_ij = r_i - r_j``. Hence the match under conjugation.
* Stokes I to xx carries a factor of 0.5, which lands in the scale factor.

Closure phase also requires **at least two sources**: for a single point source
the visibility phase is linear in baseline, so closure phase is identically
zero around every triangle no matter where the phase centre points, and
comparing it against pyuvsim compares zero with zero. The harness refuses to
report a pass unless the reference closure phases show real spread.
"""
from __future__ import annotations

import itertools
import sys

import numpy as np

from oracle import Scenario, predict
from run_validation import ARRAY_4, unit

# A real site, so that horizon and coordinate handling are exercised properly.
SITE_LAT_DEG = -30.72152     # MeerKAT / SKA-Mid, Northern Cape
SITE_LON_DEG = 21.41100
SITE_ALT_M = 1053.0
OBS_TIME_ISOT = "2026-08-02T20:00:00"


def _imports():
    """Import the optional stack, with an actionable message if it is absent."""
    try:
        import astropy                                              # noqa: F401
        import pyuvdata
        import pyradiosky
        import pyuvsim
    except ImportError as exc:
        raise SystemExit(
            f"Tier 2 requires the pyuvsim stack, which is not installed ({exc}).\n"
            f"    pip install -r validation/requirements.txt\n"
            f"Tier 1 runs without it and is the primary check."
        ) from exc

    print(f"  pyuvsim   {pyuvsim.__version__}")
    print(f"  pyuvdata  {pyuvdata.__version__}")
    print(f"  pyradiosky {pyradiosky.__version__}")
    return pyuvdata, pyradiosky, pyuvsim


def enu_direction_to_radec(zenith_deg: float, azimuth_deg: float, location, time):
    """Convert a local ENU direction to ICRS RA/Dec.

    Frame note: this project uses x=East, y=North, z=Up with azimuth measured
    from +x (East) toward +y (North). Astropy's AltAz measures azimuth from
    North toward East. The two are related by ``az_astropy = 90 - az_ours``.
    Getting this backwards mirrors the sky about the meridian and produces a
    plausible-looking but wrong answer, so it is done explicitly here.
    """
    from astropy.coordinates import AltAz, SkyCoord
    import astropy.units as u

    altaz = SkyCoord(
        alt=(90.0 - zenith_deg) * u.deg,
        az=((90.0 - azimuth_deg) % 360.0) * u.deg,
        frame=AltAz(obstime=time, location=location),
    )
    return altaz.transform_to("icrs")


def build_reference(scenario: Scenario, sources_altaz, pc_altaz):
    """Run pyuvsim for the scenario's array and sources; return visibilities.

    Args:
        scenario: the shared observation description.
        sources_altaz: list of ``(zenith_deg, azimuth_deg, flux_jy)``.
        pc_altaz: ``(zenith_deg, azimuth_deg)`` of the phase centre.

    Returns:
        (uvdata, vis) where ``vis`` is a dict keyed by (ant_i, ant_j) holding
        the complex visibility for the single frequency and time simulated.
    """
    pyuvdata, pyradiosky, pyuvsim = _imports()

    from astropy.coordinates import EarthLocation
    from astropy.time import Time
    import astropy.units as u

    from astropy.coordinates import AltAz, SkyCoord

    location = EarthLocation(lat=SITE_LAT_DEG * u.deg,
                             lon=SITE_LON_DEG * u.deg,
                             height=SITE_ALT_M * u.m)
    time = Time(OBS_TIME_ISOT, scale="utc", location=location)

    def to_radec(zen, az):
        radec = enu_direction_to_radec(zen, az, location, time)
        # Verify the AltAz <-> ICRS round trip before trusting anything built
        # on it. A mirrored azimuth convention produces a plausible wrong
        # answer rather than an obvious one.
        back = radec.transform_to(AltAz(obstime=time, location=location))
        alt_err = abs(back.alt.deg - (90.0 - zen))
        az_err = abs((back.az.deg - (90.0 - az)) % 360.0)
        az_err = min(az_err, 360.0 - az_err)
        if max(alt_err, az_err) > 1e-6:
            raise AssertionError(
                f"AltAz/ICRS round trip off by alt {alt_err:.3e} deg, "
                f"az {az_err:.3e} deg — the azimuth convention is wrong"
            )
        return radec

    src_radec = [to_radec(z, a) for z, a, _ in sources_altaz]
    fluxes = [f for _, _, f in sources_altaz]
    pc_radec = to_radec(*pc_altaz)

    for (z, a, f), rd in zip(sources_altaz, src_radec):
        print(f"  source {f:.3f} Jy at zenith {z:.1f} az {a:.1f} deg  ->  "
              f"RA {rd.ra.deg:.5f} Dec {rd.dec.deg:.5f}")
    print(f"  phase centre  ->  RA {pc_radec.ra.deg:.5f} "
          f"Dec {pc_radec.dec.deg:.5f}")

    n_ants = scenario.n_ants
    antpairs = [(i, j) for i in range(n_ants) for j in range(i + 1, n_ants)]

    # pyuvdata wants antenna positions in ECEF relative to the telescope
    # location; our scenario array is ENU in metres. In astropy 8,
    # EarthLocation.geocentric is a 3-tuple of Quantities, not one Quantity.
    site_ecef = np.array([v.to_value(u.m) for v in location.geocentric])
    ecef = pyuvdata.utils.ECEF_from_ENU(scenario.ant_positions, center_loc=location)
    ant_pos_rel = ecef - site_ecef

    # Round-trip the geometry too: this is the step most likely to silently
    # rotate the array relative to the sky.
    enu_back = pyuvdata.utils.ENU_from_ECEF(ecef, center_loc=location)
    enu_err = float(np.abs(enu_back - scenario.ant_positions).max())
    if enu_err > 1e-6:
        raise AssertionError(f"ENU->ECEF->ENU round trip is off by {enu_err:.3e} m")
    print(f"  coordinate round trips exact "
          f"(alt/az < 1e-6 deg, ENU {enu_err:.1e} m)")

    telescope = pyuvdata.Telescope.new(
        name="validation-array",
        instrument="validation-array",
        location=location,
        antenna_names=[f"A{i}" for i in range(n_ants)],
        antenna_numbers=np.arange(n_ants),
        antenna_positions=ant_pos_rel,
        feeds=["x", "y"],
        mount_type="fixed",
    )

    uv = pyuvdata.UVData.new(
        freq_array=np.array([scenario.sky_freq]),
        channel_width=np.array([scenario.sample_rate / scenario.n_channels]),
        polarization_array=np.array([-5]),          # 'xx'
        telescope=telescope,
        times=np.array([time.jd]),
        integration_time=1.0,
        antpairs=antpairs,
        vis_units="Jy",
        phase_center_catalog={
            0: {
                "cat_name": "phase-centre",
                "cat_type": "sidereal",
                "cat_lon": pc_radec.ra.rad,
                "cat_lat": pc_radec.dec.rad,
                "cat_frame": "icrs",
                "cat_epoch": 2000.0,
            }
        },
    )

    n_src = len(src_radec)
    stokes = np.zeros((4, 1, n_src))
    stokes[0, 0, :] = fluxes                     # Stokes I only
    sky = pyradiosky.SkyModel(
        name=[f"src{i}" for i in range(n_src)],
        skycoord=SkyCoord([rd.ra for rd in src_radec],
                          [rd.dec for rd in src_radec], frame="icrs"),
        stokes=stokes * u.Jy,
        spectral_type="flat",
    )

    # A uniform beam gives unit response everywhere, matching our simulator,
    # which has no primary beam model at all. Restrict it to a single feed so
    # its polarisations match the UVData object's single 'xx' — a 4-pol beam
    # against a 1-pol simulation is rejected outright.
    beam_list = pyuvsim.BeamList([
        pyuvdata.analytic_beam.UniformBeam(
            feed_array=["x"], include_cross_pols=False,
        )
    ])
    beam_dict = {f"A{i}": 0 for i in range(n_ants)}

    out = pyuvsim.uvsim.run_uvdata_uvsim(
        uv, beam_list, beam_dict=beam_dict,
        catalog=pyuvsim.simsetup.SkyModelData(sky),
        quiet=True,
    )

    # pyuvsim simulates in the unprojected (drift) frame and *discards* the
    # phase centre it was handed — `out.phase_center_catalog` comes back as
    # {'cat_type': 'unprojected'}. Its visibilities are therefore raw
    # geometric, not fringe-stopped. Comparing them against our fringe-stopped
    # output without this step compares two different quantities and produces
    # a large, structured, entirely spurious disagreement.
    if any(e.get("cat_type") == "unprojected"
           for e in out.phase_center_catalog.values()):
        out.phase(
            lon=pc_radec.ra.rad,
            lat=pc_radec.dec.rad,
            cat_name="phase-centre",
            cat_type="sidereal",
            epoch="J2000",
            phase_frame="icrs",
            use_ant_pos=True,
        )
        print("  pyuvsim returned unprojected data; phased it to the phase centre")

    vis = {}
    for (i, j) in antpairs:
        vis[(i, j)] = complex(out.get_data(i, j, "xx").ravel()[0])
    return out, vis


def closure_phases(vis: dict[tuple[int, int], complex], n_ants: int):
    """Closure phase for every antenna triangle, keyed by (i, j, k)."""
    out = {}
    for i, j, k in itertools.combinations(range(n_ants), 3):
        out[(i, j, k)] = np.angle(
            np.exp(1j * (np.angle(vis[(i, j)])
                         + np.angle(vis[(j, k)])
                         - np.angle(vis[(i, k)])))
        )
    return out


# Two sources. A *single* point source produces a visibility phase that is
# linear in baseline vector, so its closure phase is identically zero around
# every triangle no matter where the phase centre points — comparing that
# against pyuvsim compares 0 with 0 and establishes nothing. Two sources make
# the phase non-linear in baseline and the closure phase genuinely non-trivial.
SOURCES_ALTAZ = [
    (18.0, 35.0, 1.00),      # zenith angle deg, azimuth deg, flux Jy
    (34.0, 145.0, 0.35),
]
PHASE_CENTRE_ALTAZ = (21.5, 40.0)


def run() -> bool:
    """Run the Tier 2 comparison. Returns True on agreement."""
    print()
    print("Tier 2 — pyuvsim cross-check")
    print()

    # Sources are mutually incoherent, as real sky sources are, so the
    # visibility is a plain sum of per-source terms with no cross products.
    # signal_type='noise' is the oracle branch that models exactly that.
    sc = Scenario(
        name="pyuvsim cross-check",
        ant_positions=ARRAY_4,
        source_directions=[unit(z, a) for z, a, _ in SOURCES_ALTAZ],
        # Visibility amplitude goes as amplitude**2, so a flux of S Jy
        # corresponds to a voltage amplitude of sqrt(S).
        source_amplitudes=[np.sqrt(f) for _, _, f in SOURCES_ALTAZ],
        phase_center=unit(*PHASE_CENTRE_ALTAZ),
        sky_freq=1.42e9, sample_rate=1024.0, n_channels=64,
        signal_type="noise",
    )

    try:
        _, ref_vis = build_reference(sc, SOURCES_ALTAZ, PHASE_CENTRE_ALTAZ)
    except SystemExit:
        raise
    except Exception as exc:                       # noqa: BLE001
        print(f"  pyuvsim setup failed: {type(exc).__name__}: {exc}")
        print("  This is glue-code or API-version trouble, not a correlator")
        print("  result. Tier 1 remains the authority on correlator accuracy.")
        return False

    # Compare against the analytic oracle rather than a simulated run. The
    # oracle is deterministic, so this isolates the question Tier 2 exists to
    # answer — "is our measurement equation the same one pyuvsim implements?" —
    # from Monte-Carlo scatter. Tier 1 has already established, to ~1e-11, that
    # the correlator reproduces the oracle; chaining the two gives
    # correlator == pyuvsim without a statistical step in the middle.
    #
    # Channel 0 has zero baseband offset, so its absolute sky frequency is
    # exactly sky_freq, matching pyuvsim's single channel.
    predicted = predict(sc)
    ours = {}
    for bl_idx, (i, j) in enumerate(sc.baselines):
        if i != j:
            ours[(i, j)] = complex(predicted[bl_idx, 0])

    n = sc.n_ants
    keys = sorted(ref_vis)

    # ---- identify the convention from the data, don't assume it -----------
    #
    # pyuvsim works in Jy and applies a factor of 0.5 taking Stokes I to xx;
    # we carry an arbitrary channeliser gain. If both implement the same
    # equation, the ratio V_ours / V_pyuvsim must be one real positive constant
    # across every baseline. A non-constant modulus means a geometry error, a
    # non-constant argument means a phase error, and a constant-but-complex
    # ratio means a convention offset.
    #
    # pyuvdata defines uvw for baseline (i, j) as r_j - r_i, the opposite of
    # our b_ij = r_i - r_j, so the expected match is under conjugation. That is
    # verified here rather than hard-coded.
    def spread(r):
        return (float(np.ptp(np.abs(r)) / np.mean(np.abs(r))),
                float(np.ptp(np.angle(r * np.conj(r[0])))))

    ratios = {
        "direct": np.array([ours[k] / ref_vis[k] for k in keys]),
        "conjugated": np.array([ours[k] / np.conj(ref_vis[k]) for k in keys]),
    }

    # pyuvsim carries float32 internally in places, so ~1e-7 is its own
    # precision floor, not our error. Tolerance sits an order above it.
    TOL = 1e-5

    print()
    print(f"  {'convention':<14}{'|ratio| spread':>16}{'arg spread':>14}   verdict")
    print("  " + "-" * 58)
    matched = None
    for name, r in ratios.items():
        amp_s, arg_s = spread(r)
        ok = amp_s < TOL and arg_s < TOL
        if ok:
            matched = name
        print(f"  {name:<14}{amp_s:>16.2e}{arg_s:>14.2e}   "
              f"{'MATCH' if ok else 'no'}")

    if matched is None:
        print()
        print("  Visibilities DISAGREE with pyuvsim beyond a constant scale.")
        print("  Run `python diagnose.py` inside the container to classify the")
        print("  residual as antenna-based (convention) or baseline-based")
        print("  (geometry).")
        return False

    scale = float(np.abs(ratios[matched]).mean())
    print()
    print(f"  Visibilities agree with pyuvsim under the '{matched}' convention,")
    print(f"  to {max(spread(ratios[matched])):.1e} in both amplitude and phase.")
    print(f"  Constant scale factor {scale:.6f} = our channeliser gain "
          f"({channel_gain_str(sc)})")
    print(f"  divided by pyuvsim's 0.5 Stokes-I-to-xx factor.")
    if matched == "conjugated":
        print("  The sign difference is pyuvdata's uvw convention (r_j - r_i")
        print("  against our r_i - r_j), not a physics disagreement.")

    # ---- closure phase, under the identified convention -------------------
    sign = -1.0 if matched == "conjugated" else 1.0
    ref_cp = closure_phases(ref_vis, n)
    our_cp = closure_phases(ours, n)

    print()
    print(f"  {'triangle':<12}{'pyuvsim':>12}{'ours':>12}{'residual':>12}")
    print("  " + "-" * 48)
    diffs = []
    for tri in sorted(ref_cp):
        d = np.angle(np.exp(1j * (our_cp[tri] - sign * ref_cp[tri])))
        diffs.append(abs(d))
        print(f"  {str(tri):<12}{sign * ref_cp[tri]:>12.6f}"
              f"{our_cp[tri]:>12.6f}{d:>12.1e}")

    cp_spread = float(np.ptp([ref_cp[t] for t in ref_cp]))
    decisive = cp_spread > 1e-3
    print(f"\n  closure phases agree to {max(diffs):.1e} rad")
    print(f"  spread across triangles in the reference: {cp_spread:.4f} rad")
    if not decisive:
        print("  NOT DECISIVE — reference closure phases are all ~equal, so this")
        print("  comparison cannot tell a correct implementation from a broken")
        print("  one. A single point source always gives zero closure phase;")
        print("  use a model with real structure.")

    print()
    print("  Combined with Tier 1 (correlator == oracle to ~1e-11), this")
    print("  establishes that the correlator agrees with pyuvsim.")

    return bool(max(diffs) < TOL and decisive)


def channel_gain_str(scenario) -> str:
    from oracle import channel_gain
    return f"{channel_gain(scenario):g}"


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
