# Telescope Correlator - Interactive CLI Guide

## 🚀 Quick Start with Interactive CLI

The Telescope Correlator now includes a persistent interactive CLI that runs as a Docker container, giving you a virtual environment-like experience.

### Starting the Interactive CLI

```bash
# Windows
.\docker-run.bat cli

# Linux/macOS
./docker-run.sh cli

# Or directly with Docker Compose
docker compose up cli
```

This starts a persistent container with an interactive shell where you can run correlator commands repeatedly without restarting the container.

## 📟 Interactive CLI Commands

Once inside the CLI shell, you have access to these commands:

### `run` - Execute Correlator

Run the correlator with various parameters:

```bash
# Basic run with defaults
correlator> run

# Custom configuration
correlator> run --n-ants 4 --n-channels 256 --sim-duration 2.0

# High-resolution observation
correlator> run --n-ants 8 --n-channels 512 --sim-duration 1.0

# Quick test run
correlator> run --n-ants 4 --n-channels 64 --sim-duration 0.5
```

**Available options:**
- `--n-ants N` - Number of antennas (default: 4)
- `--n-channels N` - Number of frequency channels (default: 128)
- `--sim-duration SEC` - Simulation duration in seconds (default: 1.0)
- `--output-dir PATH` - Output directory (default: /app/outputs)
- `--mode MODE` - Data source mode: simulated or file (default: simulated)

### `config` - Configuration Management

View or modify settings:

```bash
# Show current configuration
correlator> config

# Set individual values
correlator> config set n_ants 8
correlator> config set n_channels 256
correlator> config set sim_duration 2.0
```

### `status` - System Status

Check system information and last run status:

```bash
correlator> status
```

Shows:
- CLI version
- Python version
- Working directory
- Last run status
- Output files count

### `clear` - Clear Screen

Clear the terminal screen:

```bash
correlator> clear
```

### `help` - Show Available Commands

Display help information:

```bash
correlator> help
correlator> help run
correlator> help config
```

### `exit` / `quit` - Exit CLI

Exit the interactive shell:

```bash
correlator> exit
# or
correlator> quit
# or press Ctrl+D
```

## 🐳 Docker Services Overview

The correlator now provides multiple Docker services:

### 1. **`cli`** - Interactive CLI (Persistent)
```bash
docker compose up cli
```
- Runs continuously with interactive shell
- Best for: Repeated runs, experimentation, learning
- Features: Full CLI commands, configuration management, status monitoring

### 2. **`correlator`** - One-Shot Execution
```bash
docker compose run --rm correlator python -m correlator --n-ants 4 --n-channels 128
```
- Runs once and exits
- Best for: Single batch processing, CI/CD pipelines
- Features: Direct Python invocation

### 3. **`test`** - Test Suite
```bash
docker compose run --rm test
```
- Runs all 33 tests
- Best for: Validation, CI/CD verification
- Features: pytest integration

### 4. **`dev`** - Development Shell
```bash
docker compose run --rm dev
```
- Bash shell with full workspace access
- Best for: Development, debugging, file exploration
- Features: Full Linux shell access

## 📁 New Project Structure

The codebase has been restructured for modularity and clarity:

```
app/src/correlator/
├── core/                    # Core processing modules
│   ├── __init__.py
│   ├── delay.py            # Delay compensation
│   ├── fengine.py          # F-Engine (channelizer)
│   ├── frontend.py         # Data ingestion
│   └── xengine.py          # X-Engine (correlator)
├── cli/                     # CLI interface
│   ├── __init__.py
│   ├── commands.py         # Command-line argument parsing
│   ├── interactive.py      # Interactive shell
│   └── runner.py           # Correlator execution
├── utils/                   # Utility functions
│   └── __init__.py
├── config.py               # Configuration management
├── __init__.py             # Package initialization
└── __main__.py             # Entry point
```

## 🔄 Typical Workflow

### 1. **Start the CLI**
```bash
.\docker-run.bat cli
```

### 2. **Check Status**
```bash
correlator> status
```

### 3. **Configure Settings (Optional)**
```bash
correlator> config set n_ants 8
correlator> config set n_channels 512
```

### 4. **Run Correlator**
```bash
correlator> run --sim-duration 2.0
```

### 5. **Check Output**
```bash
correlator> status
```

### 6. **Run Again with Different Parameters**
```bash
correlator> run --n-ants 4 --n-channels 256 --sim-duration 1.0
```

### 7. **Exit When Done**
```bash
correlator> exit
```

## 🎯 Management Scripts Reference

### Windows (PowerShell)

```batch
# Start interactive CLI
.\docker-run.bat cli

# One-shot correlator run
.\docker-run.bat run --n-ants 4 --n-channels 128

# Pull and run latest published image
.\docker-run.bat pull-run --n-ants 4 --n-channels 64

# Run tests
.\docker-run.bat test

# Development shell
.\docker-run.bat dev

# Build image
.\docker-run.bat build

# Clean up
.\docker-run.bat clean
```

### Linux/macOS (Bash)

```bash
# Start interactive CLI
./docker-run.sh cli

# One-shot correlator run
./docker-run.sh run --n-ants 4 --n-channels 128

# Pull and run latest published image
./docker-run.sh pull-run --n-ants 4 --n-channels 64

# Run tests
./docker-run.sh test

# Development shell
./docker-run.sh dev

# Build image
./docker-run.sh build

# Clean up
./docker-run.sh clean
```

## 💡 Tips & Best Practices

### 1. **Use CLI for Interactive Work**
The interactive CLI is perfect for:
- Experimenting with different parameters
- Running multiple correlations in a session
- Learning how the correlator works

### 2. **Use One-Shot for Automation**
For scripts and automation:
```bash
docker compose run --rm correlator python -m correlator --n-ants 4 --n-channels 256
```

### 3. **Check Output Files**
Outputs are automatically saved to `dev_workspace/outputs/`:
```
dev_workspace/outputs/
├── visibility_0001.npy
├── visibility_0002.npy
├── visibility_0003.npy
├── visibility_0004.npy
└── config.yaml
```

### 4. **Monitor Container in Docker Desktop**
When running the CLI service, you'll see:
- Container name: `telescope-correlator-cli`
- Status: Running (persistent until stopped)
- Logs: Full CLI interaction history

### 5. **Stop the CLI Container**
```bash
docker compose down cli
# or
docker stop telescope-correlator-cli
```

## 🔍 Viewing Logs

```bash
# View CLI logs
docker compose logs cli

# Follow logs in real-time
docker compose logs -f cli

# View last 50 lines
docker compose logs --tail=50 cli
```

## 🚀 Advanced Usage

### Using Both CLI and Dev Shell

You can run multiple services simultaneously:

```bash
# Terminal 1: Interactive CLI
.\docker-run.bat cli

# Terminal 2: Development shell for file inspection
.\docker-run.bat dev
```

### Custom Configuration File

```bash
# One-shot run with config file
docker compose run --rm correlator python -m correlator --config my_config.yaml

# Or use interactive mode from command line
docker compose run --rm correlator python -m correlator --interactive
```

## 📊 Example Session

```
C:\Projects\Telescope-Correlator> .\docker-run.bat cli

╔══════════════════════════════════════════════════════════════╗
║         Telescope Correlator - Interactive CLI              ║
║                    FX Architecture                           ║
╚══════════════════════════════════════════════════════════════╝

Type 'help' or '?' to list commands.
Type 'exit' or 'quit' to exit the shell.

correlator> status

============================================================
SYSTEM STATUS
============================================================
CLI Version:       1.0.0
Python:            3.11.14
Working Directory: /app
Last Run Status:   ✗ Not run or failed
Output Directory:  /app/outputs
Output Files:      0 visibility files, 0 config files
============================================================

correlator> run --n-ants 4 --n-channels 64 --sim-duration 0.5

============================================================
STARTING CORRELATOR RUN
============================================================

Initializing FX correlator with 4 antennas, 64 channels
Creating simulated stream: 0.5s @ 1024.0 Hz
  Sources: [0.0, 0.5235987755982988] rad
  SNR: 20.0 dB
  Total samples: 512, chunks: 1
Delay compensation enabled
Integration time: 1.0s (16 spectra)

Processing...
  Saved integration 1 -> visibility_0001.npy
  Saved integration 2 -> visibility_0002.npy
  Saved integration 3 -> visibility_0003.npy
  Saved integration 4 -> visibility_0004.npy
Saved configuration: /app/outputs/config.yaml

Complete: 4 integrations written to /app/outputs/

============================================================
✓ CORRELATOR RUN COMPLETED SUCCESSFULLY
============================================================

correlator> status

============================================================
SYSTEM STATUS
============================================================
CLI Version:       1.0.0
Python:            3.11.14
Working Directory: /app
Last Run Status:   ✓ Success
Output Directory:  /app/outputs
Output Files:      4 visibility files, 1 config files
============================================================

correlator> exit

Exiting Telescope Correlator CLI. Goodbye!
```

## 🛠️ Troubleshooting

### CLI Won't Start
```bash
# Stop any running CLI containers
docker compose down cli

# Restart
.\docker-run.bat cli
```

### Output Files Not Appearing
Check the volume mount in `docker-compose.yml`:
```yaml
volumes:
  - ./dev_workspace/outputs:/app/outputs
```

### Permission Issues
```bash
# Ensure output directory exists
mkdir -p dev_workspace/outputs
```

### Container Won't Stop
```bash
# Force stop
docker stop telescope-correlator-cli

# Or remove
docker rm -f telescope-correlator-cli
```

## 📚 Additional Resources

- **DOCKER_README.md** - Complete Docker usage guide
- **README.md** - Project overview
- **USAGE_GUIDE.md** - Detailed correlator usage
- **ARCHITECTURE.md** - Technical architecture

---

**Happy correlating! 🛰️📡**
