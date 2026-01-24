# Telescope Correlator - FX Architecture

A production-ready software correlator for radio telescope arrays implementing the FX (Fourier Transform-Cross Multiply) architecture. This correlator processes time-domain antenna signals to produce calibrated visibility measurements used in radio astronomy imaging.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [Usage](#usage)
  - [Development Mode](#development-mode)
  - [Production Mode](#production-mode)
  - [File-Based Processing](#file-based-processing)
- [Configuration](#configuration)
- [Output Data](#output-data)
- [Testing](#testing)
- [Examples](#examples)
- [Troubleshooting](#troubleshooting)
- [System Requirements](#system-requirements)

## Overview

The Telescope Correlator is a Python-based implementation of an FX correlator designed for radio telescope arrays. It converts time-domain signals from multiple antennas into frequency-domain visibilities, which are the fundamental measurements in radio interferometry.

### What is an FX Correlator?

An FX correlator processes antenna signals in two stages:
- **F-Engine (Fourier Transform)**: Converts time-domain signals into frequency channels using windowed FFT
- **X-Engine (Cross-Multiply)**: Computes cross-correlations between antenna pairs to produce visibilities

This architecture is efficient for wide-field imaging and is used in many modern radio telescopes.

## Features

### Core Capabilities
- ✅ **Dual Operation Modes**: Development (simulation) and Production (real data)
- ✅ **FX Pipeline**: Complete F-engine channelization and X-engine correlation
- ✅ **Geometric Delay Compensation**: Corrects for antenna position differences
- ✅ **Flexible Data Sources**: Simulated, file-based, and network streaming
- ✅ **Multiple Window Functions**: Hanning, Hamming, Blackman, Rectangular
- ✅ **Configurable Parameters**: FFT size, integration time, overlap, quantization
- ✅ **Multiple Output Formats**: NumPy (.npy), HDF5 (.h5), FITS (.fits)

### Advanced Features
- 🔧 **Quantization Emulation**: 8/16-bit quantization for realistic system modeling
- 🔧 **Polyphase Filterbank Mode**: Overlapping FFT windows for improved frequency response
- 🔧 **Real-time Simulation**: Time-synchronized data generation
- 🔧 **Batch Processing**: Process pre-recorded data files
- 🔧 **Docker Support**: Containerized deployment for reproducibility

## Quick Start

### Using Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/yourusername/telescope-correlator.git
cd telescope-correlator

# Build the Docker image
correlator.bat build     # Windows
# or
./correlator build       # Linux/Mac

# Start interactive development mode
correlator.bat dev       # Windows
# or
./correlator dev         # Linux/Mac
```

### Quick Test Run

```bash
# Run a quick simulation with 4 antennas
correlator.bat dev run --n-ants 4 --sim-duration 5.0

# Check the output
ls workspace/outputs/
```

## Installation

### Docker Installation (Recommended)

1. **Install Docker Desktop**
   - Windows/Mac: [Docker Desktop](https://www.docker.com/products/docker-desktop)
   - Linux: [Docker Engine](https://docs.docker.com/engine/install/)

2. **Build the Correlator Image**
   ```bash
   # Windows
   correlator.bat build
   
   # Linux/Mac
   ./correlator build
   ```

3. **Verify Installation**
   ```bash
   correlator.bat dev --help
   ```

### Native Python Installation

If you prefer to run without Docker:

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Install the package
pip install -e app/src/

# Run correlator
python -m correlator dev --help
```

**Requirements:**
- Python 3.11+
- NumPy >= 1.25
- SciPy >= 1.11
- PyYAML >= 6.0
- h5py >= 3.10 (for HDF5 output)
- astropy >= 6.0 (for FITS output)

## Usage

The correlator has two primary operation modes:

### Development Mode

Development mode is for simulations, testing, and learning. It generates synthetic antenna signals and is perfect for algorithm development.

#### Interactive CLI

```bash
correlator.bat dev
```

This starts an interactive shell where you can:
- Configure parameters interactively
- Run simulations
- Inspect results
- Iterate quickly

#### Command-Line Execution

```bash
# Basic simulation with default parameters
correlator.bat dev run

# Custom configuration
correlator.bat dev run --n-ants 8 --n-channels 512 --integration-time 2.0

# With specific output directory
correlator.bat dev run --output-dir workspace/outputs/test1

# Longer simulation
correlator.bat dev run --sim-duration 30.0 --max-integrations 10
```

#### Common Development Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `--n-ants` | Number of antennas | 4 |
| `--n-channels` | FFT size (power of 2) | 256 |
| `--sample-rate` | Sample rate (Hz) | 1024.0 |
| `--integration-time` | Integration period (sec) | 1.0 |
| `--sim-duration` | Simulation length (sec) | 10.0 |
| `--sim-snr` | Signal SNR (dB) | 20.0 |
| `--window-type` | Window function | hanning |
| `--output-dir` | Output directory | /workspace/outputs |

### Production Mode

Production mode processes real telescope data from files or network streams.

#### Interactive CLI

```bash
correlator.bat prod
```

#### Streaming from Network

```bash
# TCP streaming
correlator.bat prod stream --source tcp://10.0.0.1:7148

# With custom configuration
correlator.bat prod stream --source tcp://antenna-server:7148 --config workspace/configs/prod/default.yaml
```

#### Processing Recorded Data

```bash
# Process from file
correlator.bat prod process --input-file workspace/inputs/observation_20260124.npy

# With specific configuration
correlator.bat prod process --input-file data/obs.npy --config workspace/configs/prod/array64.yaml
```

### File-Based Processing

Process pre-recorded antenna data from NumPy files:

```bash
# Using development mode with file input
correlator.bat dev run --mode file --input-file workspace/inputs/simple_signal.npy

# Or create a configuration file
correlator.bat dev run --config workspace/configs/my_config.yaml
```

**Data Format Requirements:**
- NumPy array (.npy file)
- Shape: `(n_antennas, n_samples)`
- Dtype: `complex64` or `complex128`
- Complex time-domain signals

## Configuration

### Configuration Files

Configuration files use YAML format and allow you to specify all correlator parameters.

#### Example: Development Configuration

```yaml
# dev_config.yaml
operation_mode: development
data_source: simulated

# Array configuration
n_ants: 8
ant_radius: 10.0  # meters

# Signal parameters
sample_rate: 1024.0  # Hz
center_freq: 1420000000.0  # 1.42 GHz (HI line)

# F-engine
n_channels: 256
window_type: hanning
quantize_bits: 0  # No quantization
overlap_factor: 0.0

# X-engine
integration_time: 1.0  # seconds

# Simulation
sim_duration: 20.0
sim_snr: 20.0
sim_source_angles: [0.0, 0.5236]  # radians

# Delay compensation
enable_delays: true
phase_center: [1.0, 0.0, 0.0]  # Unit vector

# Output
output_dir: workspace/outputs
save_visibilities: true
output_format: npy
max_integrations: null
```

#### Example: Production Configuration

```yaml
# prod_config.yaml
operation_mode: production
data_source: network_stream

# Network configuration
stream_protocol: tcp
stream_address: telescope-server:7148
stream_buffer_size: 10485760  # 10 MB

# Array (64-element array)
n_ants: 64
ant_radius: 100.0

# Signal parameters
sample_rate: 2048000.0  # 2.048 MHz
center_freq: 1420405751.77  # Precise HI line

# F-engine (high resolution)
n_channels: 4096
window_type: hanning
quantize_bits: 8  # Production quantization
overlap_factor: 0.25

# X-engine
integration_time: 1.0

# Output
output_dir: workspace/outputs/prod
output_format: hdf5
save_channelised: false

# Production features
enable_monitoring: true
enable_logging: true
log_level: INFO
log_file: workspace/logs/correlator.log
```

#### Loading Configuration

```bash
# From command line
correlator.bat dev run --config workspace/configs/my_config.yaml

# Override specific parameters
correlator.bat dev run --config my_config.yaml --n-ants 16 --sim-duration 5.0
```

### Configuration Parameters

#### Array Configuration
- `n_ants`: Number of antennas (≥ 2)
- `ant_positions`: Explicit antenna positions `[[x1,y1], [x2,y2], ...]` or null for circular array
- `ant_radius`: Radius for auto-generated circular array (meters)

#### Signal Parameters
- `sample_rate`: ADC sample rate (Hz)
- `center_freq`: Observation center frequency (Hz)

#### F-Engine Parameters
- `n_channels`: Number of frequency channels (must be power of 2)
- `window_type`: Window function (`rectangular`, `hanning`, `hamming`, `blackman`)
- `quantize_bits`: Quantization bit depth (0 = no quantization, 8/16 typical)
- `overlap_factor`: FFT window overlap (0.0 to 0.5)

#### X-Engine Parameters
- `integration_time`: Time integration period (seconds)

#### Delay Compensation
- `enable_delays`: Enable geometric delay correction (true/false)
- `phase_center`: Pointing direction as unit vector `[x, y, z]`

#### Output Parameters
- `output_dir`: Directory for output files
- `output_format`: File format (`npy`, `hdf5`, `fits`)
- `save_channelised`: Save intermediate F-engine output (true/false)
- `save_visibilities`: Save integrated visibilities (true/false)
- `max_integrations`: Maximum integrations to compute (null = unlimited)

## Output Data

The correlator produces visibility measurements for each integration period.

### File Naming Convention

```
workspace/outputs/
├── visibility_0001.npy      # First integration
├── visibility_0002.npy      # Second integration
├── visibility_0003.npy
├── ...
├── config.yaml              # Configuration used for this run
└── channelised.npy          # (Optional) F-engine output
```

### Visibility Data Format

**Shape:** `(n_baselines, n_channels)`

where:
- `n_baselines = n_ants * (n_ants + 1) / 2` (includes autocorrelations)
- For 4 antennas: 10 baselines
- For 8 antennas: 36 baselines
- For 64 antennas: 2080 baselines

**Baseline Ordering:**
1. Autocorrelations first: (0,0), (1,1), (2,2), ...
2. Cross-correlations: (0,1), (0,2), ..., (n-2,n-1)

**Data Type:** `complex128` (real for autocorrelations)

### Reading Output Data

```python
import numpy as np

# Load visibility data
vis = np.load('workspace/outputs/visibility_0001.npy')
print(f"Shape: {vis.shape}")  # (n_baselines, n_channels)

# Extract autocorrelations (antenna powers)
n_ants = 4
autocorr = vis[:n_ants, :]  # First n_ants baselines

# Extract cross-correlations
cross_corr = vis[n_ants:, :]

# Examine specific baseline (e.g., antennas 0-1)
baseline_01 = vis[4, :]  # Depends on ordering
```

### HDF5 Format

When using `output_format: hdf5`:

```python
import h5py

with h5py.File('workspace/outputs/visibility_0001.h5', 'r') as f:
    vis = f['visibilities'][:]
    print(f"Shape: {vis.shape}")
    print(f"Attributes: {dict(f.attrs)}")
```

### FITS Format

When using `output_format: fits`:

```python
from astropy.io import fits

with fits.open('workspace/outputs/visibility_0001.fits') as hdul:
    real_part = hdul['REAL'].data
    imag_part = hdul['IMAG'].data
    vis = real_part + 1j * imag_part
```

## Testing

The correlator includes comprehensive test suites.

### Run All Tests

```bash
# Using Docker
correlator.bat test

# Or with native Python
pytest tests_harness/ -v
```

### Test Categories

1. **Unit Tests** (`tests_harness/unit/`)
   - Individual component testing
   - F-engine FFT accuracy
   - X-engine correlation
   - Delay compensation

2. **Integration Tests** (`tests_harness/integration/`)
   - Full pipeline testing
   - End-to-end workflows
   - Data format validation

3. **Validation Tests** (`tests_harness/validate_accuracy.py`)
   - Analytical validation
   - Known signal testing
   - Accuracy benchmarking

### Run Specific Tests

```bash
# Test F-engine only
pytest tests_harness/unit/test_fengine.py -v

# Test delay compensation
pytest tests_harness/unit/test_delay.py -v

# Run validation suite
python tests_harness/validate_accuracy.py all
```

## Examples

### Example 1: Basic Simulation

```bash
# Simple 4-antenna correlation
correlator.bat dev run --n-ants 4 --sim-duration 10.0 --output-dir workspace/outputs/ex1
```

### Example 2: Large Array Simulation

```bash
# 64-antenna array with high resolution
correlator.bat dev run \
  --n-ants 64 \
  --n-channels 4096 \
  --integration-time 2.0 \
  --sim-duration 60.0 \
  --output-dir workspace/outputs/ex2
```

### Example 3: Process Test Data

```bash
# Generate test data first
cd workspace/inputs
python generate_test_data.py

# Process the test data
cd ../..
correlator.bat dev run \
  --mode file \
  --input-file workspace/inputs/large_test.npy \
  --n-channels 512 \
  --output-dir workspace/outputs/ex3
```

### Example 4: Custom Configuration

Create `my_experiment.yaml`:

```yaml
operation_mode: development
data_source: simulated
n_ants: 16
n_channels: 1024
sample_rate: 2048.0
integration_time: 5.0
sim_duration: 120.0
window_type: blackman
overlap_factor: 0.25
output_format: hdf5
```

Run:

```bash
correlator.bat dev run --config my_experiment.yaml
```

### Example 5: Astronomical Observation Simulation

```bash
# Simulate HI line observation
correlator.bat dev run \
  --n-ants 8 \
  --center-freq 1420000000 \
  --sample-rate 2048000 \
  --n-channels 2048 \
  --integration-time 10.0 \
  --sim-duration 600.0 \
  --output-format hdf5
```

## Troubleshooting

### Common Issues

#### 1. Docker Container Won't Start

```bash
# Check Docker is running
docker --version

# Remove old containers
docker ps -a
docker rm telescope-correlator

# Rebuild image
correlator.bat build
```

#### 2. "n_channels must be a power of 2"

The FFT requires the number of channels to be a power of 2 (e.g., 64, 128, 256, 512, 1024, 2048, 4096).

```bash
# Correct
correlator.bat dev run --n-channels 512

# Incorrect
correlator.bat dev run --n-channels 500  # Error!
```

#### 3. Out of Memory

For large arrays or high channel counts:

```bash
# Reduce parameters
--n-channels 256    # Instead of 4096
--chunk-size 2048   # Instead of 8192
--max-integrations 10  # Limit output
```

#### 4. File Not Found Errors

Ensure paths use the correct workspace mount:

```bash
# Correct (inside Docker container)
--input-file /workspace/inputs/data.npy
--output-dir /workspace/outputs/

# Incorrect
--input-file ./data.npy  # May not be mounted
```

#### 5. Visibility Shape Mismatch

For `n_ants` antennas:
- Number of baselines = `n_ants * (n_ants + 1) / 2`
- 4 ants → 10 baselines
- 8 ants → 36 baselines
- 16 ants → 136 baselines

### Getting Help

```bash
# Mode help
correlator.bat dev --help
correlator.bat prod --help

# Command help
correlator.bat dev run --help
```

## System Requirements

### Minimum Requirements
- CPU: 2 cores, 2.0 GHz
- RAM: 4 GB
- Disk: 5 GB free space
- OS: Windows 10/11, Linux (Ubuntu 20.04+), macOS 11+

### Recommended for Production
- CPU: 8+ cores, 3.0+ GHz
- RAM: 16+ GB
- Disk: 100+ GB SSD
- GPU: Optional (for future CUDA acceleration)

### Performance Guidelines

| Array Size | Channels | Integration | RAM Usage | Processing Speed |
|------------|----------|-------------|-----------|------------------|
| 4 ants     | 256      | 1s          | ~500 MB   | Real-time        |
| 8 ants     | 512      | 1s          | ~1 GB     | Real-time        |
| 16 ants    | 1024     | 1s          | ~2 GB     | Near real-time   |
| 64 ants    | 4096     | 1s          | ~8 GB     | Batch preferred  |

## Architecture Overview

For detailed information about the system architecture, signal processing algorithms, and implementation details, see [ARCHITECTURE.md](ARCHITECTURE.md).

## Contributing

Contributions are welcome! Please ensure:
- All tests pass: `correlator.bat test`
- Code follows existing style
- Add tests for new features
- Update documentation

## License

This project is part of academic research. Please cite appropriately if used in publications.

## Citation

If you use this correlator in your research, please cite:

```
Telescope Correlator - FX Architecture
[Author], [Institution], 2026
```

## Contact

For questions, issues, or contributions:
- Create an issue on GitHub
- Email: [your-email@institution.edu]

## Acknowledgments

This correlator was developed as part of [Institution] research in radio astronomy signal processing and software-defined radio telescopes.

---

**Version:** 1.0.0  
**Last Updated:** January 2026  
**Documentation:** [ARCHITECTURE.md](ARCHITECTURE.md) for technical details
