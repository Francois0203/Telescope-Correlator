# Telescope Correlator - Docker Usage Guide

This repository contains a radio telescope correlator implemented in Python, fully containerized with Docker for easy deployment and testing. **This guide focuses on using the published Docker images.**

> **💡 New!** The correlator now includes an **interactive CLI shell** for persistent container operation. See [CLI_GUIDE.md](CLI_GUIDE.md) for details.

## 🐳 Docker Setup

The application runs entirely in Docker containers using pre-built images published to GitHub Container Registry (GHCR). No local building required!

### Prerequisites

- Docker and Docker Compose installed
- Internet connection to pull images from GHCR
- At least 2GB free disk space for Docker images

### Quick Start

#### Option 1: Interactive CLI (Recommended)

Start a persistent interactive correlator shell:

```bash
# Windows
.\docker-run.bat cli

# Linux/macOS
./docker-run.sh cli

# Or directly
docker compose up cli
```

This starts a container that runs continuously with an interactive CLI. See [CLI_GUIDE.md](CLI_GUIDE.md) for full documentation.

#### Option 2: One-Shot Execution

For single batch runs:

1. **Pull the published Docker image:**
   ```bash
   docker pull ghcr.io/francois0203/telescope-correlator:latest
   ```

2. **Run the test suite:**
   ```bash
   docker compose run --rm test
   ```

3. **Run the correlator:**
   ```bash
   docker compose run --rm correlator python -m correlator --n-ants 4 --n-channels 128 --sim-duration 1.0 --output-dir /app/outputs
   ```

4. **Start a development shell:**
   ```bash
   docker compose run --rm dev
   ```

### Automated CI/CD Verification

When you push to the `main` branch, the CI/CD pipeline automatically:

- ✅ Builds and publishes the Docker image to GHCR
- ✅ Runs comprehensive tests with the published image
- ✅ Executes the correlator and verifies output generation
- ✅ Provides attestation for build provenance

**View containers in GitHub Actions:** Check the "Verify published image" step in your CI/CD runs to see containers executing in real-time!

### Alternative: Direct Docker Commands

If you prefer not to use Docker Compose:

```bash
# Run correlator directly
docker run --rm -v ${PWD}/dev_workspace/outputs:/app/outputs ghcr.io/francois0203/telescope-correlator:latest python -m correlator --n-ants 4 --n-channels 64 --sim-duration 0.5 --output-dir /app/outputs

# Run tests directly
docker run --rm -v ${PWD}:/workspace -v ${PWD}/dev_workspace/outputs:/app/outputs ghcr.io/francois0203/telescope-correlator:latest pytest tests_harness/ -v
```

## 📁 Project Structure

```
telescope-correlator/
├── app/
│   └── src/                    # Source code (for reference only)
│       ├── correlator/         # Main package
│       └── setup.py           # Package setup
├── tests_harness/             # Test suite (mounted for testing)
├── dev_workspace/             # Development workspace
│   └── outputs/               # Output files (mounted volume)
├── docker-compose.yml         # Docker services using published images
├── docker-run.sh             # Management script (Linux/Mac)
├── docker-run.bat            # Management script (Windows)
├── requirements.txt           # Python dependencies (for reference)
└── visualize_*.py            # Visualization scripts
```
└── visualize_*.py            # Visualization scripts
```

## 🧪 Testing

All tests pass in the Docker environment:

```bash
# Run all tests
docker-compose run --rm test

# Expected output: 33 passed
```

Test coverage includes:
- Unit tests for all components (F-engine, X-engine, Delay engine, Frontend)
- Integration tests for the complete FX pipeline
- Validation of signal processing algorithms

## 🚀 Running the Correlator

### Basic Usage

```bash
# Run with default simulated data
docker-compose run --rm correlator python -m correlator --n-ants 4 --n-channels 128 --sim-duration 1.0 --output-dir /app/outputs
```

### Available Options

- `--n-ants`: Number of antennas (default: 4)
- `--n-channels`: Number of frequency channels (default: 128)
- `--sim-duration`: Simulation duration in seconds (default: 1.0)
- `--output-dir`: Output directory inside container (default: /app/outputs)
- `--mode`: Data source mode - `simulated` or `file` (default: simulated)

### Output Files

All outputs are saved to `dev_workspace/outputs/` on the host machine:
- `visibility_*.npy`: Visibility data files
- `config.yaml`: Configuration used for the run
- Visualization PNG files (when using visualization scripts)

## 📊 Visualization

After running the correlator, visualize the results:

```bash
# Simple visualization (no correlator dependencies)
python visualize_simple.py dev_workspace/outputs/visibility_0001.npy

# Full visualization (requires correlator modules)
python visualize_correlator.py dev_workspace/outputs/visibility_0001.npy
```

## 🛠️ Management Scripts

Cross-platform scripts are provided for easy Docker management:

### Windows (PowerShell)
```batch
# Run correlator
.\docker-run.bat run --n-ants 4 --n-channels 128 --sim-duration 1.0

# Pull latest published image and run
.\docker-run.bat pull-run --n-ants 4 --n-channels 64 --sim-duration 0.5

# Run tests
.\docker-run.bat test

# Development shell
.\docker-run.bat dev

# Clean up
.\docker-run.bat clean
```

### Linux/macOS (Bash)
```bash
# Run correlator
./docker-run.sh run --n-ants 4 --n-channels 128 --sim-duration 1.0

# Pull latest published image and run
./docker-run.sh pull-run --n-ants 4 --n-channels 64 --sim-duration 0.5

# Run tests
./docker-run.sh test

# Development shell
./docker-run.sh dev

# Clean up
./docker-run.sh clean
```

## 🔧 Development & CI/CD

### Automated Image Publishing

Docker images are automatically built and published via GitHub Actions CI/CD:

- **Trigger**: Push to `main` branch
- **Registry**: GitHub Container Registry (`ghcr.io`)
- **Image**: `ghcr.io/francois0203/telescope-correlator:latest`
- **Platforms**: Linux AMD64 + ARM64

### Development Shell

```bash
# Start interactive development environment with published image
docker compose run --rm dev

# Inside the container, you can:
# - Run tests: pytest tests_harness/
# - Run correlator: python -m correlator [options]
# - Explore the containerized environment
```

### Local Development (For Contributors)

If you need to modify the code and build custom images:

1. **Clone the repository**
2. **Modify source code** in `app/src/`
3. **Build locally** (not recommended for regular use):
   ```bash
   docker compose build
   ```
4. **Test changes**:
   ```bash
   docker compose run --rm test
   ```
5. **Push changes** to trigger automated image publishing

## 🏗️ Architecture

The correlator implements an FX architecture:

1. **Frontend (F)**: Data ingestion and channelization
2. **F-Engine**: FFT-based channelization with windowing
3. **Delay Engine**: Geometric delay compensation
4. **X-Engine**: Cross-correlation and integration

### Docker Architecture

- **Multi-stage build**: Optimized for both development and production
- **Volume mounting**: Outputs persist outside containers
- **Separate services**: Test, development, and production environments
- **Python 3.11**: Modern Python with scientific computing stack

## 📋 Troubleshooting

### Common Issues

1. **Permission denied on outputs**
   ```bash
   # Ensure output directory exists and is writable
   mkdir -p dev_workspace/outputs
   ```

2. **Image pull fails**
   ```bash
   # Check Docker is running and you have internet access
   docker pull ghcr.io/francois0203/telescope-correlator:latest
   ```

3. **Tests fail**
   ```bash
   # Check Docker has sufficient resources
   docker system df

   # Try running tests directly
   docker run --rm -v ${PWD}:/workspace ghcr.io/francois0203/telescope-correlator:latest pytest tests_harness/ -v
   ```

4. **Container exits immediately**
   ```bash
   # Check the command syntax
   docker compose run --rm correlator python -m correlator --help
   ```

### Logs and Debugging

```bash
# View container logs
docker-compose logs

# Run with verbose output
docker-compose run --rm correlator python -m correlator --help
```

## 📈 Performance

- **Test execution**: ~2 seconds for 33 tests
- **Correlation time**: ~1 second for 4 antennas, 128 channels, 1 second simulation
- **Memory usage**: ~50MB per container
- **Output size**: ~20KB per visibility file

## 🤝 Contributing

1. **For Code Changes:**
   - Modify source code in `app/src/`
   - Test locally if needed: `docker compose run --rm test`
   - Push changes to `main` branch
   - CI/CD automatically builds and publishes new images

2. **For Docker/Deployment Changes:**
   - Modify `docker-compose.yml` or CI/CD workflow
   - Test changes locally
   - Push to `main` to deploy updates

3. **Testing Your Changes:**
   ```bash
   # Test with published image (recommended)
   docker compose run --rm test
   docker compose run --rm correlator python -m correlator --n-ants 4 --n-channels 64 --sim-duration 0.5 --output-dir /app/outputs

   # Or test with local build (for development)
   docker compose build
   docker compose run --rm test
   ```

## 📄 License

This project is part of the Telescope Correlator implementation for radio astronomy signal processing.