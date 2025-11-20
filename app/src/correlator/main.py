"""Lightweight CLI to run correlator on two input files or simulated data."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
import numpy as np

from .core import Correlator
from . import io as io_mod


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="telescope-correlator")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--simulate", action="store_true", help="Generate simulated signals and correlate them")
    g.add_argument("--inputs", nargs=2, metavar=("INPUT1", "INPUT2"), help="Two input files (.npy or .csv)")
    p.add_argument("--out", default="correlation.npy", help="Output numpy file for correlation result")
    p.add_argument("--sample-rate", type=float, default=1.0, help="Sample rate (Hz)")
    return p.parse_args(argv)


def run(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    correlator = Correlator(sample_rate=args.sample_rate)

    if args.simulate:
        # small synthetic example
        t = np.arange(0, 1.0, 1.0 / 1024)
        x = np.sin(2 * np.pi * 50 * t)
        # y is delayed version
        shift = 10
        y = np.roll(x, shift)
    else:
        a_path, b_path = args.inputs
        x = io_mod.load_signal(a_path)
        y = io_mod.load_signal(b_path)

    corr = correlator.correlate(x, y, mode="full")
    np.save(args.out, corr)
    # print the sample lag of peak
    lag_index = int(np.argmax(np.abs(corr)))
    zero_lag = len(y) - 1
    lag_samples = lag_index - zero_lag
    print(f"peak at lag (samples): {lag_samples}")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
