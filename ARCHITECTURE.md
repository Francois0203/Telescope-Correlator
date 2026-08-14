# Telescope Correlator - System Architecture & Design

This document provides a comprehensive technical overview of the telescope correlator system, including architectural design, signal processing algorithms, data flow, and implementation details.

## Table of Contents

- [System Overview](#system-overview)
- [Architecture](#architecture)
- [Signal Processing Pipeline](#signal-processing-pipeline)
- [Component Details](#component-details)
  - [Frontend (Data Ingestion)](#frontend-data-ingestion)
  - [F-Engine (Channelizer)](#f-engine-channelizer)
  - [Delay Engine](#delay-engine)
  - [X-Engine (Correlator)](#x-engine-correlator)
- [Data Structures](#data-structures)
- [Configuration System](#configuration-system)
- [Mathematical Foundations](#mathematical-foundations)
- [Performance Considerations](#performance-considerations)
- [Implementation Details](#implementation-details)
- [Testing Strategy](#testing-strategy)

## System Overview

The Telescope Correlator implements an **FX (Fourier Transform-Cross Multiply) Architecture** for radio telescope interferometry. This architecture is widely used in modern radio telescopes including LOFAR, MWA, and SKA.

### Purpose

The correlator converts time-domain voltage signals from multiple antennas into **visibility measurements** - the fundamental data product in radio interferometry. These visibilities represent spatial frequency components of the sky brightness distribution and are used to create radio images through synthesis imaging techniques.

### Key Design Principles

1. **Modular Architecture**: Each processing stage (frontend, F-engine, delay, X-engine) is an independent, testable module
2. **Configurable Pipeline**: All parameters are exposed as settings on a single `Config` object, adjustable from the interactive shell
3. **Dual Input Modes**: Supports both `simulate` (synthetic signals) and `file` (load a recorded `.npy` array)
4. **Scientific Accuracy**: Algorithms validated against analytical expectations in the test suite
5. **Reproducible**: Each run writes the exact `Config` used to `config.yaml` alongside its outputs

## Architecture

### High-Level Block Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        DATA SOURCES                             │
├─────────────────────────────────────────────────────────────────┤
│      Simulated Stream      │      File (Batch .npy)             │
│  (mode=simulate)           │      (mode=file)                   │
└───────────┬────────────────────────────┬────────────────────────┘
            │                            │
            └──────────────┬─────────────┘
                           │
                    ┌─────────▼──────────┐
                    │     FRONTEND       │
                    │  (Data Ingestion)  │
                    └─────────┬──────────┘
                              │ Time-domain signals
                              │ Shape: (n_ants, n_samples)
                    ┌─────────▼──────────┐
                    │     F-ENGINE       │
                    │  (Channelizer)     │
                    │  - Windowing       │
                    │  - FFT             │
                    │  - Quantization    │
                    └─────────┬──────────┘
                              │ Frequency-domain spectra
                              │ Shape: (n_ants, n_spectra, n_channels)
                    ┌─────────▼──────────┐
                    │   DELAY ENGINE     │
                    │ (Geometric Delay   │
                    │   Compensation)    │
                    └─────────┬──────────┘
                              │ Phase-corrected spectra
                              │ Shape: (n_ants, n_spectra, n_channels)
                    ┌─────────▼──────────┐
                    │    X-ENGINE        │
                    │  (Correlator)      │
                    │  - Cross-multiply  │
                    │  - Integration     │
                    └─────────┬──────────┘
                              │ Visibilities
                              │ Shape: (n_baselines, n_channels)
                    ┌─────────▼──────────┐
                    │   OUTPUT WRITER    │
                    │  (NPY/HDF5/FITS)   │
                    └────────────────────┘
```

### Processing Flow

1. **Data Acquisition**: Ingest time-domain signals from antennas
2. **Channelization**: Transform to frequency domain with windowing
3. **Delay Correction**: Apply geometric delay compensation
4. **Correlation**: Compute cross-products between antenna pairs
5. **Integration**: Time-average to reduce noise
6. **Output**: Write visibility products to disk

## Signal Processing Pipeline

### Mathematical Overview

The FX correlator implements the following mathematical operations:

#### Input Signal
Time-domain voltage signal from antenna `i`:
```
V_i(t) = complex voltage at time t
```

#### F-Engine: Channelization
Apply windowing and FFT to convert to frequency domain:
```
Ṽ_i[k] = FFT{ w[n] · V_i[n] }
```
where:
- `w[n]` = window function (Hanning, Hamming, etc.)
- `k` = frequency channel index
- `Ṽ_i[k]` = complex spectrum at channel k

#### Delay Compensation
Correct for geometric delays:
```
Ṽ'_i[k] = Ṽ_i[k] · exp(-2πj · (f_sky + f_k) · a_i)
```
where:
- `f_sky` = sky (RF) frequency the band was mixed down from (`center_freq`)
- `f_k` = baseband offset of channel k
- `a_i` = geometric advance of antenna i, in seconds

> **The `f_sky` term is not optional.** For a 1.42 GHz observation with a few
> kHz of bandwidth it exceeds the `f_k` term by six orders of magnitude.
> Rotating by `f_k` alone — as an earlier version of this code did — discards
> the entire fringe rather than introducing a small error.

#### X-Engine: Correlation
Compute visibilities for baseline (i,j):
```
V_ij[k] = <Ṽ'_i[k] · Ṽ'_j[k]*>
```
where:
- `*` = complex conjugate
- `<...>` = time averaging over integration period

#### Output
Visibility matrix for N antennas:
```
V[k] = matrix of all baseline visibilities at frequency k
Shape: (N(N+1)/2, n_channels)
```

## Component Details

### Frontend (Data Ingestion)

**File:** [`app/src/correlator/core/frontend.py`](app/src/correlator/core/frontend.py)

#### Purpose
Provides a unified interface for loading antenna data from various sources.

#### Supported Data Sources

1. **Simulated Stream** (`SimulatedStream`)
   - Generates synthetic antenna signals on-the-fly
   - Models point sources with configurable angles
   - Adds realistic Gaussian noise
   - Supports real-time simulation with timing delays
   - Useful for: Algorithm development, testing, demonstrations

2. **Batch File Source** (`BatchFileSource`)
   - Loads pre-recorded data from NumPy files
   - Supports chunked reading for memory efficiency
   - Input format: `(n_ants, n_samples)` complex array
   - Useful for: Processing observations, benchmarking

3. **Network Stream** (future enhancement)
   - TCP/UDP streaming from antenna digitizers
   - SPEAD protocol support for radio astronomy
   - Buffering and flow control
   - Useful for: Real-time processing, production operations

#### Data Format

All sources produce data chunks with shape:
```python
shape: (n_antennas, chunk_size)
dtype: complex128
```

Each value represents a complex voltage measurement at a single time instant.

#### Implementation: Simulated Stream

The simulator generates signals for multiple sources:

The simulator produces **complex baseband voltages** — what a receiver yields
after mixing the sky signal down from `sky_freq` — using the same conventions
as the delay engine, so that fringe stopping has something real to undo.

```python
# Geometric advance of antenna i toward a source at unit direction ŝ:
a_i = (r_i · ŝ) / c            # seconds

# Voltage at antenna i:
x_i(t) = s(t + a_i) · exp(+2πj · f_sky · a_i)

# Where:
# r_i    = antenna position vector (metres, x=East y=North z=Up)
# ŝ      = unit vector toward the source, zenith = [0, 0, 1]
# s(t)   = baseband envelope, shared by all antennas
# f_sky  = sky frequency the band was mixed down from
```

Receiver noise is added **independently per antenna** afterwards, so it
correlates only on the autocorrelations — which is what makes a cross-
correlation a measurement rather than a power meter.

> An earlier version applied `exp(-2πj · (r_i · ŝ))`, treating antenna
> positions in metres as though they were wavelengths, with no `c` and no
> frequency dependence. That model could not be cancelled by the delay engine
> under any parameters, because the two used different unit systems.

**Key Features:**
- Multiple simultaneous point sources, each with its own direction and amplitude
- Coherent tone or band-limited Gaussian noise envelopes
- Configurable SNR in dB
- Physically correct geometric delays and fringe phases
- Optional real-time streaming simulation

### F-Engine (Channelizer)

**File:** [`app/src/correlator/core/fengine.py`](app/src/correlator/core/fengine.py)

#### Purpose
Converts time-domain signals to frequency domain using windowed FFT, producing narrow frequency channels.

#### Algorithm

For each antenna:
1. Extract overlapping windows of length `n_channels`
2. Apply window function (e.g., Hanning), normalised to unit coherent gain
3. Compute FFT of each window
4. Optionally apply quantization

#### Amplitude Normalisation

Windows are scaled by `n_channels / sum(w)` before use. Without this, a taper
attenuates coherent signals by `sum(w)/N` — about 0.5 for Hanning — so merely
changing `window` would rescale every visibility and, with it, the flux scale.

| Signal | Channel response |
|---|---|
| coherent tone on an exact bin | `A · n_channels` — identical for every window |
| white noise, variance `σ²` | `σ² · sum(w²)` — window dependent |

Noise power cannot be made window-independent at the same time, because
equivalent noise bandwidths genuinely differ. `FEngine` exposes both figures
as `coherent_gain` and `noise_gain`. The FFT itself carries no `1/N`, so
visibility amplitudes scale as `n_channels²`; flux calibration absorbs the
constant.

#### Window Functions

**Available Windows:**
- **Rectangular**: `w[n] = 1` (no windowing)
  - Pros: Maximum frequency resolution
  - Cons: High sidelobes, spectral leakage
  
- **Hanning**: `w[n] = 0.5 - 0.5·cos(2πn/N)`
  - Pros: Good sidelobe suppression, smooth
  - Cons: Slightly reduced resolution
  - **Recommended for most applications**
  
- **Hamming**: `w[n] = 0.54 - 0.46·cos(2πn/N)`
  - Pros: Lower *first* sidelobe than Hanning (−43 dB vs −31 dB)
  - Cons: Far-field rolloff is worse — `1/d²` against Hanning's `1/d³`, so it
    leaks substantially more power far from the peak. Measured at ~400× more
    than Hanning beyond 8 channels (`test_windows_suppress_spectral_leakage`).
    Prefer Hanning or Blackman when distant leakage matters, which for RFI
    rejection it usually does.
  
- **Blackman**: `w[n] = 0.42 - 0.5·cos(2πn/N) + 0.08·cos(4πn/N)`
  - Pros: Excellent sidelobe suppression
  - Cons: Reduced frequency resolution

#### Overlap Processing

The F-engine supports overlapping FFT windows:
```
overlap_factor = 0.0 to 0.5
stride = n_channels × (1 - overlap_factor)
```

Benefits of overlap:
- Smoother frequency response
- Reduced scalloping loss
- Improved time resolution

> **Note:** Overlap is implemented in the `FEngine` class (`overlap_factor` constructor argument) but is **not currently exposed** through `Config` or the shell. The pipeline instantiates `FEngine` with the default `overlap_factor=0.0` (no overlap).

#### Quantization

Emulates real hardware quantizers:
```python
n_bits = 0: No quantization (infinite precision)
n_bits = 8: 8-bit quantization (256 levels)
n_bits = 16: 16-bit quantization (65536 levels)
```

Quantization process:
1. Compute 3-sigma clipping level
2. Normalize to [-1, 1]
3. Quantize real and imaginary parts independently
4. Reconstruct complex values

**Impact:** Adds quantization noise, models real systems

> **Note:** Quantization is implemented in the `FEngine` class (`quantize_bits` constructor argument and the `quantize_signal` helper) but is **not currently exposed** through `Config` or the shell. The pipeline runs with the default `quantize_bits=0` (no quantization).

#### Channel Frequencies

For sample rate `f_s` and `N` channels:
```python
f[k] = k · f_s / N  for k = 0, 1, ..., N-1
```

Standard FFT frequency ordering:
- `f[0]` = DC (0 Hz)
- `f[1...N/2-1]` = positive frequencies
- `f[N/2]` = Nyquist frequency
- `f[N/2+1...N-1]` = negative frequencies

### Delay Engine

**File:** [`app/src/correlator/core/delay.py`](app/src/correlator/core/delay.py)

#### Purpose
Corrects for geometric time delays caused by different path lengths from a source to different antennas.

#### Geometric Delay Calculation

For a source at direction `ŝ` (unit vector):
```
Path difference to antenna i: Δl_i = r_i · ŝ - r_0 · ŝ
Geometric advance:            a_i  = Δl_i / c
```

where:
- `r_i` = position of antenna i (metres, x=East y=North z=Up)
- `r_0` = reference antenna position
- `c` = speed of light (`scipy.constants.c`, not 3×10⁸)
- `ŝ` = [sx, sy, sz] unit vector toward the source, zenith = `[0, 0, 1]`

`a_i` is how much *earlier* the wavefront reaches antenna i than the array
origin. Referencing to antenna 0 keeps the numbers small and has no effect on
visibilities: a common offset cancels in every baseline difference `a_i - a_j`.

#### Phase Rotation

To compensate delay, apply phase rotation in frequency domain:
```
Ṽ'_i[k] = Ṽ_i[k] · exp(-2πj · (f_sky + f[k]) · a_i)
```

This "stops the fringes" by aligning all antenna phases to a common reference
direction. After fringe stopping toward `s0`, a point source at `ŝ` gives

```
V_ij[k] = A · exp(+2πj · (f_sky + f[k]) · b_ij · (ŝ - s0) / c),   b_ij = r_i - r_j
```

which is zero-phase when `ŝ == s0`. That closed form is what the validation
harness asserts against; see [`validation/README.md`](validation/README.md).

#### Phase Center

The phase center is the direction on the sky where:
- All antenna phases are aligned
- Maximum sensitivity for sources
- Typically the pointing direction

Setting phase center:
```python
delay_engine.set_phase_center([sx, sy, sz])  # Unit vector
```

#### 2D vs 3D Arrays

- **2D Arrays**: Antennas in horizontal plane (common for radio arrays)
  - Positions: `(x, y)` or `(x, y, 0)`
  - Simplified geometry for altitude-azimuth arrays

- **3D Arrays**: Full 3D positions
  - Positions: `(x, y, z)`
  - Required for elevation differences

### X-Engine (Correlator)

**File:** [`app/src/correlator/core/xengine.py`](app/src/correlator/core/xengine.py)

#### Purpose
Computes cross-correlations between all antenna pairs to produce visibility measurements.

#### Baseline Definition

A **baseline** is a pair of antennas `(i, j)` where `i ≤ j`.

For `N` antennas:
- Total baselines: `N(N+1)/2`
- Autocorrelations: `N` (i=j)
- Cross-correlations: `N(N-1)/2` (i<j)

**Baseline Ordering:**
```
Baseline 0: (0, 0)  [autocorr]
Baseline 1: (1, 1)  [autocorr]
...
Baseline N-1: (N-1, N-1)  [autocorr]
Baseline N: (0, 1)  [cross-corr]
Baseline N+1: (0, 2)
...
```

#### Correlation Algorithm

For each spectrum (time sample in frequency domain):
```python
# For each baseline (i, j):
if i == j:
    # Autocorrelation (power)
    V_ij[k] = |Ṽ_i[k]|²
else:
    # Cross-correlation
    V_ij[k] = Ṽ_i[k] · Ṽ_j[k]*
```

**Result:** Instantaneous visibility for one time sample

#### Time Integration

To reduce noise, visibilities are averaged over time:
```
<V_ij[k]> = (1/M) · Σ_{m=1}^M V_ij^(m)[k]
```

where `M` = number of spectra to integrate

Calculating `M`:
```python
spectrum_duration = n_channels / sample_rate  # seconds
M = integration_time / spectrum_duration
```

Example:
- `n_channels = 256`
- `sample_rate = 1024 Hz`
- `spectrum_duration = 0.25 s`
- `integration_time = 1.0 s`
- `M = 4 spectra`

#### Output

Integrated visibility matrix:
```
shape: (n_baselines, n_channels)
dtype: complex128 (real for autocorrelations)
```

Each entry `V_ij[k]` represents:
- **Amplitude**: Correlation strength
- **Phase**: Relative phase between antennas
- **Frequency**: Channel k

## Data Structures

### Time-Domain Data

**Format:** Complex voltage samples
```python
shape: (n_antennas, n_samples)
dtype: complex128
units: Arbitrary voltage units
```

Example (4 antennas, 1024 samples):
```python
time_data.shape = (4, 1024)
time_data[0, 500]  # Voltage at antenna 0, time index 500
```

### Frequency-Domain Data (Channelized)

**Format:** Complex spectra from FFT
```python
shape: (n_antennas, n_spectra, n_channels)
dtype: complex128
```

Example (4 antennas, 16 spectra, 256 channels):
```python
channelized.shape = (4, 16, 256)
channelized[2, 5, 100]  # Antenna 2, spectrum 5, channel 100
```

### Visibility Data

**Format:** Correlation products
```python
shape: (n_baselines, n_channels)
dtype: complex128
```

Example (4 antennas = 10 baselines, 256 channels):
```python
visibilities.shape = (10, 256)
visibilities[0, :]   # Autocorrelation antenna 0
visibilities[4, :]   # Cross-correlation antennas 0-1
visibilities[:, 128] # All baselines at channel 128
```

### Configuration Structure

**File:** [`app/src/correlator/config.py`](app/src/correlator/config.py)

```python
@dataclass
class Config:
    # Array
    n_ants: int = 4
    ant_radius: float = 10.0           # metres, for auto-generated circular array

    # F-engine
    n_channels: int = 256              # FFT size — must be a power of 2
    window: str = "hanning"            # rectangular / hanning / hamming / blackman
    integration_time: float = 1.0      # seconds per output visibility

    # Signal
    sample_rate: float = 1024.0        # Hz
    center_freq: float = 1.42e9        # Hz  (HI line default)

    # Input
    mode: str = "simulate"             # "simulate" or "file"
    input_file: str = ""               # path to .npy file  (mode=file only)
    duration: float = 10.0             # seconds  (mode=simulate only)
    snr: float = 20.0                  # dB       (mode=simulate only)

    # Output
    output_dir: str = "/workspace/outputs"
    output_format: str = "npy"         # npy / hdf5 / fits
```

The `Config` class also provides:

- `validate()` — raises `ValueError` on invalid settings
- `ant_positions()` — returns an `(n_ants, 2)` array of antenna positions on a uniform circle of radius `ant_radius`
- `to_yaml(path)` / `from_yaml(path)` — save and load settings as YAML

> **Note:** Antenna positions are always auto-generated as a uniform circle from `n_ants` and `ant_radius`; explicit per-antenna positions are not currently a configurable setting. Source angles for simulation are fixed in the pipeline (`[0.0, π/6]`, as zenith angles), the delay phase centre is fixed to zenith `[0.0, 0.0, 1.0]`, and quantization/overlap are not exposed (see the F-engine notes above). The `DelayEngine` and `SimulatedStream` classes accept arbitrary 3-D geometry and phase centres directly — only the `Config`/shell surface is restricted.

## Configuration System

### How settings are set

Settings start at the dataclass defaults and are changed interactively in the shell with `set KEY VALUE`. There is **no command-line argument parsing** — the application is a single interactive shell (`python -m correlator`).

Every run writes the `Config` that was used to `config.yaml` in the output directory, so any run can be reproduced.

### Configuration Loading

```python
# Defaults
config = Config()

# Programmatic configuration
config = Config(
    n_ants=8,
    n_channels=512,
    integration_time=2.0,
)

# Save / load YAML  (unknown keys are ignored on load)
config.to_yaml("saved_config.yaml")
config = Config.from_yaml("saved_config.yaml")
```

### Validation

`Config.validate()` is called at the start of every pipeline run and ensures:
- `n_ants >= 2`
- `n_channels` is a power of 2 (and `>= 2`)
- `window` is one of `rectangular` / `hanning` / `hamming` / `blackman`
- `mode` is `simulate` or `file`
- `input_file` is set when `mode == "file"`
- `output_format` is one of `npy` / `hdf5` / `fits`

The shell additionally enforces numeric bounds on each setting as it is entered (e.g. `n_ants` 2–64, `n_channels` 32–4096). Invalid configurations raise `ValueError` with descriptive messages.

## Mathematical Foundations

### Fourier Transform

The F-engine uses the **Discrete Fourier Transform (DFT)**:
```
X[k] = Σ_{n=0}^{N-1} x[n] · e^{-2πjkn/N}
```

Implemented via **FFT (Fast Fourier Transform)** for efficiency:
- Complexity: O(N log N) instead of O(N²)
- NumPy implementation: `numpy.fft.fft()`

### Windowing

Window functions reduce spectral leakage by smoothing signal edges:
```
X_windowed[k] = FFT{ w[n] · x[n] }
```

Trade-offs:
- **Rectangular**: Narrowest main lobe, highest sidelobes (-13 dB)
- **Hanning**: Moderate main lobe, moderate sidelobes (-31 dB)
- **Blackman**: Widest main lobe, lowest sidelobes (-58 dB)

### Cross-Correlation

The visibility function is the cross-correlation of antenna signals:
```
R_ij(τ) = ∫ V_i(t) · V_j*(t-τ) dt
```

In frequency domain (Wiener-Khinchin theorem):
```
S_ij(f) = V_i(f) · V_j*(f)
```

This is exactly what the X-engine computes!

### Van Cittert-Zernike Theorem

Relates visibilities to sky brightness:
```
V(u,v) = ∫∫ I(l,m) · e^{-2πj(ul+vm)} dl dm
```

where:
- `V(u,v)` = visibility at baseline (u,v)
- `I(l,m)` = sky brightness distribution
- `(u,v)` = baseline in wavelengths

This is a **2D Fourier transform** - visibilities sample the Fourier transform of the sky!

### Sensitivity

Thermal noise in visibilities:
```
σ_V = (2 k_B T_sys) / (η √(Δν · t_int))
```

where:
- `k_B` = Boltzmann constant
- `T_sys` = system temperature
- `η` = antenna efficiency
- `Δν` = channel bandwidth
- `t_int` = integration time

**Implication:** Longer integration and wider channels improve SNR.

## Performance Considerations

### Computational Complexity

For `N` antennas, `C` channels, `T` time samples:

**F-Engine:**
```
Cost = N · (T/C) · C·log(C) = N·T·log(C)
Dominated by: FFT operations
Scaling: O(N · T · log C)
```

**X-Engine:**
```
Cost = N²·C·(T/C) = N²·T
Dominated by: Cross-multiplication
Scaling: O(N² · T)
```

**Total:** X-engine dominates for large N (N > ~16)

### Memory Usage

**Time-domain:** `16·N·chunk_size` bytes
**Channelized:** `16·N·n_spectra·n_channels` bytes  
**Visibilities:** `16·N²·n_channels` bytes

Example (64 antennas, 4096 channels):
```
Visibility size = 16 · 2080 · 4096 = ~136 MB per integration
```

### Optimization Strategies

1. **Chunked Processing**
   - Process data in chunks to manage memory
   - Typical chunk size: 4096-8192 samples

2. **NumPy Vectorization**
   - Operations over the channel axis are vectorised (C-speed)
   - *Current state:* the F-engine loops over antennas/spectra and the X-engine loops over baselines in Python; these per-element loops are an obvious target for further vectorisation

3. **FFT Optimization**
   - Use power-of-2 channel counts
   - `numpy.fft` uses the bundled pocketfft implementation

4. **Baseline Triangular Loop**
   - Only compute i ≤ j (use conjugate symmetry)
   - Saves 50% of correlations

5. **Future: GPU Acceleration**
   - F-engine: Batched FFTs on GPU
   - X-engine: Matrix multiplication on GPU
   - Potential speedup: 10-100×

### Performance

Runtime is dominated by the X-engine for large arrays (`O(N² · T)`) and by the F-engine FFTs for small ones (`O(N · T · log C)`). Because the X-engine currently loops over baselines in Python, throughput is well below what a fully vectorised or GPU implementation would achieve.

> No benchmark numbers are published here. The previous version of this document listed measured timings on a specific machine; those figures predated the "Simplify App" rewrite and are no longer representative, so they have been removed. Run the pipeline on your target hardware to obtain current numbers.

## Implementation Details

### Code Organization

```
app/src/correlator/
├── __init__.py           # Package exports (Config, FEngine, XEngine, DelayEngine, ...)
├── __main__.py           # Entry point — launches the interactive shell
├── config.py             # Config dataclass (settings, validation, YAML I/O)
├── shell.py              # Interactive shell (cmd.Cmd): run/set/config/list/plot/...
├── pipeline.py           # FX pipeline orchestration (pipeline.run)
└── core/                 # Core processing modules
    ├── __init__.py
    ├── frontend.py       # Data ingestion (SimulatedStream, BatchFileSource)
    ├── fengine.py        # Channeliser (windowed FFT)
    ├── delay.py          # Geometric delay compensation
    └── xengine.py        # Correlator (cross-multiply + integrate)
```

> **Note:** Network streaming is described as a future enhancement above; there is currently no `streaming/` package or CLI argument layer in the codebase.

### Key Design Patterns

**1. Strategy Pattern (Data Sources)**
```python
class DataSource:
    def stream(self, chunk_size) -> Iterator[np.ndarray]:
        raise NotImplementedError

class SimulatedStream(DataSource): ...
class BatchFileSource(DataSource): ...
```

**2. Pipeline Pattern (Processing)** — see [`pipeline.py`](app/src/correlator/pipeline.py)
```python
for chunk in source:                                     # (n_ants, chunk_size)
    channelised = fengine.process_chunk(chunk)           # (n_ants, n_spectra, n_channels)
    channelised = delay_engine.apply_delays(channelised, freq_channels)
    for spec_idx in range(channelised.shape[1]):
        vis = xengine.correlate_spectrum(channelised[:, spec_idx, :])
        xengine.accumulate(vis)
        if xengine.is_ready():
            integrated = xengine.get_integrated()        # (n_baselines, n_channels)
            # ... save to disk
```

**3. Explicit-Argument Construction**

Engines are constructed with explicit keyword arguments (not the whole `Config` object), which keeps each module decoupled from the configuration schema:
```python
config  = Config.from_yaml("config.yaml")
fengine = FEngine(n_channels=config.n_channels, window_type=config.window)
xengine = XEngine(n_ants=config.n_ants, n_channels=config.n_channels,
                  integration_time=config.integration_time, sample_rate=config.sample_rate)
```

### Error Handling

**Validation Errors:**
```python
if n_ants < 2:
    raise ValueError("n_ants must be >= 2")
if not is_power_of_2(n_channels):
    raise ValueError("n_channels must be power of 2")
```

**Runtime Errors:**
```python
try:
    data = np.load(input_file)
except FileNotFoundError:
    print(f"Error: File {input_file} not found")
    return 1
```

**Graceful Degradation:**
```python
try:
    import h5py
    save_hdf5(data, output_file)
except ImportError:
    print("Warning: h5py not installed, using .npy")
    np.save(output_file, data)
```

### Testing Strategy

Tests live in `tests_harness/` and run with `pytest tests_harness/ -v`, or through the launcher (`./correlator test` on Linux, `correlator.bat test` on Windows), or via `docker compose run --rm test`. The suite is organised into three layers:

```
tests_harness/
├── unit/          # test_fengine, test_xengine, test_delay, test_frontend,
│                  # test_accuracy, test_config
└── integration/   # test_fx_pipeline, test_astronomical_accuracy,
                   # test_correlator_validation
```

Synthetic signals come from `correlator.core.frontend.SimulatedStream`, which
is the same generator the pipeline uses, so tests exercise the production code
path rather than a parallel one that can drift away from it.

**Unit Tests** — exercise individual components in isolation: window functions and FFT output shape/Parseval (`test_fengine`), baseline count/ordering and autocorrelation reality/Hermitian symmetry (`test_xengine`), geometric delays for zenith/horizon sources (`test_delay`), the simulated/batch data sources (`test_frontend`), and config loading including rejection of unknown keys (`test_config`).

**Integration Tests** — run the full FX pipeline end-to-end:
```python
def test_end_to_end_pipeline():
    cfg = Config(n_ants=4, n_channels=256, duration=2.0)
    result = pipeline.run(cfg)
    assert result == 0
    # ... assert visibility files were written
```

**Accuracy / Validation Tests** — compare results to values derived independently of the correlator (`test_accuracy`, `test_astronomical_accuracy`, `test_correlator_validation`):

- **Off-pointing phase.** The load-bearing test. Deliberately mis-point the phase centre by a known angle and assert the residual fringe matches `2π(f_sky + f_k)·b_ij·(ŝ − s0)/c`. A source *at* the phase centre gives zero phase — but so does a delay engine that does nothing, so an on-axis test alone proves nothing.
- **Closure phase.** `arg(V_ij) + arg(V_jk) − arg(V_ik)` must vanish for a point source, and must keep vanishing when arbitrary per-antenna phase errors are injected.
- **FX versus XF.** Cross-check against a lag-domain correlator that shares no code with `FEngine` or `XEngine`.
- **Invariants.** Cauchy–Schwarz (`|V_ij|² ≤ V_ii·V_jj`), conjugate symmetry, autocorrelation reality, amplitude preservation under fringe stopping.
- **Window behaviour.** Amplitude independence across windows, plus a spectral-leakage test — since coherent-gain normalisation makes the on-bin amplitude window-independent, only leakage can show that windowing happens at all.

> **On test geometry.** Use irregular, genuinely 3-D antenna layouts. An earlier version of this suite passed while testing nothing: the simulator defaulted to a 10 m circle at integer coordinates, its geometric term `exp(-2πj·x)` was identically 1 for integer `x`, every antenna received the same signal, and the phase centre was orthogonal to the planar array so the delay stage was a no-op. The tests then asserted the phase was zero. They could not fail.

**External validation** — [`validation/`](validation/) holds an optional harness that re-derives expected visibilities from the measurement equation independently of the correlator, and can cross-check against [pyuvsim](https://github.com/RadioAstronomySoftwareGroup/pyuvsim). It is detachable: nothing in `app/src` imports it and it is excluded from the Docker image.

### Console Output

The pipeline reports progress with plain `print` statements (there is no structured-logging or metrics framework). A typical run looks like:

```
Antennas        : 4
Channels        : 256  (window: hanning)
Sample rate     : 1024.0 Hz
Centre freq     : 1420.000 MHz
Integration     : 1.0 s
Mode            : simulate
Output          : /workspace/outputs/

  Integration    1  saved
  Integration    2  saved
  ...
Complete: 10 integrations written to /workspace/outputs/
```

Errors raised during a run (e.g. validation failures, missing input files) are caught by the shell and printed as `Error: <message>`, leaving the shell running.

## Example Data

### Test Signals

**File:** `workspace/inputs/generate_test_data.py` — run it (`python workspace/inputs/generate_test_data.py`) to write the datasets below as `.npy` files alongside the script. Each is a complex `(n_ants, n_samples)` array suitable for `mode=file`.

**1. Simple Signal** (`simple_signal.npy`)
- 4 antennas, 4096 samples
- Single sinusoid at 10 Hz
- Linear phase delays across antennas simulate a point source
- SNR: 20 dB

**2. Dual Source** (`dual_source_signal.npy`)
- 4 antennas, 4096 samples
- Two sources at different frequencies (10 Hz, 15 Hz)
- Tests source separation

**3. Pulsed Signal** (`pulsed_signal.npy`)
- 4 antennas, 4096 samples
- Pulsed carrier (pulsar-like), 20 Hz carrier, 30% duty cycle
- Tests time variability

**4. Quick Test** (`quick_test.npy`)
- 4 antennas, 512 samples
- A small simple-signal dataset for fast tests

**5. Large Test** (`large_test.npy`)
- 8 antennas, 16384 samples
- Larger simple-signal dataset for performance testing

### Generating Custom Data

```python
import numpy as np

n_ants = 4
n_samples = 8192
sample_rate = 1024.0

# Create time array
t = np.arange(n_samples) / sample_rate

# Generate signal
freq = 10.0  # Hz
signal = np.exp(2j * np.pi * freq * t)

# Add phase delays for each antenna
data = np.zeros((n_ants, n_samples), dtype=complex)
for i in range(n_ants):
    phase = i * np.pi / 4  # 45 degrees per antenna
    data[i] = signal * np.exp(1j * phase)

# Add noise
noise_power = 0.1
noise = np.random.randn(n_ants, n_samples) + \
        1j * np.random.randn(n_ants, n_samples)
data += noise * np.sqrt(noise_power / 2)

# Save
np.save('my_test_data.npy', data)
```

## Output Data Processing

### Loading and Analyzing Visibilities

```python
import numpy as np
import matplotlib.pyplot as plt

# Load visibility data
vis = np.load('workspace/outputs/visibility_0001.npy')
n_baselines, n_channels = vis.shape

# Extract autocorrelation (antenna 0)
auto_0 = vis[0, :].real  # Autocorr is real

# Plot power spectrum
plt.figure(figsize=(10, 6))
plt.plot(auto_0)
plt.xlabel('Channel')
plt.ylabel('Power')
plt.title('Antenna 0 Power Spectrum')
plt.grid(True)
plt.savefig('power_spectrum.png')

# Extract cross-correlation (antennas 0-1)
# Baseline index depends on n_ants
n_ants = 4
cross_01_idx = n_ants  # First cross-correlation
cross_01 = vis[cross_01_idx, :]

# Plot amplitude and phase
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))

ax1.plot(np.abs(cross_01))
ax1.set_ylabel('Amplitude')
ax1.set_title('Baseline 0-1 Visibility')
ax1.grid(True)

ax2.plot(np.angle(cross_01))
ax2.set_ylabel('Phase (radians)')
ax2.set_xlabel('Channel')
ax2.grid(True)

plt.tight_layout()
plt.savefig('visibility_analysis.png')
```

### Computing UV Coverage

```python
def get_uv_coverage(ant_positions, wavelength):
    """Compute UV coverage for an array."""
    n_ants = len(ant_positions)
    baselines = []
    
    for i in range(n_ants):
        for j in range(i+1, n_ants):
            # Baseline vector
            b = ant_positions[j] - ant_positions[i]
            # Convert to wavelengths
            u = b[0] / wavelength
            v = b[1] / wavelength
            baselines.append([u, v])
            # Add conjugate baseline
            baselines.append([-u, -v])
    
    return np.array(baselines)

# Example
ant_pos = np.array([[0, 0], [10, 0], [0, 10], [10, 10]])
wavelength = 0.21  # 1.42 GHz HI line
uv = get_uv_coverage(ant_pos, wavelength)

plt.figure(figsize=(8, 8))
plt.plot(uv[:, 0], uv[:, 1], 'o')
plt.xlabel('u (wavelengths)')
plt.ylabel('v (wavelengths)')
plt.title('UV Coverage')
plt.axis('equal')
plt.grid(True)
plt.savefig('uv_coverage.png')
```

### Imaging (Basic)

```python
def simple_image(visibilities, uv_coords, image_size=256):
    """Create image via inverse FFT (simplified)."""
    # Create UV grid
    grid = np.zeros((image_size, image_size), dtype=complex)
    
    # Grid visibilities
    center = image_size // 2
    for (u, v), vis in zip(uv_coords, visibilities):
        # Convert u,v to grid coordinates
        iu = int(u + center)
        iv = int(v + center)
        if 0 <= iu < image_size and 0 <= iv < image_size:
            grid[iv, iu] += vis
    
    # Inverse FFT to get image
    image = np.fft.ifft2(np.fft.ifftshift(grid))
    
    return np.abs(image)

# Example usage
vis_avg = np.mean(vis, axis=1)  # Average over frequency
image = simple_image(vis_avg, uv)

plt.figure(figsize=(8, 8))
plt.imshow(image, origin='lower', cmap='hot')
plt.colorbar(label='Intensity')
plt.title('Radio Image (Simplified)')
plt.savefig('radio_image.png')
```

## Deployment

### Docker Deployment

The image is built from a multi-stage [`app/Dockerfile`](app/Dockerfile) and defaults to launching the interactive shell. (Abbreviated — see the file for the full builder stage.)

```dockerfile
FROM python:3.11-slim AS builder
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends build-essential
COPY requirements.txt /app/
RUN pip install --prefix=/install -r requirements.txt
COPY app/src/ /app/src/
RUN pip install --prefix=/install /app/src/

FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /install /usr/local
ENV PYTHONPATH=/usr/local/lib/python3.11/site-packages
ENV PYTHONUNBUFFERED=1
CMD ["python", "-m", "correlator"]      # interactive shell
```

**Docker Compose** ([`docker-compose.yml`](docker-compose.yml)) defines a `correlator` service (interactive shell) and a `test` service (pytest):

```yaml
services:
  correlator:
    build:
      context: .
      dockerfile: app/Dockerfile
    image: telescope-correlator:latest
    volumes:
      - ./workspace:/workspace
    stdin_open: true
    tty: true
    command: ["python", "-m", "correlator"]

  test:
    image: telescope-correlator:latest
    volumes:
      - .:/workspace
    working_dir: /workspace
    command: ["pytest", "tests_harness/", "-v", "--tb=short"]
    environment:
      - PYTHONPATH=/workspace/app/src:/usr/local/lib/python3.11/site-packages
```

### Kubernetes Deployment (illustrative)

> The repository does **not** include Kubernetes manifests. The example below is an illustrative starting point for a long-running deployment, not a tested artifact in this project.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: correlator
spec:
  replicas: 1
  selector:
    matchLabels:
      app: correlator
  template:
    metadata:
      labels:
        app: correlator
    spec:
      containers:
      - name: correlator
        image: telescope-correlator:latest
        resources:
          requests:
            memory: "16Gi"
            cpu: "8"
          limits:
            memory: "32Gi"
            cpu: "16"
        volumeMounts:
        - name: data
          mountPath: /workspace
      volumes:
      - name: data
        persistentVolumeClaim:
          claimName: correlator-data
```

## Future Enhancements

### Planned Features

1. **GPU Acceleration**
   - CuPy for FFTs
   - CUDA kernels for correlation
   - Target: 100× speedup

2. **Distributed Processing**
   - Multiple X-engine nodes
   - Frequency-domain data distribution
   - Scalability to 1000+ antennas

3. **Advanced Calibration**
   - Bandpass calibration
   - Gain calibration
   - Phase calibration
   - RFI detection and mitigation

4. **Real-time Streaming**
   - SPEAD protocol support
   - ZeroMQ transport
   - Buffering and flow control

5. **Enhanced Output**
   - Measurement Set (MS) format
   - CASA compatibility
   - Metadata standards compliance

6. **Monitoring Dashboard**
   - Real-time performance metrics
   - Data quality indicators
   - System health monitoring

## References

### Textbooks

1. **Interferometry and Synthesis in Radio Astronomy**
   Thompson, Moran, & Swenson (2017)
   - Comprehensive reference for radio interferometry

2. **Essential Radio Astronomy**
   Condon & Ransom (2016)
   - Modern introduction to radio astronomy techniques

### Papers

1. **FX Correlator Architecture**
   Chikada et al. (1987)
   "A 6×320 MHz, 1024-channel FFT cross spectrum analyzer..."

2. **LOFAR Correlator**
   Romein (2010)
   "An Efficient Work-Distribution Strategy for Gridding Radio-Telescope Data on GPUs"

3. **MWA Correlator**
   Ord et al. (2015)
   "The Murchison Widefield Array Correlator"

### Software

1. **CASACORE**: Radio astronomy libraries
2. **GPUSPEC**: GPU correlator implementation
3. **xGPU**: CUDA X-engine library

## Glossary

- **Antenna**: Radio telescope receiver element
- **Autocorrelation**: Correlation of an antenna with itself (power spectrum)
- **Baseline**: Pair of antennas forming an interferometer
- **Channelization**: Converting time-domain to frequency channels
- **Cross-correlation**: Correlation between two different antennas
- **F-Engine**: Fourier (channelization) processing stage
- **FFT**: Fast Fourier Transform algorithm
- **Fringe**: Interference pattern from two antennas
- **Integration**: Time-averaging to reduce noise
- **Quantization**: Bit-depth reduction (e.g., 8-bit)
- **Spectral Resolution**: Frequency width of each channel
- **Visibility**: Complex correlation measurement (amplitude + phase)
- **Window Function**: Taper applied before FFT
- **X-Engine**: Cross-multiplication (correlation) processing stage

## Conclusion

The Telescope Correlator implements a clean, modular FX architecture covering both simulated signals and recorded data files. The modular design enables easy testing, validation, and future enhancements (network streaming, GPU acceleration, calibration) while maintaining scientific accuracy.

For usage instructions, see [README.md](README.md).

---

**Last Updated:** June 2026  
**Contributors:** Francois
