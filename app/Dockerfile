# Multi-stage Dockerfile for the Telescope Correlator
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build-time dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt /app/
RUN python -m pip install --upgrade pip && \
    pip install --prefix=/install -r requirements.txt

# Copy source code and install the package
COPY app/src/ /app/src/
RUN pip install --prefix=/install /app/src/

FROM python:3.11-slim

WORKDIR /app

# Copy installed packages from builder stage
COPY --from=builder /install /usr/local

# Set environment variables
ENV PYTHONPATH=/usr/local/lib/python3.11/site-packages
ENV PYTHONUNBUFFERED=1

# Default: start the interactive shell
CMD ["python", "-m", "correlator"]