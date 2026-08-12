#!/usr/bin/env bash
# Build and run the correlator validation suite in Docker.
#
# Works identically on a workstation and on a bare Ubuntu server: the only
# requirement is Docker with the Compose plugin. Nothing is installed on the
# host.
#
#   ./validate.sh              full run: unit tests + Tier 1 + Tier 2 (pyuvsim)
#   ./validate.sh quick        Tier 1 only, no pyuvsim (~1 second)
#   ./validate.sh tests        the correlator's own pytest suite
#   ./validate.sh diagnose     classify a Tier 2 disagreement
#   ./validate.sh shell        interactive shell inside the validation image
#   ./validate.sh build        rebuild the image only
#
# JSON results land in validation/reports/ on the host.
set -euo pipefail

cd "$(dirname "$0")"

# Git Bash / MSYS rewrites anything that looks like a Unix path into a Windows
# one before handing it to docker.exe, turning /app/reports into
# C:/Program Files/Git/app/reports. Disable that. Both variables are ignored on
# Linux, so the script behaves identically on an Ubuntu server.
export MSYS_NO_PATHCONV=1
export MSYS2_ARG_CONV_EXCL='*'

IMAGE=telescope-correlator-validation:latest
MODE="${1:-full}"

if ! docker info >/dev/null 2>&1; then
  echo "Error: cannot reach the Docker daemon." >&2
  echo "  Linux:   sudo systemctl start docker" >&2
  echo "  Desktop: start Docker Desktop, or 'docker desktop start'" >&2
  exit 1
fi

mkdir -p validation/reports

build() {
  echo "==> Building ${IMAGE}"
  docker build -f validation/Dockerfile -t "${IMAGE}" .
}

# Build if the image is missing; otherwise reuse. Pass 'build' to force.
if [ "${MODE}" = "build" ]; then
  build
  exit 0
fi
if ! docker image inspect "${IMAGE}" >/dev/null 2>&1; then
  build
fi

run() {
  docker run --rm \
    -v "$(pwd)/validation/reports:/app/reports" \
    "${IMAGE}" "$@"
}

# Paths inside the container are given relative to the workdir
# (/app/validation) so they survive any residual path rewriting, and the image
# runs as a non-root user that cannot write a pytest cache next to the source.
PYTEST=(python -m pytest ../tests_harness -p no:cacheprovider)

case "${MODE}" in
  full)
    echo "==> Correlator test suite"
    run "${PYTEST[@]}" -q
    echo
    echo "==> Validation: Tier 1 (analytic oracle) + Tier 2 (pyuvsim)"
    run python run_validation.py --with-pyuvsim --json ../reports/validation.json
    echo
    echo "Reports written to validation/reports/"
    ;;
  quick)
    run python run_validation.py --json ../reports/validation-tier1.json
    ;;
  tests)
    run "${PYTEST[@]}" -v
    ;;
  diagnose)
    run python diagnose.py
    ;;
  shell)
    docker run --rm -it \
      -v "$(pwd)/validation/reports:/app/reports" \
      "${IMAGE}" bash
    ;;
  *)
    echo "Usage: $0 [full|quick|tests|diagnose|shell|build]" >&2
    exit 2
    ;;
esac
