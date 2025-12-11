"""Correlator runner module - executes the FX pipeline."""
from __future__ import annotations

from pathlib import Path
import numpy as np

from correlator.config import CorrelatorConfig
from correlator.core.frontend import SimulatedStream, BatchFileSource
from correlator.core.fengine import FEngine
from correlator.core.xengine import XEngine
from correlator.core.delay import DelayEngine


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
