# Telescope Correlator

A complete radio telescope correlator implementation with FX architecture, fully containerized for easy deployment and testing.

## 🚀 Quick Start (Docker)

**For complete Docker usage instructions, see [DOCKER_README.md](DOCKER_README.md)**

```bash
# Pull the published image
docker pull ghcr.io/francois0203/telescope-correlator:latest

# Run the correlator
docker compose run --rm correlator python -m correlator --n-ants 4 --n-channels 128 --sim-duration 1.0 --output-dir /app/outputs

# Run tests
docker compose run --rm test
```

## 📋 Project Status

✅ **Fully Implemented & Containerized**
- Complete FX correlator with F-engine, X-engine, and delay compensation
- Comprehensive test suite (33 tests passing)
- Automated CI/CD with GitHub Actions
- Published Docker images on GHCR
- Cross-platform support (Linux AMD64/ARM64)

## 🏗️ Architecture

The correlator implements a complete FX architecture:

1. **Frontend**: Data ingestion with simulated or file-based sources
2. **F-Engine**: FFT-based channelization with configurable windowing
3. **Delay Engine**: Geometric delay compensation for antenna arrays
4. **X-Engine**: Cross-correlation with integration and accumulation

### Key Features

- **Multi-antenna correlation**: Supports N-antenna arrays with all baselines
- **Wideband processing**: Configurable frequency channels (32-1024+)
- **Real-time capable**: Optimized for streaming data processing
- **Signal validation**: Built-in SNR simulation and signal quality metrics

## 📊 Usage Examples

```bash
# Basic 4-antenna correlator
docker compose run --rm correlator python -m correlator --n-ants 4 --n-channels 128 --sim-duration 1.0

# High-resolution observation
docker compose run --rm correlator python -m correlator --n-ants 8 --n-channels 512 --sim-duration 2.0

# Development shell
docker compose run --rm dev
```

## 📁 Project Structure

```
telescope-correlator/
├── app/src/                   # Core correlator implementation
├── tests_harness/            # Complete test suite
├── dev_workspace/outputs/    # Generated results (gitignored)
├── docker-compose.yml        # Docker services configuration
├── docker-run.sh/.bat        # Cross-platform management scripts
├── DOCKER_README.md          # Complete Docker usage guide
└── visualize_*.py           # Result visualization tools
```

## 🔧 Development

- **Language**: Python 3.11 with scientific computing stack
- **Testing**: pytest with 33 comprehensive tests
- **Containerization**: Multi-stage Docker builds
- **CI/CD**: GitHub Actions with automated publishing
- **Registry**: GitHub Container Registry (ghcr.io)

## 📖 Documentation

- **[DOCKER_README.md](DOCKER_README.md)** - Complete Docker usage guide
- **[USAGE_GUIDE.md](USAGE_GUIDE.md)** - Detailed correlator usage and parameters
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Technical architecture documentation

## 🤝 Contributing

See [DOCKER_README.md](DOCKER_README.md) for contribution guidelines. Images are automatically built and published via CI/CD when changes are pushed to `main`.
