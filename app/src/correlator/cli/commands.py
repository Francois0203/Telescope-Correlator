"""Command-line interface for the FX correlator."""
from __future__ import annotations

import argparse
import sys

from correlator.config import CorrelatorConfig
from correlator.cli.runner import run_correlator
from correlator.cli.interactive import start_interactive_shell


def main(args=None) -> int:
    """Parse command-line arguments and run correlator."""
    parser = argparse.ArgumentParser(
        description="FX Correlator for Radio Telescope Arrays",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    
    # Add --interactive flag for shell mode
    parser.add_argument(
        "--interactive", "-i", action="store_true",
        help="Start interactive CLI shell"
    )
    
    # Configuration file
    parser.add_argument(
        "--config", type=str, default=None,
        help="Load configuration from YAML file (CLI args override file settings)"
    )
    
    # Array configuration
    parser.add_argument("--n-ants", type=int, help="Number of antennas")
    parser.add_argument("--array-radius", type=float, help="Antenna array radius (meters)")
    
    # Signal parameters
    parser.add_argument("--sample-rate", type=float, help="Sample rate (Hz)")
    parser.add_argument("--center-freq", type=float, help="Center frequency (Hz)")
    
    # F-Engine
    parser.add_argument("--n-channels", type=int, help="Number of frequency channels")
    parser.add_argument("--window-type", choices=["rectangular", "hanning", "hamming", "blackman"],
                        help="Window function for channeliser")
    parser.add_argument("--quantize-bits", type=int, help="Quantization bits (0=none)")
    parser.add_argument("--overlap-factor", type=float, help="FFT window overlap (0.0-0.5)")
    
    # X-Engine
    parser.add_argument("--integration-time", type=float, help="Integration time (seconds)")
    
    # Data source
    parser.add_argument("--mode", choices=["simulated", "file"], help="Data source mode")
    parser.add_argument("--input-file", type=str, help="Input file for file mode")
    
    # Simulation parameters
    parser.add_argument("--sim-duration", type=float, help="Simulation duration (seconds)")
    parser.add_argument("--sim-snr", type=float, help="Simulated signal SNR (dB)")
    parser.add_argument("--sim-realtime", action="store_true", help="Simulate real-time streaming")
    
    # Delay compensation
    parser.add_argument("--no-delays", action="store_true", help="Disable delay compensation")
    
    # Output
    parser.add_argument("--output-dir", type=str, help="Output directory")
    parser.add_argument("--save-channelised", action="store_true", 
                        help="Save intermediate F-engine output")
    parser.add_argument("--max-integrations", type=int, 
                        help="Maximum integrations to compute (default=unlimited)")
    
    # Runtime
    parser.add_argument("--chunk-size", type=int, help="Samples per processing chunk")
    
    parsed = parser.parse_args(args)
    
    # If interactive mode requested, start shell
    if parsed.interactive:
        start_interactive_shell()
        return 0
    
    # Load base configuration
    if parsed.config:
        print(f"Loading configuration from {parsed.config}")
        config = CorrelatorConfig.from_yaml(parsed.config)
    else:
        config = CorrelatorConfig()
    
    # Override with CLI arguments
    if parsed.n_ants is not None:
        config.n_ants = parsed.n_ants
    if parsed.array_radius is not None:
        config.ant_radius = parsed.array_radius
    if parsed.sample_rate is not None:
        config.sample_rate = parsed.sample_rate
    if parsed.center_freq is not None:
        config.center_freq = parsed.center_freq
    if parsed.n_channels is not None:
        config.n_channels = parsed.n_channels
    if parsed.window_type is not None:
        config.window_type = parsed.window_type
    if parsed.quantize_bits is not None:
        config.quantize_bits = parsed.quantize_bits
    if parsed.overlap_factor is not None:
        config.overlap_factor = parsed.overlap_factor
    if parsed.integration_time is not None:
        config.integration_time = parsed.integration_time
    if parsed.mode is not None:
        config.mode = parsed.mode
    if parsed.input_file is not None:
        config.input_file = parsed.input_file
    if parsed.sim_duration is not None:
        config.sim_duration = parsed.sim_duration
    if parsed.sim_snr is not None:
        config.sim_snr = parsed.sim_snr
    if parsed.sim_realtime:
        config.sim_realtime = True
    if parsed.no_delays:
        config.enable_delays = False
    if parsed.output_dir is not None:
        config.output_dir = parsed.output_dir
    if parsed.save_channelised:
        config.save_channelised = True
    if parsed.max_integrations is not None:
        config.max_integrations = parsed.max_integrations
    if parsed.chunk_size is not None:
        config.chunk_size = parsed.chunk_size
    
    try:
        return run_correlator(config)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
