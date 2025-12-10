"""Telescope Correlator Package

A modular FX correlator implementation following radio astronomy correlator
architecture with separate F-engine (channeliser) and X-engine (cross-multiply
and accumulate) stages.

Main components:
- frontend: Data ingestion (batch files, simulated streaming)
- fengine: Channeliser (windowed FFT, quantization)
- xengine: Cross-correlation and accumulation
- delay: Geometric delay compensation and phasing
- config: Configuration management
- cli: Command-line interface
"""

__version__ = "0.1.0"

from correlator.config import CorrelatorConfig
from correlator.frontend import DataSource, SimulatedStream, BatchFileSource
from correlator.fengine import FEngine
from correlator.xengine import XEngine
from correlator.delay import DelayEngine

__all__ = [
    "__version__",
    "CorrelatorConfig",
    "DataSource",
    "SimulatedStream",
    "BatchFileSource",
    "FEngine",
    "XEngine",
    "DelayEngine",
]
