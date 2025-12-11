#!/bin/bash
# Docker management script for Telescope Correlator

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

# Check if Docker is running
check_docker() {
    if ! docker info >/dev/null 2>&1; then
        log_error "Docker is not running. Please start Docker first."
        exit 1
    fi
}

# Build the Docker image
build() {
    log_info "Building Docker image..."
    cd "$PROJECT_ROOT"
    docker compose build
    log_success "Docker image built successfully"
}

# Run tests
test() {
    log_info "Running tests..."
    cd "$PROJECT_ROOT"
    docker compose run --rm test
    log_success "Tests completed"
}

# Run the correlator with default parameters
run() {
    log_info "Running correlator..."
    cd "$PROJECT_ROOT"
    docker compose run --rm correlator "$@"
}

# Start development shell
dev() {
    log_info "Starting development shell..."
    cd "$PROJECT_ROOT"
    docker compose run --rm dev
}

# Pull and run latest published image
pull-run() {
    log_info "Pulling latest published image..."
    cd "$PROJECT_ROOT"
    docker pull ghcr.io/francois0203/telescope-correlator:latest
    log_success "Latest image pulled successfully"

    log_info "Running correlator with latest image..."
    docker run --rm -v "$(pwd)/dev_workspace/outputs:/app/outputs" ghcr.io/francois0203/telescope-correlator:latest python -m correlator "$@"
}

# Start interactive CLI shell
cli() {
    log_info "Starting interactive correlator CLI..."
    cd "$PROJECT_ROOT"
    docker compose up cli
}

# Show usage
usage() {
    echo "Telescope Correlator Docker Management Script"
    echo ""
    echo "Usage: $0 <command> [options]"
    echo ""
    echo "Commands:"
    echo "  cli       Start interactive correlator CLI (persistent)"
    echo "  build     Build the Docker image"
    echo "  test      Run the test suite"
    echo "  run       Run the correlator (pass correlator args after --)"
    echo "  pull-run  Pull latest published image and run correlator"
    echo "  dev       Start development shell"
    echo "  clean     Clean up Docker resources"
    echo "  help      Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 cli       # Start interactive CLI shell"
    echo "  $0 build"
    echo "  $0 test"
    echo "  $0 run -- --n-ants 4 --n-channels 128 --sim-duration 1.0"
    echo "  $0 pull-run -- --n-ants 4 --n-channels 64 --sim-duration 0.5"
    echo "  $0 dev"
    echo "  $0 clean"
}

# Main command dispatcher
case "${1:-help}" in
    cli)
        check_docker
        cli
        ;;
    build)
        check_docker
        build
        ;;
    test)
        check_docker
        test
        ;;
    run)
        check_docker
        shift
        run "$@"
        ;;
    pull-run)
        check_docker
        shift
        pull-run "$@"
        ;;
    dev)
        check_docker
        dev
        ;;
    clean)
        clean
        ;;
    help|--help|-h)
        usage
        ;;
    *)
        log_error "Unknown command: $1"
        echo ""
        usage
        exit 1
        ;;
esac