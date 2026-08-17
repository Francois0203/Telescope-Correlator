# Validation image: the correlator plus the Tier 2 reference stack.
#
# Self-contained rather than layered on telescope-correlator:latest, so
# `docker build -f validation/Dockerfile .` works on a bare server with no
# prior images and no build ordering to remember.
#
# Build context is the repository root:
#     docker build -f validation/Dockerfile -t telescope-correlator-validation .
FROM python:3.11-slim

# libopenmpi is needed to build mpi4py, which pyuvsim.uvsim imports even for a
# single-process run. This is the dependency that makes running Tier 2 on a
# workstation awkward and in a container trivial.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libopenmpi-dev \
        openmpi-bin \
    && rm -rf /var/lib/apt/lists/*

# Dependencies first, in their own layers, so edits to source or scenarios do
# not trigger a numba/astropy rebuild.
COPY requirements.txt /tmp/requirements.txt
RUN python -m pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /tmp/requirements.txt

COPY validation/requirements.txt /tmp/validation-requirements.txt
RUN pip install --no-cache-dir -r /tmp/validation-requirements.txt

# The correlator itself.
COPY app/src/ /app/src/
RUN pip install --no-cache-dir /app/src/

# Validation harness and the project's own test suite, so one image runs every
# check. The shipped configs come too: tests_harness/unit/test_config.py
# asserts every key in them is a real Config field, and skips silently if they
# are absent. Without them, that check quietly disappears.
COPY validation/ /app/validation/
COPY tests_harness/ /app/tests_harness/
COPY workspace/configs/ /app/workspace/configs/

# Open MPI refuses to run as root unless told to. Set here so `mpirun -n N`
# works if the simulation is ever scaled up on a server.
ENV OMPI_ALLOW_RUN_AS_ROOT=1 \
    OMPI_ALLOW_RUN_AS_ROOT_CONFIRM=1 \
    OMPI_MCA_btl_vader_single_copy_mechanism=none \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    MPLCONFIGDIR=/tmp/matplotlib

# Astropy needs to resolve Earth-rotation data to convert AltAz to ICRS. The
# bundled astropy-iers-data table is used offline; this stops astropy trying to
# reach the network and hanging on an air-gapped server.
ENV ASTROPY_IERS_AUTO_DOWNLOAD=False

# Run as non-root. Nothing here needs write access outside /tmp and the
# reports mount.
RUN useradd --create-home --uid 10001 validator \
    && mkdir -p /app/reports \
    && chown -R validator:validator /app/reports
USER validator

WORKDIR /app/validation

# Both tiers by default.
CMD ["python", "run_validation.py", "--with-pyuvsim"]
