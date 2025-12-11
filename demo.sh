#!/bin/bash
# Complete Telescope Correlator Docker Workflow Demo

set -e

echo "🚀 Telescope Correlator - Complete Docker Workflow Demo"
echo "======================================================"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is available
check_docker() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first."
        exit 1
    fi

    if ! docker info &> /dev/null; then
        log_error "Docker is not running. Please start Docker."
        exit 1
    fi

    log_success "Docker is available and running"
}

# Clean up any existing containers/images
cleanup() {
    log_info "Cleaning up previous runs..."
    docker-compose down -v --rmi local 2>/dev/null || true
    docker system prune -f >/dev/null 2>&1 || true
    rm -rf demo-outputs test-outputs
    mkdir -p demo-outputs
}

# Build the Docker image
build_image() {
    log_info "Building Docker image..."
    docker-compose build
    log_success "Docker image built successfully"
}

# Run the test suite
run_tests() {
    log_info "Running test suite..."
    docker-compose run --rm test
    log_success "All tests passed!"
}

# Test correlator functionality
test_correlator() {
    log_info "Testing correlator functionality..."

    # Run correlator with different configurations
    log_info "Running correlator with 4 antennas..."
    docker-compose run --rm correlator python -m correlator \
        --n-ants 4 --n-channels 128 --sim-duration 1.0 --output-dir /app/outputs

    log_info "Running correlator with 6 antennas..."
    docker-compose run --rm correlator python -m correlator \
        --n-ants 6 --n-channels 64 --sim-duration 0.5 --output-dir /app/outputs

    log_success "Correlator tests completed successfully"
}

# Verify outputs
verify_outputs() {
    log_info "Verifying outputs..."

    if [ ! -d "demo-outputs" ]; then
        log_error "Output directory not found"
        return 1
    fi

    local file_count=$(ls demo-outputs/*.npy 2>/dev/null | wc -l)
    if [ "$file_count" -eq 0 ]; then
        log_error "No visibility files found"
        return 1
    fi

    log_success "Found $file_count visibility files"

    # Show file details
    echo "Generated files:"
    ls -la demo-outputs/

    # Quick data validation
    if command -v python3 &> /dev/null; then
        log_info "Running data validation..."
        python3 -c "
import numpy as np
import os
files = [f for f in os.listdir('demo-outputs') if f.endswith('.npy')]
for f in files:
    data = np.load(f'demo-outputs/{f}')
    print(f'{f}: shape={data.shape}, dtype={data.dtype}, range={np.abs(data).min():.2f}-{np.abs(data).max():.2f}')
        "
    fi
}

# Show usage examples
show_usage() {
    echo ""
    echo "📚 Usage Examples:"
    echo "=================="
    echo ""
    echo "# Build and test"
    echo "./docker-run.sh build"
    echo "./docker-run.sh test"
    echo ""
    echo "# Run correlator"
    echo "./docker-run.sh run --n-ants 4 --n-channels 128 --sim-duration 1.0 --output-dir /app/outputs"
    echo ""
    echo "# Development shell"
    echo "./docker-run.sh dev"
    echo ""
    echo "# Direct Docker commands"
    echo "docker-compose build"
    echo "docker-compose run --rm test"
    echo "docker-compose run --rm correlator python -m correlator --help"
    echo ""
    echo "# Pull from GitHub Container Registry"
    echo "docker pull ghcr.io/francois0203/telescope-correlator:latest"
    echo "docker run --rm ghcr.io/francois0203/telescope-correlator:latest python -m correlator --n-ants 4 --output-dir /app/outputs"
}

# Main demo flow
main() {
    echo ""
    check_docker
    cleanup
    build_image
    run_tests
    test_correlator
    verify_outputs

    echo ""
    log_success "🎉 Complete Docker workflow demonstration finished!"
    log_success "Your Telescope Correlator is fully containerized and CI/CD ready!"
    echo ""

    show_usage

    echo ""
    echo "💡 Next Steps:"
    echo "- Push to GitHub main branch to trigger CI/CD pipeline"
    echo "- Check Actions tab for automated testing results"
    echo "- Pull published images from GHCR for deployment"
    echo ""
}

# Run the demo
main "$@"