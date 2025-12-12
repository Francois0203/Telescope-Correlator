# Telescope Correlator - Quick Reference

## Installation

1. Install Docker Desktop: https://www.docker.com/products/docker-desktop
2. Clone this repository
3. Run `correlator` (Windows) or `./correlator` (Linux/Mac)

## Basic Usage

```cmd
correlator                     # Start interactive CLI
correlator build               # Build Docker image
correlator run [OPTIONS]       # Run with parameters
correlator test                # Run tests
```

## Interactive CLI

After running `correlator`:

```
run                            # Execute correlator
run --n-ants 8 --sim-duration 2.0  # With parameters
set n_ants 8                   # Change settings
config                         # View settings
list                           # List outputs
visualize                      # Create plots
help                           # Show commands
exit                           # Exit
```

## Examples

```cmd
# Basic runs
correlator run --n-ants 4 --n-channels 64
correlator run --n-ants 8 --n-channels 512 --sim-duration 2.0
correlator run --sim-snr 5 --sim-duration 1.0

# Inside interactive CLI
correlator> set n_ants 6
correlator> set sim_duration 3.0
correlator> run
correlator> list
correlator> visualize
```

## Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--n-ants` | 4 | Number of antennas |
| `--n-channels` | 256 | Frequency channels |
| `--sim-duration` | 10.0 | Simulation time (sec) |
| `--sim-snr` | 20.0 | Signal-to-noise (dB) |
| `--sample-rate` | 1024.0 | Sample rate (Hz) |

## Output

All results in `dev_workspace/outputs/`:
- `visibility_*.npy` - Correlation data
- `config.yaml` - Configuration
- `*_visualization.png` - Plots

## Troubleshooting

- **Docker not installed**: Get from docker.com
- **Image not found**: Run `correlator build`
- **CLI won't start**: Start Docker Desktop
- **Permission denied** (Linux/Mac): Run `chmod +x correlator`
