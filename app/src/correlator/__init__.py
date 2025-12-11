"""Telescope Correlator Package

A modular FX correlator implementation following radio astronomy correlator
architecture with separate F-engine (channeliser) and X-engine (cross-multiply
and accumulate) stages.

Package structure:
- core/: Core signal processing modules (delay, fengine, frontend, xengine)
- cli/: Command-line interface and interactive shell
- config.py: Configuration management
- utils/: Utility functions and helpers

Main components:
- frontend: Data ingestion (batch files, simulated streaming)
- fengine: Channeliser (windowed FFT, quantization)
- xengine: Cross-correlation and accumulation
- delay: Geometric delay compensation and phasing
- config: Configuration management
- cli: Command-line interface with interactive shell
"""

__version__ = "1.0.0"

from correlator.config import CorrelatorConfig
from correlator.core import (
    DataSource,
    SimulatedStream,
    BatchFileSource,
    FEngine,
    XEngine,
    DelayEngine,
    calculate_geometric_delays,
)

__all__ = [
    "__version__",
    "CorrelatorConfig",
    "DataSource",
    "SimulatedStream",
    "BatchFileSource",
    "FEngine",
    "XEngine",
    "DelayEngine",
    "calculate_geometric_delays",
]
