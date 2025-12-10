"""Command-line interface for the FX correlator.

This is the main entry point to run the correlator from the terminal.
Implements batch and simulated streaming modes.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
import numpy as np
from typing import Optional

from correlator.config import CorrelatorConfig
from correlator.frontend import SimulatedStream, BatchFileSource
from correlator.fengine import FEngine
from correlator.xengine import XEngine
from correlator.delay import DelayEngine


def run_correlator(config: CorrelatorConfig) -> int:
    """Execute FX correlator pipeline with given configuration.
    
    Pipeline stages:
    1. Frontend: Load data (file or simulated stream)
    2. F-Engine: Channelise with windowed FFT
    3. Delay Engine: Apply geometric delay compensation
    4. X-Engine: Cross-correlate and integrate
    5. Output: Save visibility products
    
    Returns
    -------
    int
        Exit code (0 = success)
    """
    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize pipeline components
    print(f"Initializing FX correlator with {config.n_ants} antennas, {config.n_channels} channels")
    
    # Frontend
    if config.mode == "simulated":
        print(f"Creating simulated stream: {config.sim_duration}s @ {config.sample_rate} Hz")
        print(f"  Sources: {config.sim_source_angles} rad")
        print(f"  SNR: {config.sim_snr} dB")
        
        ant_pos = config.get_ant_positions()
        total_samples = int(config.sim_duration * config.sample_rate)
        max_chunks = int(np.ceil(total_samples / config.chunk_size))
        print(f"  Total samples: {total_samples}, chunks: {max_chunks}")
        
        sim_source = SimulatedStream(
            n_ants=config.n_ants,
            sample_rate=config.sample_rate,
            ant_positions=ant_pos,
            source_angles=config.sim_source_angles,
            freq=config.sim_freq,
            snr=config.sim_snr,
        )
        
        source = sim_source.stream(
            chunk_size=config.chunk_size,
            max_chunks=max_chunks,
            realtime=config.sim_realtime,
        )
    else:
        print(f"Loading data from {config.input_file}")
        batch_source = BatchFileSource(
            file_path=config.input_file,
            sample_rate=config.sample_rate,
        )
        source = batch_source.stream(chunk_size=config.chunk_size)
    
    # F-Engine
    fengine = FEngine(
        n_channels=config.n_channels,
        window_type=config.window_type,
        quantize_bits=config.quantize_bits,
        overlap_factor=config.overlap_factor,
    )
    
    # Delay Engine
    if config.enable_delays:
        ant_pos = config.get_ant_positions()
        # Add z=0 if 2D positions
        if ant_pos.shape[1] == 2:
            ant_pos = np.hstack([ant_pos, np.zeros((config.n_ants, 1))])
        
        delay_engine = DelayEngine(
            ant_positions=ant_pos,
            reference_freq=config.center_freq,
        )
        delay_engine.set_phase_center(np.array(config.phase_center))
        print("Delay compensation enabled")
    else:
        delay_engine = None
        print("Delay compensation disabled")
    
    # X-Engine
    xengine = XEngine(
        n_ants=config.n_ants,
        n_channels=config.n_channels,
        integration_time=config.integration_time,
        sample_rate=config.sample_rate,
    )
    spectra_per_integration = xengine.spectra_per_integration
    print(f"Integration time: {config.integration_time}s ({spectra_per_integration} spectra)")
    
    # Processing loop
    integration_count = 0
    channelised_data = []
    
    print("\nProcessing...")
    for chunk_idx, time_data in enumerate(source):
        # F-Engine: channelise
        channelised = fengine.process_chunk(time_data)  # Shape: (n_ants, n_spectra, n_channels)
        n_ants, n_spectra, n_channels = channelised.shape
        
        # Delay compensation
        if delay_engine:
            freq_channels = np.fft.fftfreq(config.n_channels, 1 / config.sample_rate)
            channelised = delay_engine.apply_delays(channelised, freq_channels)
        
        # Save channelised data if requested
        if config.save_channelised:
            channelised_data.append(channelised)
        
        # X-Engine: correlate each spectrum
        for spec_idx in range(n_spectra):
            spectrum = channelised[:, spec_idx, :]  # Shape: (n_ants, n_channels)
            vis = xengine.correlate_spectrum(spectrum)
            xengine.accumulate(vis)
            
            # Check if integration complete
            if xengine.is_ready():
                integrated_vis = xengine.get_integrated()
                integration_count += 1
                
                # Save integrated visibility
                vis_file = output_dir / f"visibility_{integration_count:04d}.npy"
                np.save(vis_file, integrated_vis)
                print(f"  Saved integration {integration_count} -> {vis_file.name}")
                
                # Check if we've reached max integrations
                if config.max_integrations and integration_count >= config.max_integrations:
                    print(f"Reached max integrations ({config.max_integrations})")
                    break
            
        # Break outer loop if max integrations reached
        if config.max_integrations and integration_count >= config.max_integrations:
            break
    
    # Save channelised data if requested
    if config.save_channelised and channelised_data:
        channelised_file = output_dir / "channelised.npy"
        np.save(channelised_file, np.array(channelised_data))
        print(f"Saved channelised data: {channelised_file}")
    
    # Save configuration for reproducibility
    config_file = output_dir / "config.yaml"
    config.to_yaml(config_file)
    print(f"Saved configuration: {config_file}")
    
    print(f"\nComplete: {integration_count} integrations written to {output_dir}/")
    return 0


def main(args=None) -> int:
    """Parse command-line arguments and run correlator."""
    parser = argparse.ArgumentParser(
        description="FX Correlator for Radio Telescope Arrays",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
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
