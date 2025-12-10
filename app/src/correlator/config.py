"""Configuration Management

Handles correlator configuration with sensible defaults and validation.
Supports loading from YAML files or programmatic configuration.
"""
from __future__ import annotations

import yaml
from pathlib import Path
from typing import Any, Optional, Literal
from dataclasses import dataclass, field, asdict
import numpy as np


WindowType = Literal["rectangular", "hanning", "hamming", "blackman"]


@dataclass
class CorrelatorConfig:
    """Complete correlator configuration."""
    
    # Array configuration
    n_ants: int = 4
    ant_positions: Optional[np.ndarray] = None  # If None, use uniform circle
    ant_radius: float = 10.0  # For auto-generated positions
    
    # Signal parameters
    sample_rate: float = 1024.0  # Hz
    center_freq: float = 1.0  # Hz (arbitrary units)
    
    # F-engine (channeliser)
    n_channels: int = 256
    window_type: WindowType = "hanning"
    quantize_bits: int = 0  # 0 = no quantization
    overlap_factor: float = 0.0  # 0.0 to 0.5
    
    # X-engine (correlator)
    integration_time: float = 1.0  # seconds
    
    # Data source
    mode: Literal["simulated", "file"] = "simulated"
    input_file: Optional[str] = None  # For file mode
    
    # Simulation parameters (when mode="simulated")
    sim_source_angles: list[float] = field(default_factory=lambda: [0.0, np.pi/6])
    sim_freq: float = 1.0
    sim_snr: float = 20.0
    sim_duration: float = 10.0  # seconds
    sim_realtime: bool = False  # Simulate real-time streaming
    
    # Delay compensation
    enable_delays: bool = True
    phase_center: list[float] = field(default_factory=lambda: [1.0, 0.0, 0.0])  # Unit vector
    
    # Output
    output_dir: str = "../dev_workspace/outputs"
    save_channelised: bool = False  # Save intermediate F-engine output
    save_visibilities: bool = True
    
    # Runtime
    chunk_size: int = 4096  # Samples per processing chunk
    max_integrations: Optional[int] = None  # None = run until data exhausted
    
    def __post_init__(self):
        """Validate and normalize configuration."""
        if self.n_ants < 2:
            raise ValueError("n_ants must be >= 2")
        
        if self.n_channels < 2 or (self.n_channels & (self.n_channels - 1)) != 0:
            raise ValueError("n_channels must be a power of 2")
        
        if self.integration_time <= 0:
            raise ValueError("integration_time must be positive")
        
        if self.mode == "file" and self.input_file is None:
            raise ValueError("input_file must be specified when mode='file'")
    
    @classmethod
    def from_yaml(cls, path: str | Path) -> "CorrelatorConfig":
        """Load configuration from YAML file."""
        with open(path, "r") as f:
            data = yaml.safe_load(f) or {}
        
        # Convert ant_positions from list to ndarray if present
        if "ant_positions" in data and data["ant_positions"] is not None:
            data["ant_positions"] = np.array(data["ant_positions"])
        
        return cls(**data)
    
    def to_yaml(self, path: str | Path):
        """Save configuration to YAML file."""
        data = asdict(self)
        
        # Convert ndarray to list for YAML serialization
        if self.ant_positions is not None:
            data["ant_positions"] = self.ant_positions.tolist()
        
        with open(path, "w") as f:
            yaml.dump(data, f, default_flow_style=False)
    
    def get_ant_positions(self) -> np.ndarray:
        """Get or generate antenna positions."""
        if self.ant_positions is not None:
            return self.ant_positions
        
        # Generate uniform circle
        angles = np.linspace(0, 2 * np.pi, self.n_ants, endpoint=False)
        x = self.ant_radius * np.cos(angles)
        y = self.ant_radius * np.sin(angles)
        return np.stack([x, y], axis=1)
