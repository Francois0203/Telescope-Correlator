# FX Correlator Architecture

This document describes the architecture and implementation of the FX correlator for radio telescope arrays.

## Overview

The correlator implements a standard **FX architecture** used in radio astronomy:
- **F-Engine (Frontend + Channeliser)**: Converts time-domain signals to frequency domain
- **X-Engine (Cross-Correlator)**: Computes cross-products between antenna pairs

This design follows Chapter 2.3 of the dissertation "A Python Correlator for Radio Astronomy".

## Data Flow

```
┌─────────────┐
│  Data       │  Raw time-domain signals (batch files or simulated)
│  Source     │  Shape: (n_ants, n_samples) complex128
└──────┬──────┘
       │
       ↓
┌─────────────┐
│  F-Engine   │  Windowed FFT channelisation
│(Channeliser)│  - Apply window function (Hanning, Hamming, etc.)
└──────┬──────┘  - Perform FFT with optional overlap
       │          - Optional quantization emulation
       ↓          Shape: (n_ants, n_spectra, n_channels)
┌─────────────┐
│   Delay     │  Geometric delay compensation
│   Engine    │  - Calculate delays from antenna positions
└──────┬──────┘  - Apply phase rotations per channel
       │          Shape: (n_ants, n_spectra, n_channels)
       ↓
┌─────────────┐
│  X-Engine   │  Cross-correlation and accumulation
│ (Correlator)│  - Compute V_ij = E_i * conj(E_j) for all pairs
└──────┬──────┘  - Accumulate over integration time
       │          Shape: (n_baselines, n_channels)
       ↓
┌─────────────┐
│  Output     │  Save visibility products to .npy files
│  Files      │  One file per integration period
└─────────────┘
```

## Module Descriptions

### `correlator/config.py`
**Purpose**: Configuration management with YAML support

**Key Classes**:
- `CorrelatorConfig`: Dataclass holding all configuration parameters
  - Array configuration (n_ants, positions, radius)
  - Signal parameters (sample_rate, center_freq)
  - F-Engine settings (n_channels, window_type, quantize_bits, overlap)
  - X-Engine settings (integration_time)
  - Data source (mode, input_file, simulation parameters)
  - Output options (output_dir, save_channelised)

**Methods**:
- `from_yaml()`: Load configuration from YAML file
- `to_yaml()`: Save configuration for reproducibility
- `get_ant_positions()`: Generate or return antenna positions

### `correlator/frontend.py`
**Purpose**: Data ingestion from various sources

**Key Classes**:
- `DataSource`: Base class for data sources
  - `stream(chunk_size)`: Iterator yielding (n_ants, chunk_size) arrays

- `SimulatedStream`: Generate synthetic antenna signals
  - Simulates point sources at specified angles
  - Adds realistic noise with configurable SNR
  - Includes geometric delays based on antenna positions
  - Optional real-time streaming simulation

- `BatchFileSource`: Load data from .npy files
  - Chunks large files for memory efficiency
  - Yields data in (n_ants, chunk_size) format

### `correlator/fengine.py`
**Purpose**: F-Engine channeliser (time → frequency conversion)

**Key Functions**:
- `get_window()`: Generate window functions (Hanning, Hamming, Blackman, Rectangular)
- `quantize_signal()`: Emulate ADC quantization with configurable bit depth

**Key Classes**:
- `FEngine`: Windowed FFT channeliser
  - `process_chunk(signals)`: Convert time-domain chunk to frequency-domain
    - Input: (n_ants, n_samples)
    - Output: (n_ants, n_spectra, n_channels)
  - Supports overlapped processing for better spectral resolution
  - Optional quantization to emulate hardware constraints

**Algorithm**:
1. Apply quantization (if enabled)
2. Compute number of FFT windows that fit in chunk
3. For each window position:
   - Extract n_channels samples
   - Apply window function (reduces spectral leakage)
   - Perform FFT
   - Store in output array

### `correlator/delay.py`
**Purpose**: Geometric delay compensation and phasing

**Key Functions**:
- `calculate_geometric_delays()`: Compute delays from antenna positions and source direction

**Key Classes**:
- `DelayEngine`: Phase tracking and delay compensation
  - `set_phase_center()`: Set tracking direction (source position)
  - `apply_delays()`: Apply phase corrections to channelised data
    - For each antenna: phase = exp(-2π * delay * frequency)
    - Corrects for path length differences

**Algorithm**:
1. Calculate geometric delay: delay = (antenna_position · source_direction) / c
2. Reference to first antenna (or array center)
3. For each frequency channel:
   - Compute phase rotation: exp(-j * 2π * delay * freq)
   - Multiply channelised data by phasor

### `correlator/xengine.py`
**Purpose**: X-Engine correlator core (cross-multiplication)

**Key Functions**:
- `get_baseline_indices()`: Generate list of antenna pairs (i,j) where i ≤ j

**Key Classes**:
- `XEngine`: Cross-correlation and accumulation
  - `correlate_spectrum()`: Compute visibilities for one time sample
    - V_ij = E_i * conj(E_j) for all antenna pairs
    - Input: (n_ants, n_channels)
    - Output: (n_baselines, n_channels)
  
  - `accumulate()`: Add visibilities to integration buffer
  
  - `is_ready()`: Check if integration period is complete
  
  - `get_integrated()`: Return averaged visibilities and reset

**Baseline Indexing**:
- For N antennas, computes N(N+1)/2 baselines (including autocorrelations)
- Example for 4 antennas: (0,0), (0,1), (0,2), (0,3), (1,1), (1,2), (1,3), (2,2), (2,3), (3,3)
- Total: 10 baselines

**Integration**:
- Accumulates visibilities over multiple spectra
- Integration time = spectra_per_integration × (FFT_size / sample_rate)
- Averaging reduces noise: SNR ∝ √(integration_time)

### `correlator/cli.py`
**Purpose**: Command-line interface and pipeline orchestration

**Key Functions**:
- `run_correlator(config)`: Execute full FX pipeline
  1. Initialize components (frontend, F-engine, delay engine, X-engine)
  2. Process data in chunks
  3. Save outputs and configuration

- `main()`: Parse command-line arguments and run correlator
  - Supports YAML configuration files
  - CLI arguments override file settings
  - Comprehensive options for all parameters

**Command-Line Options**:
```bash
# Run with default settings (4 antennas, 256 channels, simulated)
python -m correlator

# Custom array and channelisation
python -m correlator --n-ants 8 --n-channels 1024 --window-type hamming

# Enable quantization emulation
python -m correlator --quantize-bits 8

# Run from configuration file
python -m correlator --config my_config.yaml

# Process batch data from file
python -m correlator --mode file --input-file data.npy

# Longer simulation with real-time streaming
python -m correlator --sim-duration 60.0 --sim-realtime
```

## Configuration

### Default Settings
```yaml
n_ants: 4                    # Number of antennas
n_channels: 256              # Frequency channels (power of 2)
sample_rate: 1024.0          # Hz
integration_time: 1.0        # seconds
window_type: hanning         # Windowing function
quantize_bits: 0             # 0 = no quantization
mode: simulated              # Data source
sim_snr: 20.0               # Simulation SNR (dB)
enable_delays: true          # Delay compensation
```

### Configuration File Example
```yaml
# Array configuration
n_ants: 8
ant_radius: 25.0  # meters

# Signal parameters
sample_rate: 2048.0
center_freq: 1.4e9  # 1.4 GHz (L-band)

# F-Engine
n_channels: 512
window_type: hamming
quantize_bits: 8
overlap_factor: 0.25

# X-Engine
integration_time: 2.0

# Simulation
sim_duration: 30.0
sim_snr: 15.0
sim_source_angles: [0.0, 0.785, 1.571]  # 0°, 45°, 90°

# Output
output_dir: ./outputs
save_channelised: true
max_integrations: 100
```

## Output Format

### Visibility Files
- Filename: `visibility_NNNN.npy`
- Shape: `(n_baselines, n_channels)`
- dtype: `complex128`
- Content: Averaged cross-correlations V_ij for each frequency channel

### Baseline Ordering
For N antennas, baselines are ordered as:
```
[
  (0,0), (0,1), ..., (0,N-1),  # Antenna 0 with all others
  (1,1), (1,2), ..., (1,N-1),  # Antenna 1 with remaining
  ...
  (N-1,N-1)                     # Autocorrelation
]
```

### Configuration File
- Filename: `config.yaml`
- Contains all parameters used for the run
- Ensures reproducibility

### Optional Channelised Output
- Filename: `channelised.npy`
- Shape: `(n_chunks, n_ants, n_spectra, n_channels)`
- Intermediate F-Engine output for debugging

## Performance Considerations

### Memory Usage
- Each visibility integration: `n_baselines × n_channels × 16 bytes`
- Example (4 ants, 256 channels): 10 × 256 × 16 = 41 KB per integration
- Channelised data (if saved): Much larger, consider disk space

### Processing Speed
- FFT computation dominates: O(n_channels × log(n_channels))
- Cross-correlation: O(n_ants²× n_channels)
- Scales linearly with data volume

### Optimization Opportunities
- Use FFTW for faster FFTs
- GPU acceleration for correlation (cupy)
- Multi-processing for parallel antenna processing
- Streaming output to avoid memory accumulation

## Testing

### Unit Tests (Planned)
- `test_fengine.py`: Test windowing, FFT, quantization
- `test_xengine.py`: Test baseline indexing, correlation, accumulation
- `test_delay.py`: Test delay calculation and phase correction
- `test_frontend.py`: Test data sources and chunking

### Integration Tests (Planned)
- `test_fx_pipeline.py`: End-to-end pipeline test
- Verify output shapes and data ranges
- Test with known signal (verify fringe patterns)

## References

- Dissertation: "A Python Correlator for Radio Astronomy", Chapter 2.3
- Thompson, Moran, Swenson: "Interferometry and Synthesis in Radio Astronomy"
- FX Correlator: Weinreb & Vivekanand (2006)

## Future Enhancements

1. **Polyphase Filterbank**: Replace simple windowing with PFB for better channel response
2. **GPU Acceleration**: cupy/numba for 10-100× speedup
3. **Real-time Mode**: Process data as it arrives from receivers
4. **Calibration Pipeline**: Gain, phase, bandpass calibration
5. **Imaging Backend**: Integrate with WSClean or CASA for image reconstruction
6. **Distributed Processing**: Multi-node processing with MPI
7. **HDF5 Output**: Support for Measurement Set format