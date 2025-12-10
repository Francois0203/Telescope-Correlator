#!/usr/bin/env python3
"""
Simple visualization script for radio telescope correlator data.

This script shows correlation results without requiring the full correlator modules.
Run this after running the correlator to visualize your results.
"""

import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import argparse

def load_and_visualize_simple(vis_file, save_plots=True):
    """
    Load visibility data and create simple visualizations.

    Parameters:
    -----------
    vis_file : str
        Path to visibility .npy file
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
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    fig.suptitle('Radio Telescope Correlation Results', fontsize=16, fontweight='bold')

    # Create baseline labels
    baseline_labels = []
    baseline_idx = 0
    for i in range(n_ants):
        for j in range(i, n_ants):
            baseline_labels.append(f'{i}-{j}')

    # 1. Visibility amplitudes by baseline (first frequency)
    baselines = range(n_baselines)
    amplitudes = np.abs(vis[:, 0])  # First frequency channel

    colors = ['red'] * n_ants + ['blue'] * (n_baselines - n_ants)  # Auto vs cross
    bars = axes[0, 0].bar(baselines, amplitudes, color=colors, alpha=0.7)

    axes[0, 0].set_xlabel('Baseline (Antenna Pair)')
    axes[0, 0].set_ylabel('Visibility Amplitude')
    axes[0, 0].set_title('Visibility Amplitudes\n(First Frequency Channel)')
    axes[0, 0].set_xticks(baselines)
    axes[0, 0].set_xticklabels(baseline_labels, rotation=45)
    axes[0, 0].grid(True, alpha=0.3)

    # Add legend
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='red', alpha=0.7, label='Autocorrelations'),
        Patch(facecolor='blue', alpha=0.7, label='Cross-correlations')
    ]
    axes[0, 0].legend(handles=legend_elements, loc='upper right')

    # 2. Complex visibility space (first cross-correlation)
    cross_baseline_idx = n_ants  # First cross-correlation (after autocorrelations)
    if n_baselines > n_ants:  # Make sure we have cross-correlations
        real_part = vis[cross_baseline_idx, :].real
        imag_part = vis[cross_baseline_idx, :].imag

        scatter = axes[0, 1].scatter(real_part, imag_part,
                                   c=np.arange(len(real_part)),
                                   cmap='viridis', alpha=0.7, s=20)
        axes[0, 1].set_xlabel('Real Part')
        axes[0, 1].set_ylabel('Imaginary Part')
        axes[0, 1].set_title(f'Complex Visibility\n(Baseline {baseline_labels[cross_baseline_idx]})')
        axes[0, 1].grid(True, alpha=0.3)
        axes[0, 1].axis('equal')
        plt.colorbar(scatter, ax=axes[0, 1], label='Frequency Channel')
    else:
        axes[0, 1].text(0.5, 0.5, 'No cross-correlations\n(only autocorrelations)',
                      transform=axes[0, 1].transAxes, ha='center', va='center')
        axes[0, 1].set_title('Complex Visibility\n(No cross-correlations)')

    # 3. Visibility spectrum (waterfall plot)
    im = axes[1, 0].imshow(np.abs(vis).T, aspect='auto', cmap='viridis',
                         extent=[0, n_baselines-1, vis.shape[1]-1, 0])
    axes[1, 0].set_xlabel('Baseline Index')
    axes[1, 0].set_ylabel('Frequency Channel')
    axes[1, 0].set_title('Visibility Spectrum\n(Amplitude vs Frequency)')
    axes[1, 0].set_xticks(range(n_baselines))
    axes[1, 0].set_xticklabels(baseline_labels, rotation=45)
    plt.colorbar(im, ax=axes[1, 0], label='Visibility Amplitude')

    # 4. Phase information
    if n_baselines > n_ants:
        phases = np.angle(vis[cross_baseline_idx, :])  # Phase in radians
        axes[1, 1].plot(phases, 'b.-', linewidth=1, markersize=3)
        axes[1, 1].set_xlabel('Frequency Channel')
        axes[1, 1].set_ylabel('Phase (radians)')
        axes[1, 1].set_title(f'Visibility Phase\n(Baseline {baseline_labels[cross_baseline_idx]})')
        axes[1, 1].grid(True, alpha=0.3)
        axes[1, 1].set_ylim(-np.pi, np.pi)
        # Add pi/2 grid lines
        axes[1, 1].axhline(y=np.pi/2, color='r', linestyle='--', alpha=0.5, label='π/2')
        axes[1, 1].axhline(y=-np.pi/2, color='r', linestyle='--', alpha=0.5, label='-π/2')
        axes[1, 1].legend()
    else:
        axes[1, 1].text(0.5, 0.5, 'No cross-correlations\nfor phase analysis',
                      transform=axes[1, 1].transAxes, ha='center', va='center')
        axes[1, 1].set_title('Visibility Phase\n(No cross-correlations)')

    plt.tight_layout()

    if save_plots:
        output_file = vis_path.parent / f"{vis_path.stem}_simple_visualization.png"
        plt.savefig(output_file, dpi=150, bbox_inches='tight')
        print(f"Saved visualization to: {output_file}")

    plt.show()

def print_data_summary(vis_file):
    """Print a summary of the visibility data."""
    vis = np.load(vis_file)
    n_baselines, n_freqs = vis.shape

    # Calculate number of antennas
    n_ants = int((-1 + np.sqrt(1 + 8*n_baselines)) / 2)

    print("\n=== Visibility Data Summary ===")
    print(f"File: {vis_file}")
    print(f"Shape: {vis.shape} (baselines × frequency channels)")
    print(f"Antennas: {n_ants}")
    print(f"Baselines: {n_baselines} total")
    print(f"  - Autocorrelations: {n_ants}")
    print(f"  - Cross-correlations: {n_baselines - n_ants}")
    print(f"Frequency channels: {n_freqs}")
    print(f"Data type: {vis.dtype}")
    print(f"Value range: {np.abs(vis).min():.3f} to {np.abs(vis).max():.3f}")
    print(f"Memory usage: {vis.nbytes / 1024:.1f} KB")

    # Show first few baselines
    print("\nFirst few baselines (antenna pairs):")
    baseline_idx = 0
    for i in range(min(n_ants, 5)):
        for j in range(i, min(i+3, n_ants)):
            amp = np.abs(vis[baseline_idx, 0])
            phase = np.angle(vis[baseline_idx, 0])
            print(f"  {i}-{j}: amplitude={amp:.3f}, phase={phase:.3f} rad")
            baseline_idx += 1
            if baseline_idx >= 10:  # Limit output
                break
        if baseline_idx >= 10:
            break

def main():
    parser = argparse.ArgumentParser(description="Simple visualization of radio telescope correlator data")
    parser.add_argument("vis_file", help="Path to visibility .npy file")
    parser.add_argument("--no-save", action="store_true",
                       help="Don't save plots to disk")
    parser.add_argument("--summary-only", action="store_true",
                       help="Only print data summary, don't create plots")

    args = parser.parse_args()

    if args.summary_only:
        print_data_summary(args.vis_file)
    else:
        load_and_visualize_simple(args.vis_file, save_plots=not args.no_save)

if __name__ == "__main__":
    main()