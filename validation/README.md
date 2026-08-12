# Correlator validation harness

An external, optional harness that answers one question: **does this
correlator produce the visibilities that physics says it should?**

It is deliberately kept outside the correlator. Nothing under
`app/src/correlator` imports anything here, nothing here is installed by
`setup.py`, and the directory is excluded from the Docker image. Deleting
`validation/` leaves the correlator and its own test suite working unchanged —
see [Detaching it](#detaching-it).

```bash
./validate.sh              # everything, in Docker: 72 tests + Tier 1 + Tier 2
./validate.sh quick        # Tier 1 only, ~1 second
./validate.sh tests        # the correlator's pytest suite
./validate.sh diagnose     # classify a Tier 2 disagreement
./validate.sh shell        # interactive shell in the validation image
```

Docker is the only host requirement — nothing is installed on the machine.
The same script works on a workstation and on a bare Ubuntu server.

To run Tier 1 directly against a local Python instead:

```bash
python validation/run_validation.py                 # Tier 1, numpy/scipy only
python validation/run_validation.py --with-pyuvsim  # needs the pyuvsim stack
python validation/run_validation.py --json out.json # machine-readable
```

Exit code is 0 if everything passed, 1 otherwise, so it drops into CI directly.
JSON reports land in `validation/reports/`.

---

## Why a separate harness at all

The correlator's own `tests_harness/` suite checks the correlator against
itself and against hand-derived values, which is necessary but has a specific
blind spot: a test written from the same understanding as the code inherits
the same mistakes. This harness re-derives the expected answer from the
measurement equation independently, and then — in Tier 2 — from a third-party
implementation that shares no lineage with either.

That layering matters, because the failure mode this project actually had was
not a wrong formula. It was a test suite that passed while testing nothing.

---

## The two tiers

### Tier 1 — analytic oracle (`oracle.py`)

An independent implementation of the interferometric measurement equation. For
antennas at `r_i`, a point source at unit direction `s`, and a phase centre
`s0`, with geometric advance `a_i(s) = (r_i · s) / c`:

```
V_ij[k] = G · Σ_s A_s² · exp( 2πi · f_k · b_ij · (s − s0) / c )
```

where `b_ij = r_i − r_j`, `f_k` is the **absolute sky frequency** of channel
`k` (that is, `sky_freq + channel_offset` — see [Conventions](#conventions)),
and `G` is the channeliser power gain.

`G` depends on the signal statistics, and conflating the two cases is a common
way to be wrong by a constant factor:

| Signal | Channel gain |
|---|---|
| coherent tone on an exact bin | `sum(window)²` |
| white noise | `sum(window²)` |

Windows are normalised to unit coherent gain (`w · n/sum(w)`), so the first
row equals `n_channels²` for every window while the second stays window
dependent — equivalent noise bandwidths genuinely differ. The oracle derives
this from NumPy directly rather than importing `FEngine`.

The oracle imports nothing from `correlator`. If it did, agreement would prove
nothing.

Tier 1 needs only numpy and scipy, runs in under a second, and is the
authority on correlator accuracy.

### Tier 2 — pyuvsim cross-check (`pyuvsim_reference.py`)

Tier 1 proves the correlator implements *our* measurement equation. It cannot
prove that equation is what the field means by "visibility". Tier 2 compares
against [pyuvsim](https://github.com/RadioAstronomySoftwareGroup/pyuvsim), the
Radio Astronomy Software Group's reference simulator.

```bash
./validate.sh                        # runs both tiers in the container
```

### Result

Verified against **pyuvsim 1.4.2 / pyuvdata 3.2.6 / pyradiosky 1.1.1**:

```
  convention      |ratio| spread    arg spread   verdict
  ----------------------------------------------------------
  direct                1.84e-07      5.56e+00   no
  conjugated            1.84e-07      2.24e-07   MATCH

  Constant scale factor 128.000002 = our channeliser gain (64)
  divided by pyuvsim's 0.5 Stokes-I-to-xx factor.

  closure phases agree to 2.4e-07 rad
  spread across triangles in the reference: 1.3610 rad
```

The `~2e-7` floor is pyuvsim's own internal float32 precision
(`1.84e-07 ≈ 1.5 × float32 eps`), not a correlator error. The scale factor is
predicted exactly from first principles before being measured.

### What is compared

The comparison is against the **Tier 1 oracle**, not a simulated correlator
run. The oracle is deterministic, so this isolates the question Tier 2 exists
to answer — *is our measurement equation the one pyuvsim implements?* — from
Monte-Carlo scatter. Tier 1 has already shown the correlator reproduces the
oracle to ~1e-11, so chaining the two gives correlator == pyuvsim with no
statistical step in the middle.

Two quantities are checked:

1. **Complex visibility ratio.** If both implement the same equation,
   `V_ours / V_pyuvsim` must be one real positive constant across every
   baseline. A non-constant modulus means a geometry error; a non-constant
   argument means a phase error; constant-but-complex means a convention
   offset. This single test covers amplitude and phase at once.
2. **Closure phase**, `Φ_ijk = arg(V_ij) + arg(V_jk) − arg(V_ik)` — invariant
   under per-antenna phase terms, so it separates physics from bookkeeping.

> **Closure phase needs at least two sources.** For a *single* point source the
> visibility phase is linear in the baseline vector, so closure phase is
> identically zero around every triangle regardless of where the phase centre
> points. Comparing that against pyuvsim compares 0 with 0 and establishes
> nothing. The scenario therefore uses two sources, and the harness refuses to
> report a pass unless the reference closure phases show real spread.

### Three convention traps, all found by running it

None of these are physics problems, and each produced a large, plausible,
entirely spurious disagreement:

- **pyuvsim discards the phase centre.** `run_uvdata_uvsim` simulates in the
  unprojected (drift) frame and returns `cat_type: 'unprojected'` regardless of
  the `phase_center_catalog` it was handed. Its visibilities are raw geometric,
  not fringe-stopped. `pyuvsim_reference.py` detects this and calls
  `UVData.phase(...)` before comparing. Without that step a source sitting
  exactly at the phase centre comes back with structured phases near 0 and ±π.
- **pyuvdata's uvw is `r_j − r_i`**, the opposite of our `b_ij = r_i − r_j`.
  Hence the match under conjugation. Read off the `uvw_array`, not assumed.
- **Stokes I → xx carries a factor of 0.5**, which lands in the scale factor.

### When it breaks again

pyuvsim, pyuvdata and pyradiosky all make breaking API changes across major
versions, and Tier 2 is glue code across three of them. When it fails:

```bash
./validate.sh diagnose
```

`diagnose.py` classifies the residual — constant ratio (agreement), purely
antenna-based (a phasing/convention difference), or baseline-based (a genuine
geometry error worth investigating). It also prints raw visibilities for a
source placed exactly at the phase centre, where every phase must be zero;
that one case is the fastest way to tell whether the reference is phased at
all, and it is how the unprojected-data behaviour was found.

**Treat a Tier 2 failure as glue-code trouble until diagnose.py says
otherwise.** Tier 1 is the authority on correlator correctness.

---

## Reading the Tier 1 report

```
scenario                                          bl  max dphase   amp bias  scatter  fringe  result
----------------------------------------------------------------------------------------------------
on-axis point source                               6     1.4e-11  +2.40e-12  4.5e-12    0.00  pass*
off-axis by 3.5 deg (fringe must survive)          6     1.5e-11  -2.03e-12  3.1e-12    3.26  pass
two sources, hanning window                        6     1.3e-11  +7.37e-12  1.1e-11    0.83  pass
6 antennas, 15 baselines, blackman                15     1.1e-11  +3.73e-12  4.8e-12    6.00  pass
broadband noise source, all channels               6     1.1e-04  -6.41e-03   0.0606    5.20  pass
low elevation, long baselines (many fringe turns)  15     9.9e-12  -2.76e-12  7.6e-12    4.65  pass
```

| Column | Meaning |
|---|---|
| `max dphase` | Largest phase disagreement with the oracle, radians. `~1e-11` is double-precision noise. |
| `amp bias` | `mean(|V_measured| / |V_predicted|) − 1`. Catches a systematic scale error even when scatter looks healthy. |
| `scatter` | Standard deviation of that ratio. For noise scenarios it must match the theoretical `1/√N_spectra` — *too small is as suspicious as too large*. |
| `fringe` | Spread of predicted phase across baselines. |

**`pass*` means "passed, but not decisive on its own."** A scenario with a
source exactly at the phase centre predicts zero phase — and zero is also what
you get from a delay engine that does nothing at all. Such a scenario cannot
distinguish the two, so the harness flags it rather than letting it pad the
pass count. At least one decisive (non-zero fringe) scenario must pass for the
run to mean anything.

### Amplitude is judged by bias and scatter, not a max threshold

With `N` averaged spectra, visibility amplitude has an irreducible relative
scatter of `~1/√N`. The maximum over many baselines and channels is then
several sigma *by construction* — in the broadband row above, 256 spectra give
6.25% expected scatter, and the max over 384 samples lands near 20%. A
max-error tolerance would either have to be set absurdly loose or would flag
correct behaviour as a bug.

Testing that the mean ratio is 1 (no systematic scale error) and that the
scatter matches theory (no excess variance) is both stricter and honest. The
measured 0.0606 against a predicted 0.0625 above is agreement to 3%.

---

## Conventions

Stated explicitly because getting these wrong is the most common source of
silent correlator errors. `correlator/core/delay.py` and
`correlator/core/frontend.py` carry the same statement.

- Antenna positions in **metres**, right-handed local frame, **x = East,
  y = North, z = Up**.
- A source direction is a **unit vector pointing from the array toward the
  source**. Zenith is `[0, 0, 1]`.
- **Geometric advance** `a_i(s) = (r_i · s) / c` seconds — how much *earlier*
  the wavefront reaches antenna `i` than the array origin.
- A receiver at sky frequency `f_sky`, mixed to complex baseband, sees in the
  channel at baseband offset `f_ch`:
  `X_i[k] = S[k] · exp(+2πi · (f_sky + f_ch) · a_i)`
- Fringe stopping toward `s0` multiplies by `exp(−2πi · (f_sky + f_ch) · a_i(s0))`.

> **Both `f_sky` and `f_ch` appear.** For a 1.42 GHz observation with 1 kHz of
> bandwidth, the `f_sky` term exceeds the `f_ch` term by six orders of
> magnitude. Omitting it does not introduce a small error — it discards the
> entire fringe. This was a real bug in this project.

Azimuth here is measured from **+x (East) toward +y (North)**. Astropy's AltAz
measures from North toward East; the conversion `az_astropy = 90° − az_ours` is
applied explicitly in `pyuvsim_reference.py`. Getting it backwards mirrors the
sky about the meridian and produces a plausible-looking wrong answer.

---

## What this harness does *not* validate

Being clear about the boundary is part of the point.

- **Absolute flux calibration.** Windows are normalised to unit coherent gain,
  so amplitudes no longer depend on the window choice, but the FFT still
  carries no `1/N`: a tone of amplitude `A` gives `(A · n_channels)²`. That is
  a documented convention which real flux calibration absorbs, not a
  correspondence to Jy. See `TestAmplitudeScale` in
  `tests_harness/integration/test_correlator_validation.py`.
- **Real recorded voltages.** Everything here is simulated. The nearest real
  data is the [`baseband`](https://baseband.readthedocs.io/) package's
  `SAMPLE_VDIF` — an actual EVN/VLBA recording — but it is single-station with
  no ground-truth visibilities, so it tests ingest, not accuracy.
- **Sky-model realism.** Point sources only: no extended emission, no
  primary beam, no polarisation, no ionosphere, no bandpass.
- **Source tracking.** The phase centre is fixed; nothing here exercises a
  phase centre that moves with time.
- **Performance.** Correctness only.

---

## Detaching it

By construction:

- `app/src/correlator/**` imports nothing from `validation/`
- `validation/` is listed in `.dockerignore`, so it never enters the image
- `setup.py` uses `find_packages()` rooted at `app/src`, which cannot see it
- `requirements.txt` (the correlator's) does not reference the Tier 2 stack

To remove it:

```bash
rm -rf validation/
```

Then confirm nothing broke:

```bash
PYTHONPATH=app/src python -m pytest tests_harness/ -q
```

The correlator's own suite is self-contained and still passes.
