# Telescope Correlator - FX Architecture

A production-ready software correlator for radio telescope arrays implementing the FX (Fourier Transform-Cross Multiply) architecture. This correlator processes time-domain antenna signals to produce calibrated visibility measurements used in radio astronomy imaging.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
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

- Full FX pipeline: F-engine channelization and X-engine cross-correlation with geometric delay compensation
- Six configurable window functions (Hanning, Hamming, Blackman, Rectangular) and polyphase filterbank mode
- Multiple output formats: NumPy (.npy), HDF5 (.h5), and FITS (.fits)
- Docker-based deployment with development (simulation) and production (real data) operation modes

## Tech Stack

`Python · NumPy · SciPy · h5py · Astropy · PyYAML · Docker`

---

## Quick Start

### Using Docker (Recommended)

```bash
git clone https://github.com/yourusername/telescope-correlator.git
cd telescope-correlator

# Build the Docker image
correlator.bat build     # Windows
./correlator build       # Linux/Mac

# Start interactive development mode
correlator.bat dev       # Windows
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
   correlator.bat build   # Windows
   ./correlator build     # Linux/Mac
   ```

3. **Verify Installation**
   ```bash
   correlator.bat dev --help
   ```

### Native Python Installation

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

pip install -r requirements.txt
pip install -e app/src/

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

#### Command-Line Execution

```bash
# Basic simulation with default parameters
correlator.bat dev run

# Custom configuration
correlator.bat dev run --n-ants 8 --n-channels 512 --integration-time 2.0

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

#### Streaming from Network

```bash
correlator.bat prod stream --source tcp://10.0.0.1:7148
correlator.bat prod stream --source tcp://antenna-server:7148 --config workspace/configs/prod/default.yaml
```

#### Processing Recorded Data

```bash
correlator.bat prod process --input-file workspace/inputs/observation_20260124.npy
correlator.bat prod process --input-file data/obs.npy --config workspace/configs/prod/array64.yaml
```

### File-Based Processing

```bash
correlator.bat dev run --mode file --input-file workspace/inputs/simple_signal.npy
correlator.bat dev run --config workspace/configs/my_config.yaml
```

**Data Format Requirements:**
- NumPy array (.npy file)
- Shape: `(n_antennas, n_samples)`
- Dtype: `complex64` or `complex128`

## Configuration

### Example: Development Configuration

```yaml
operation_mode: development
data_source: simulated
n_ants: 8
ant_radius: 10.0
sample_rate: 1024.0
center_freq: 1420000000.0
n_channels: 256
window_type: hanning
quantize_bits: 0
overlap_factor: 0.0
integration_time: 1.0
sim_duration: 20.0
sim_snr: 20.0
enable_delays: true
phase_center: [1.0, 0.0, 0.0]
output_dir: workspace/outputs
output_format: npy
```

### Example: Production Configuration

```yaml
operation_mode: production
data_source: network_stream
stream_protocol: tcp
stream_address: telescope-server:7148
n_ants: 64
ant_radius: 100.0
sample_rate: 2048000.0
center_freq: 1420405751.77
n_channels: 4096
window_type: hanning
quantize_bits: 8
overlap_factor: 0.25
integration_time: 1.0
output_dir: workspace/outputs/prod
output_format: hdf5
enable_monitoring: true
log_level: INFO
```

### Configuration Parameters

#### Array Configuration
- `n_ants`: Number of antennas (≥ 2)
- `ant_positions`: Explicit antenna positions or null for circular array
- `ant_radius`: Radius for auto-generated circular array (meters)

#### F-Engine Parameters
- `n_channels`: Number of frequency channels (must be power of 2)
- `window_type`: `rectangular`, `hanning`, `hamming`, or `blackman`
- `quantize_bits`: Bit depth (0 = no quantization, 8/16 typical)
- `overlap_factor`: FFT window overlap (0.0 to 0.5)

#### X-Engine Parameters
- `integration_time`: Time integration period (seconds)

#### Output Parameters
- `output_format`: `npy`, `hdf5`, or `fits`
- `save_channelised`: Save intermediate F-engine output
- `max_integrations`: Maximum integrations (null = unlimited)

## Output Data

### File Naming Convention

```
workspace/outputs/
├── visibility_0001.npy
├── visibility_0002.npy
├── config.yaml
└── channelised.npy   (optional)
```

### Visibility Data Format

**Shape:** `(n_baselines, n_channels)`

| Antennas | Baselines |
|----------|-----------|
| 4        | 10        |
| 8        | 36        |
| 16       | 136       |
| 64       | 2080      |

**Baseline Ordering:** Autocorrelations first `(0,0), (1,1)...`, then cross-correlations `(0,1), (0,2)...`

**Data Type:** `complex128`

### Reading Output Data

```python
import numpy as np

vis = np.load('workspace/outputs/visibility_0001.npy')
print(f"Shape: {vis.shape}")  # (n_baselines, n_channels)

n_ants = 4
autocorr  = vis[:n_ants, :]   # Antenna powers
cross_corr = vis[n_ants:, :]  # Cross-correlations
```

### HDF5 Format

```python
import h5py

with h5py.File('workspace/outputs/visibility_0001.h5', 'r') as f:
    vis = f['visibilities'][:]
    print(dict(f.attrs))
```

### FITS Format

```python
from astropy.io import fits

with fits.open('workspace/outputs/visibility_0001.fits') as hdul:
    vis = hdul['REAL'].data + 1j * hdul['IMAG'].data
```

## Testing

```bash
# Run all tests (Docker)
correlator.bat test

# Native Python
pytest tests_harness/ -v

# Specific test suites
pytest tests_harness/unit/test_fengine.py -v
pytest tests_harness/unit/test_delay.py -v
python tests_harness/validate_accuracy.py all
```

## Examples

### Basic Simulation

```bash
correlator.bat dev run --n-ants 4 --sim-duration 10.0 --output-dir workspace/outputs/ex1
```

### Large Array Simulation

```bash
correlator.bat dev run \
  --n-ants 64 \
  --n-channels 4096 \
  --integration-time 2.0 \
  --sim-duration 60.0
```

### Custom Configuration

```yaml
# my_experiment.yaml
operation_mode: development
data_source: simulated
n_ants: 16
n_channels: 1024
integration_time: 5.0
sim_duration: 120.0
window_type: blackman
overlap_factor: 0.25
output_format: hdf5
```

```bash
correlator.bat dev run --config my_experiment.yaml
```

### HI Line Observation Simulation

```bash
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

### Docker container won't start

```bash
docker ps -a
docker rm telescope-correlator
correlator.bat build
```

### "n_channels must be a power of 2"

Valid values: 64, 128, 256, 512, 1024, 2048, 4096.

### Out of memory

```bash
--n-channels 256
--max-integrations 10
```

### File not found errors

Inside Docker, use the mounted workspace path:

```bash
--input-file /workspace/inputs/data.npy
--output-dir /workspace/outputs/
```

### Getting help

```bash
correlator.bat dev run --help
correlator.bat prod --help
```

## System Requirements

### Minimum
- CPU: 2 cores, 2.0 GHz
- RAM: 4 GB
- Disk: 5 GB

### Recommended for Production
- CPU: 8+ cores, 3.0+ GHz
- RAM: 16+ GB
- Disk: 100+ GB SSD

### Performance Guidelines

| Array Size | Channels | RAM Usage | Speed |
|------------|----------|-----------|-------|
| 4 ants     | 256      | ~500 MB   | Real-time |
| 8 ants     | 512      | ~1 GB     | Real-time |
| 16 ants    | 1024     | ~2 GB     | Near real-time |
| 64 ants    | 4096     | ~8 GB     | Batch preferred |

## Architecture Overview

For detailed information about signal processing algorithms and implementation, see [ARCHITECTURE.md](ARCHITECTURE.md).

## Contributing

Contributions are welcome. Ensure all tests pass (`correlator.bat test`), code follows existing style, and new features include tests.

## License

This project is part of academic research. Please cite appropriately if used in publications.

## Citation

```
Telescope Correlator - FX Architecture
[Author], [Institution], 2026
```

## Acknowledgments

Developed as part of research in radio astronomy signal processing and software-defined radio telescopes.

---

**Version:** 1.0.0 | **Last Updated:** January 2026 | [ARCHITECTURE.md](ARCHITECTURE.md)
