#!/usr/bin/env python3
"""
Visualization script for radio telescope correlator data.

This script shows what the antennas "see" and what happens after correlation.
Run this after running the correlator to visualize your results.
"""

import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import argparse

def load_and_visualize(vis_file, show_raw_signals=True, save_plots=True):
    """
    Load visibility data and create visualizations.

    Parameters:
    -----------
    vis_file : str
        Path to visibility .npy file
    show_raw_signals : bool
        Whether to show simulated raw signals (requires running simulation)
    save_plots : bool
        Whether to save plots to disk
    """

    vis_path = Path(vis_file)
    if not vis_path.exists():
        print(f"Error: Visibility file {vis_file} not found!")
        return

    # Load visibility data
    vis = np.load(vis_path)
    print(f"Loaded visibility data: shape {vis.shape}")

    # Determine number of antennas from baselines
    n_baselines = vis.shape[0]
    # For N antennas: N(N+1)/2 = baselines
    # Solving: N² + N - 2*baselines = 0
    n_ants = int((-1 + np.sqrt(1 + 8*n_baselines)) / 2)
    print(f"Detected {n_ants} antennas from {n_baselines} baselines")

    # Create figure with subplots
    if show_raw_signals:
        fig, axes = plt.subplots(2, 3, figsize=(18, 10))
        fig.suptitle('Radio Telescope: Antennas → Correlation', fontsize=16, fontweight='bold')
    else:
        fig, axes = plt.subplots(1, 3, figsize=(18, 5))
        fig.suptitle('Radio Telescope Correlation Results', fontsize=16, fontweight='bold')
        axes = axes.reshape(1, -1)  # Make 2D for consistent indexing

    plot_row = 0

    # 1. Raw antenna signals (if requested)
    if show_raw_signals:
        print("Generating sample of raw antenna signals...")
        from correlator.frontend import SimulatedStream

        # Create sample signals (short duration for visualization)
        sim_source = SimulatedStream(
            n_ants=n_ants,
            sample_rate=1024.0,
            source_angles=[0.0, np.pi/6],  # Two sources
            freq=1.0,
            snr=20.0,
        )

        raw_signals = next(sim_source.stream(chunk_size=512, max_chunks=1))
        time_ms = np.arange(raw_signals.shape[1]) / 1024.0 * 1000

        for ant in range(n_ants):
            axes[plot_row, 0].plot(time_ms, raw_signals[ant, :].real,
                                  label=f'Antenna {ant}', linewidth=1.5)

        axes[plot_row, 0].set_xlabel('Time (ms)')
        axes[plot_row, 0].set_ylabel('Signal Voltage')
        axes[plot_row, 0].set_title('What Antennas See\n(Raw Time Signals)')
        axes[plot_row, 0].legend()
        axes[plot_row, 0].grid(True, alpha=0.3)

        # 2. Signal spectrum
        from scipy import signal
        for ant in range(n_ants):
            freqs, psd = signal.welch(raw_signals[ant, :], fs=1024.0, nperseg=128)
            axes[plot_row, 1].semilogy(freqs, psd, label=f'Ant {ant}', linewidth=1.5)

        axes[plot_row, 1].axvline(1.0, color='red', linestyle='--', alpha=0.7, label='Signal')
        axes[plot_row, 1].set_xlabel('Frequency (Hz)')
        axes[plot_row, 1].set_ylabel('Power')
        axes[plot_row, 1].set_title('Signal Spectrum\n(Before Processing)')
        axes[plot_row, 1].legend()
        axes[plot_row, 1].grid(True, alpha=0.3)

        plot_row += 1

    # 3. Visibility amplitudes by baseline
    baselines = range(n_baselines)
    amplitudes = np.abs(vis[:, 0])  # First frequency channel

    colors = ['red'] * n_ants + ['blue'] * (n_baselines - n_ants)  # Auto vs cross
    bars = axes[plot_row, 0].bar(baselines, amplitudes, color=colors, alpha=0.7)

    # Create baseline labels
    baseline_labels = []
    baseline_idx = 0
    for i in range(n_ants):
        for j in range(i, n_ants):
            baseline_labels.append(f'{i}-{j}')

    axes[plot_row, 0].set_xlabel('Baseline (Antenna Pair)')
    axes[plot_row, 0].set_ylabel('Visibility Amplitude')
    axes[plot_row, 0].set_title('Correlation Results\n(Visibility Amplitudes)')
    axes[plot_row, 0].set_xticks(baselines)
    axes[plot_row, 0].set_xticklabels(baseline_labels, rotation=45)
    axes[plot_row, 0].grid(True, alpha=0.3)

    # 4. Complex visibility space (one cross-correlation)
    cross_baseline_idx = 1  # First cross-correlation
    if n_baselines > n_ants:  # Make sure we have cross-correlations
        real_part = vis[cross_baseline_idx, :].real
        imag_part = vis[cross_baseline_idx, :].imag

        scatter = axes[plot_row, 1].scatter(real_part, imag_part,
                                           c=np.arange(len(real_part)),
                                           cmap='viridis', alpha=0.7, s=20)
        axes[plot_row, 1].set_xlabel('Real Part')
        axes[plot_row, 1].set_ylabel('Imaginary Part')
        axes[plot_row, 1].set_title(f'Complex Visibility\n(Baseline {baseline_labels[cross_baseline_idx]})')
        axes[plot_row, 1].grid(True, alpha=0.3)
        axes[plot_row, 1].axis('equal')
        plt.colorbar(scatter, ax=axes[plot_row, 1], label='Frequency Channel')
    else:
        axes[plot_row, 1].text(0.5, 0.5, 'No cross-correlations\n(only autocorrelations)',
                              transform=axes[plot_row, 1].transAxes, ha='center', va='center')
        axes[plot_row, 1].set_title('Complex Visibility\n(No cross-correlations)')

    # 5. Visibility vs frequency (waterfall plot)
    im = axes[plot_row, 2].imshow(np.abs(vis).T, aspect='auto', cmap='viridis',
                                 extent=[0, n_baselines-1, vis.shape[1]-1, 0])
    axes[plot_row, 2].set_xlabel('Baseline Index')
    axes[plot_row, 2].set_ylabel('Frequency Channel')
    axes[plot_row, 2].set_title('Visibility Spectrum\n(Amplitude vs Frequency)')
    axes[plot_row, 2].set_xticks(range(n_baselines))
    axes[plot_row, 2].set_xticklabels(baseline_labels, rotation=45)
    plt.colorbar(im, ax=axes[plot_row, 2], label='Visibility Amplitude')

    plt.tight_layout()

    if save_plots:
        output_file = vis_path.parent / f"{vis_path.stem}_visualization.png"
        plt.savefig(output_file, dpi=150, bbox_inches='tight')
        print(f"Saved visualization to: {output_file}")

    plt.show()

def main():
    parser = argparse.ArgumentParser(description="Visualize radio telescope correlator data")
    parser.add_argument("vis_file", help="Path to visibility .npy file")
    parser.add_argument("--no-raw", action="store_true",
                       help="Skip raw signal simulation (faster)")
    parser.add_argument("--no-save", action="store_true",
                       help="Don't save plots to disk")

    args = parser.parse_args()

    load_and_visualize(
        args.vis_file,
        show_raw_signals=not args.no_raw,
        save_plots=not args.no_save
    )

if __name__ == "__main__":
    main()