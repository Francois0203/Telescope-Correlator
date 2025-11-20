# Multi-stage Dockerfile for the Telescope Correlator
FROM python:3.11-slim AS builder
WORKDIR /app

# Install build-time dependencies
RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*
COPY requirements.txt /app/
RUN python -m pip install --upgrade pip && pip install --prefix=/install -r requirements.txt

FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /install /usr/local

# Put the app sources on the image and set PYTHONPATH so package can be imported
COPY src/ /app/src/
ENV PYTHONPATH=/app/src

# Lightweight entry: run the correlator CLI
ENTRYPOINT ["python", "-m", "correlator"]
