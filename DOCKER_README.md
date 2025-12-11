# Telescope Correlator - Docker Setup

This repository contains a radio telescope correlator implemented in Python, now fully containerized with Docker for easy deployment and testing.

## 🐳 Docker Setup

The application is fully containerized with Docker. The correlator app runs inside Docker containers, while outputs are stored outside the containers for persistence.

### Prerequisites

- Docker and Docker Compose installed
- At least 2GB free disk space for Docker images

### Quick Start

1. **Build the Docker images:**
   ```bash
   docker-compose build
   ```

2. **Run the test suite:**
   ```bash
   docker-compose run --rm test
   ```

3. **Run the correlator:**
   ```bash
   docker-compose run --rm correlator python -m correlator --n-ants 4 --n-channels 128 --sim-duration 1.0 --output-dir /app/outputs
   ```

4. **Start a development shell:**
   ```bash
   docker-compose run --rm dev
   ```

## 📁 Project Structure

```
telescope-correlator/
├── app/
│   ├── Dockerfile              # Multi-stage Docker build
│   └── src/                    # Source code
│       ├── correlator/         # Main package
│       └── setup.py           # Package setup
├── tests_harness/             # Test suite
├── dev_workspace/             # Development workspace
│   └── outputs/               # Output files (mounted volume)
├── docker-compose.yml         # Docker services configuration
├── docker-run.sh             # Management script (Linux/Mac)
├── requirements.txt           # Python dependencies
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

## 🔧 Development

### Development Shell

```bash
# Start interactive development environment
docker-compose run --rm dev

# Inside the container, you can:
# - Run tests: pytest tests_harness/
# - Run correlator: python -m correlator [options]
# - Modify code and test changes
```

### Building Custom Images

```bash
# Rebuild after code changes
docker-compose build --no-cache

# Build specific service
docker-compose build correlator
```

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

2. **Docker build fails**
   ```bash
   # Clear Docker cache and rebuild
   docker system prune -f
   docker-compose build --no-cache
   ```

3. **Tests fail**
   ```bash
   # Check Docker is running and has sufficient resources
   docker system df
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

1. Make changes in the development environment
2. Run tests: `docker-compose run --rm test`
3. Verify correlator works: `docker-compose run --rm correlator [options]`
4. Commit changes

## 📄 License

This project is part of the Telescope Correlator implementation for radio astronomy signal processing.