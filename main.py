"""
main.py
Top-level CLI for the FX radio telescope correlator pipeline.
"""
import logging
import argparse
import numpy as np
import sys
import os
import h5py
from signal_reader import SignalReader
from fengine import FEngine
from xengine import XEngine
from integrator import Integrator
from output import OutputWriter

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s:%(name)s: %(message)s')
logger = logging.getLogger("main")

def run_pipeline(args):
    logger.info("Starting FX correlator pipeline...")
    signal_reader = SignalReader(args.num_antennas, args.sample_rate, args.frame_size, args.frequencies)
    fengine = FEngine(args.fft_size)
    xengine = XEngine(args.num_antennas)
    integrator = Integrator(args.n_integrate)
    output_writer = OutputWriter()

    freq_axis = np.fft.fftfreq(args.fft_size, d=1/args.sample_rate)
    n_outputs = 0
    for frame in range(args.n_integrate * 2):
        logger.info(f"Processing frame {frame+1}")
        signals = signal_reader.read()
        fft_data = fengine.channelise(signals)
        vis = xengine.correlate(fft_data)
        result = integrator.add(vis)
        if result is not None:
            metadata = {
                'num_antennas': args.num_antennas,
                'sample_rate': args.sample_rate,
                'frame_size': args.frame_size,
                'fft_size': args.fft_size,
                'n_integrate': args.n_integrate,
                'frequencies': args.frequencies,
            }
            outname = args.output if n_outputs == 0 else f"int_{n_outputs}_" + args.output
            output_writer.save(result, freq_axis, metadata, outname)
            n_outputs += 1
    logger.info("Pipeline complete. Output saved in ./output/")

def view_output(args):
    path = args.file
    if not os.path.exists(path):
        print(f"File not found: {path}")
        sys.exit(1)
    print(f"\n--- Viewing HDF5 file: {path} ---\n")
    with h5py.File(path, 'r') as f:
        print("Datasets:", list(f.keys()))
        if 'visibilities' in f:
            print("Visibilities shape:", f['visibilities'].shape)
        if 'frequencies' in f:
            print("Frequencies shape:", f['frequencies'].shape)
            print("First 5 frequencies:", f['frequencies'][:5])
        if 'metadata' in f:
            print("Metadata:")
            for k, v in f['metadata'].attrs.items():
                print(f"  {k}: {v}")
        # Show a sample visibility value
        if 'visibilities' in f:
            print("Sample visibility [0,0,0]:", f['visibilities'][0,0,0])
    print("\n--- End of file ---\n")

def main():
    parser = argparse.ArgumentParser(
        description="FX Correlator: Simulate, process, and view radio telescope data.\n\n"
        "How it works: The FX correlator simulates signals from multiple antennas, channelises them with FFT, cross-correlates all pairs, integrates over time, and saves the results in HDF5 format. No hardware needed!",
        formatter_class=argparse.RawTextHelpFormatter)
    subparsers = parser.add_subparsers(dest='command', required=True, help='Sub-commands')

    # Run pipeline
    run_parser = subparsers.add_parser('run', help='Run the correlator simulation and save output')
    run_parser.add_argument('--num_antennas', type=int, default=4, help='Number of antennas (default: 4)')
    run_parser.add_argument('--sample_rate', type=float, default=1e6, help='Sample rate in Hz (default: 1e6)')
    run_parser.add_argument('--frame_size', type=int, default=4096, help='Samples per frame (default: 4096)')
    run_parser.add_argument('--fft_size', type=int, default=4096, help='FFT size (default: 4096)')
    run_parser.add_argument('--n_integrate', type=int, default=10, help='Frames to integrate (default: 10)')
    run_parser.add_argument('--frequencies', type=float, nargs='+', default=[1e5, 2e5, 3e5, 4e5], help='Antenna frequencies in Hz (default: 1e5 2e5 3e5 4e5)')
    run_parser.add_argument('--output', type=str, default='vis_example.h5', help='Output filename (default: vis_example.h5)')
    run_parser.set_defaults(func=run_pipeline)

    # View output
    view_parser = subparsers.add_parser('view', help='View/print contents of an HDF5 output file')
    view_parser.add_argument('file', type=str, help='Path to HDF5 file (e.g., output/vis_example.h5)')
    view_parser.set_defaults(func=view_output)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main() 