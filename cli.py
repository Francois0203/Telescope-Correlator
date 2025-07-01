"""
cli.py
Teaching-focused CLI for the FX radio telescope correlator.
Guides users step-by-step through the correlator pipeline with explanations and sample data.
"""
import argparse
import sys
import os
import numpy as np
import h5py
from signal_reader import SignalReader
from fengine import FEngine
from xengine import XEngine
from integrator import Integrator
from output import OutputWriter

try:
    from colorama import Fore, Style, init as colorama_init
    colorama_init()
    COLOR = True
except ImportError:
    COLOR = False
    class Dummy:
        def __getattr__(self, name): return ''
    Fore = Style = Dummy()

def explain(msg):
    print(f"{Fore.CYAN if COLOR else ''}{msg}{Style.RESET_ALL if COLOR else ''}")

def highlight(msg):
    print(f"{Fore.YELLOW if COLOR else ''}{msg}{Style.RESET_ALL if COLOR else ''}")

def error(msg):
    print(f"{Fore.RED if COLOR else ''}Error: {msg}{Style.RESET_ALL if COLOR else ''}")

def prompt(msg):
    return input(f"{Fore.GREEN if COLOR else ''}{msg}{Style.RESET_ALL if COLOR else ''}")

def run_teaching(args):
    explain("Welcome to the FX Radio Telescope Correlator Teaching CLI!")
    explain("This tool will walk you through each step of a real radio telescope correlator pipeline, using simulated data.")
    if not args.non_interactive:
        prompt("Press Enter to begin...")

    explain("Step 1: Simulating Antenna Signals")
    highlight(f"Simulating {args.num_antennas} antennas with frequencies: {args.frequencies} Hz")
    signal_reader = SignalReader(args.num_antennas, args.sample_rate, args.frame_size, args.frequencies)
    signals = signal_reader.read()
    explain(f"Generated a time-domain signal array of shape {signals.shape} (antennas x samples). Each row is a simulated antenna.")
    highlight(f"Sample data (first 5 samples of antenna 0): {signals[0, :5]}")
    if not args.non_interactive:
        prompt("Press Enter to continue to the F-Engine (FFT)...")

    explain("Step 2: F-Engine (Frequency Channelisation with FFT)")
    fengine = FEngine(args.fft_size)
    fft_data = fengine.channelise(signals)
    explain(f"Applied FFT to each antenna. Output shape: {fft_data.shape} (antennas x frequency channels)")
    highlight(f"Sample FFT data (antenna 0, first 5 freqs): {fft_data[0, :5]}")
    if not args.non_interactive:
        prompt("Press Enter to continue to the X-Engine (Correlation)...")

    explain("Step 3: X-Engine (Cross-Correlation)")
    xengine = XEngine(args.num_antennas)
    vis = xengine.correlate(fft_data)
    explain(f"Computed visibilities (auto and cross-correlations) for all antenna pairs. Output shape: {vis.shape} (ant1 x ant2 x freq)")
    highlight(f"Sample visibility (ant 0, ant 1, first 3 freqs): {vis[0,1,:3]}")
    if not args.non_interactive:
        prompt("Press Enter to continue to Integration...")

    explain("Step 4: Integration (Averaging over Time)")
    integrator = Integrator(args.n_integrate)
    explain(f"Integrating over {args.n_integrate} frames...")
    for i in range(args.n_integrate-1):
        vis_frame = xengine.correlate(fengine.channelise(signal_reader.read()))
        integrator.add(vis_frame)
    result = integrator.add(vis)
    explain(f"Integration complete. Integrated visibilities shape: {result.shape}")
    highlight(f"Sample integrated visibility (ant 0, ant 1, first 3 freqs): {result[0,1,:3]}")
    if not args.non_interactive:
        prompt("Press Enter to continue to Output...")

    explain("Step 5: Saving Output")
    output_writer = OutputWriter()
    freq_axis = np.fft.fftfreq(args.fft_size, d=1/args.sample_rate)
    metadata = {
        'num_antennas': args.num_antennas,
        'sample_rate': args.sample_rate,
        'frame_size': args.frame_size,
        'fft_size': args.fft_size,
        'n_integrate': args.n_integrate,
        'frequencies': args.frequencies,
    }
    outname = args.output
    output_writer.save(result, freq_axis, metadata, outname)
    explain(f"Output saved to {os.path.join('./output', outname)}")
    explain("You can now use the 'view' command to inspect the output file.")
    highlight(f"Try: python cli.py view ./output/{outname}")
    explain("Teaching pipeline complete! You have just run a full FX correlator simulation.")

def view_teaching(args):
    path = args.file
    if not os.path.exists(path):
        error(f"File not found: {path}")
        sys.exit(1)
    explain(f"\n--- Viewing HDF5 file: {path} ---\n")
    with h5py.File(path, 'r') as f:
        explain("Datasets in this file:")
        print(list(f.keys()))
        if 'visibilities' in f:
            explain(f"Visibilities shape: {f['visibilities'].shape}")
        if 'frequencies' in f:
            explain(f"Frequencies shape: {f['frequencies'].shape}")
            highlight(f"First 5 frequencies: {f['frequencies'][:5]}")
        if 'metadata' in f:
            explain("Metadata:")
            for k, v in f['metadata'].attrs.items():
                print(f"  {k}: {v}")
        if 'visibilities' in f:
            highlight(f"Sample visibility [0,0,0]: {f['visibilities'][0,0,0]}")
    explain("\n--- End of file ---\n")

def main():
    parser = argparse.ArgumentParser(
        description="Teaching CLI for the FX Correlator. Learn how a radio telescope correlator works, step by step!",
        formatter_class=argparse.RawTextHelpFormatter)
    subparsers = parser.add_subparsers(dest='command', required=True, help='Sub-commands')

    # Run teaching pipeline
    run_parser = subparsers.add_parser('run', help='Run the correlator simulation with teaching explanations')
    run_parser.add_argument('--num_antennas', type=int, default=4, help='Number of antennas (default: 4)')
    run_parser.add_argument('--sample_rate', type=float, default=1e6, help='Sample rate in Hz (default: 1e6)')
    run_parser.add_argument('--frame_size', type=int, default=4096, help='Samples per frame (default: 4096)')
    run_parser.add_argument('--fft_size', type=int, default=4096, help='FFT size (default: 4096)')
    run_parser.add_argument('--n_integrate', type=int, default=5, help='Frames to integrate (default: 5)')
    run_parser.add_argument('--frequencies', type=float, nargs='+', default=[1e5, 2e5, 3e5, 4e5], help='Antenna frequencies in Hz (default: 1e5 2e5 3e5 4e5)')
    run_parser.add_argument('--output', type=str, default='vis_teaching.h5', help='Output filename (default: vis_teaching.h5)')
    run_parser.add_argument('--non-interactive', action='store_true', help='Disable interactive prompts (for scripts)')
    run_parser.set_defaults(func=run_teaching)

    # View output
    view_parser = subparsers.add_parser('view', help='View/print contents of an HDF5 output file with explanations')
    view_parser.add_argument('file', type=str, help='Path to HDF5 file (e.g., output/vis_teaching.h5)')
    view_parser.set_defaults(func=view_teaching)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main() 