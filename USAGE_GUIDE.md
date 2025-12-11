# Telescope Correlator - Complete Docker Usage Guide

## 🚀 Quick Start

Your Telescope Correlator is now fully containerized! Here's how to use it:

### Prerequisites
- Docker and Docker Compose installed
- GitHub repository access (for CI/CD)

---

## 🏗️ Local Development

### 1. Clone and Setup
```bash
git clone https://github.com/Francois0203/Telescope-Correlator.git
cd Telescope-Correlator
```

### 2. Build the Docker Image
```bash
# Windows
.\docker-run.bat build

# Linux/Mac
./docker-run.sh build
```

### 3. Run Tests
```bash
# Windows
.\docker-run.bat test

# Linux/Mac
./docker-run.sh test
```

**Expected Output:**
```
================================================== 33 passed in 2.07s ==================================================
[SUCCESS] Tests completed
```

### 4. Run the Correlator
```bash
# Basic run with 4 antennas
.\docker-run.bat run --n-ants 4 --n-channels 128 --sim-duration 1.0 --output-dir /app/outputs

# Advanced run with custom parameters
.\docker-run.bat run --n-ants 8 --n-channels 256 --sim-duration 2.0 --sim-snr 30.0 --output-dir /app/outputs
```

### 5. Check Results
```bash
# View generated files
dir dev_workspace\outputs\

# Visualize results
python visualize_simple.py dev_workspace\outputs\visibility_0001.npy
```

---

## 🐳 Docker Compose Usage

### Direct Docker Compose Commands
```bash
# Build all services
docker-compose build

# Run tests
docker-compose run --rm test

# Run correlator
docker-compose run --rm correlator python -m correlator --n-ants 4 --n-channels 128 --sim-duration 1.0 --output-dir /app/outputs

# Development shell
docker-compose run --rm dev
```

### Available Services
- **`correlator`**: Main application container
- **`test`**: Runs the test suite
- **`dev`**: Interactive development environment

---

## 🔄 CI/CD Pipeline

### Automatic Testing on GitHub

Every push to `main` branch automatically:
1. ✅ Builds Docker image
2. ✅ Runs all 33 tests inside Docker
3. ✅ Tests correlator functionality end-to-end
4. ✅ Publishes image to GitHub Container Registry (GHCR)

### Pipeline Status
Check your repository's **Actions** tab to see pipeline status.

### Using Published Images

Once published, you can pull and run the image directly:

```bash
# Pull from GitHub Container Registry
docker pull ghcr.io/francois0203/telescope-correlator:latest

# Run the correlator
docker run --rm \
  -v $(pwd)/outputs:/app/outputs \
  ghcr.io/francois0203/telescope-correlator:latest \
  python -m correlator --n-ants 4 --n-channels 128 --sim-duration 1.0 --output-dir /app/outputs
```

---

## 📊 Working with Outputs

### Output Location
- **Local development**: `dev_workspace/outputs/`
- **Docker containers**: `/app/outputs/` (mapped to host)

### Generated Files
```
dev_workspace/outputs/
├── visibility_0001.npy      # Correlation results
├── visibility_0002.npy      # Additional integrations
├── config.yaml             # Run configuration
└── *.png                   # Visualization files
```

### Data Analysis
```bash
# Quick data summary
python visualize_simple.py dev_workspace/outputs/visibility_0001.npy --summary-only

# Full visualization
python visualize_simple.py dev_workspace/outputs/visibility_0001.npy

# Custom analysis
python -c "
import numpy as np
vis = np.load('dev_workspace/outputs/visibility_0001.npy')
print(f'Shape: {vis.shape}')
print(f'Amplitude range: {np.abs(vis).min():.2f} - {np.abs(vis).max():.2f}')
"
```

---

## 🛠️ Development Workflow

### 1. Make Changes
Edit files in your local repository.

### 2. Test Locally
```bash
# Run tests
.\docker-run.bat test

# Test specific functionality
.\docker-run.bat run --n-ants 4 --n-channels 64 --sim-duration 0.5 --output-dir /app/outputs
```

### 3. Commit and Push
```bash
git add .
git commit -m "Your changes"
git push origin main
```

### 4. CI/CD Takes Over
- GitHub Actions automatically builds and tests
- If tests pass, image is published to GHCR
- Check Actions tab for results

---

## 🔧 Troubleshooting

### Build Issues
```bash
# Clear Docker cache
docker system prune -f
.\docker-run.bat build
```

### Test Failures
```bash
# Run tests with more verbose output
docker-compose run --rm test pytest tests_harness/ -v -s
```

### Permission Issues
```bash
# Ensure output directory exists
mkdir -p dev_workspace/outputs
```

### Container Won't Start
```bash
# Check Docker is running
docker info

# Clean up old containers
docker-compose down -v
```

---

## 📈 Advanced Usage

### Custom Configuration
```bash
# Create custom config
cat > my_config.yaml << EOF
n_ants: 6
n_channels: 512
sim_duration: 5.0
sim_snr: 25.0
EOF

# Run with config
docker-compose run --rm correlator python -m correlator --config my_config.yaml --output-dir /app/outputs
```

### Batch Processing
```bash
# Run multiple configurations
for ants in 4 6 8; do
  echo "Testing with $ants antennas..."
  .\docker-run.bat run --n-ants $ants --n-channels 128 --sim-duration 1.0 --output-dir /app/outputs
done
```

### Performance Testing
```bash
# Time the correlator
time .\docker-run.bat run --n-ants 16 --n-channels 1024 --sim-duration 10.0 --output-dir /app/outputs
```

---

## 🌐 Deployment Options

### 1. Local Deployment
- Use the Docker setup as shown above
- Outputs saved to local filesystem

### 2. Cloud Deployment
```bash
# Example: Run on cloud VM
docker run --rm \
  -v /data/outputs:/app/outputs \
  ghcr.io/francois0203/telescope-correlator:latest \
  python -m correlator --n-ants 8 --n-channels 256 --sim-duration 60.0 --output-dir /app/outputs
```

### 3. Kubernetes
```yaml
# k8s deployment example
apiVersion: apps/v1
kind: Job
metadata:
  name: telescope-correlator-job
spec:
  template:
    spec:
      containers:
      - name: correlator
        image: ghcr.io/francois0203/telescope-correlator:latest
        command: ["python", "-m", "correlator", "--n-ants", "4", "--output-dir", "/app/outputs"]
        volumeMounts:
        - name: output-volume
          mountPath: /app/outputs
      volumes:
      - name: output-volume
        persistentVolumeClaim:
          claimName: correlator-output-pvc
      restartPolicy: Never
```

---

## 📚 Key Concepts

### FX Correlator Architecture
- **F-Engine**: Channelization (FFT-based)
- **X-Engine**: Cross-correlation
- **Delay Engine**: Geometric delay compensation

### Data Flow
1. **Input**: Simulated or real antenna signals
2. **Processing**: F-engine → Delay engine → X-engine
3. **Output**: Visibility data (complex correlations)

### Visibility Data
- **Shape**: `(n_baselines, n_channels)`
- **Type**: Complex float (real + imaginary)
- **Baselines**: Auto-correlations + cross-correlations

---

## 🎯 Success Checklist

- [x] Docker image builds successfully
- [x] All 33 tests pass
- [x] Correlator generates valid outputs
- [x] CI/CD pipeline works
- [x] Images published to GHCR
- [x] Outputs persist outside containers
- [x] Cross-platform compatibility (Linux/Windows/Mac)

Your Telescope Correlator is production-ready! 🚀