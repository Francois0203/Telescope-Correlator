# Telescope Correlator

A radio telescope correlator implementing the FX architecture for array signal processing.

## Quick Start

**Windows:**
```cmd
correlator
```

**Linux/Mac:**
```bash
chmod +x correlator
./correlator
```

This automatically builds and starts the interactive CLI.

## Commands

```cmd
correlator                     # Start interactive CLI (default)
correlator build               # Build Docker image
correlator run [OPTIONS]       # Run with parameters
correlator test                # Run test suite
correlator help                # Show help
```

## Interactive CLI Commands

Inside the CLI (`correlator`):

```
run                           # Execute correlator
run --n-ants 8 --sim-duration 2.0  # Run with custom parameters
set n_ants 8                  # Change number of antennas
set n_channels 256            # Change frequency channels
set sim_duration 2.0          # Change simulation time
config                        # View all settings
list                          # List output files
list *.npy                    # List specific files
visualize                     # Create plots from latest output
visualize visibility_0001     # Visualize specific file
help                          # Show all commands
exit                          # Exit CLI
```

## Common Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `--n-ants` | Number of antennas | 4 |
| `--n-channels` | Frequency channels | 256 |
| `--sim-duration` | Simulation time (seconds) | 10.0 |
| `--sim-snr` | Signal-to-noise ratio (dB) | 20.0 |
| `--sample-rate` | Sample rate (Hz) | 1024.0 |
| `--output-dir` | Output directory | /app/outputs |

## Quick Examples

```cmd
# Start interactive CLI
correlator

# Direct run with parameters
correlator run --n-ants 4 --n-channels 64
correlator run --n-ants 8 --n-channels 512 --sim-duration 2.0

# Run tests
correlator test
```

## Output Files

Results in `dev_workspace/outputs/`:
- `visibility_*.npy` - Correlation data
- `config.yaml` - Configuration
- `*_visualization.png` - Plots

## Requirements

- Docker Desktop (Windows/Mac) or Docker Engine (Linux)
- 2GB+ disk space
- No Python installation needed

## Architecture

**FX Correlator Pipeline:**
1. Frontend → Data ingestion
2. F-Engine → FFT channelization
3. Delay Engine → Geometric compensation
4. X-Engine → Cross-correlation

**Features:**
- Multi-antenna arrays (2-32+ antennas)
- Configurable channels (32-1024+)
- Built-in visualization
- Real-time processing

See [QUICKSTART.md](QUICKSTART.md) for more examples.
