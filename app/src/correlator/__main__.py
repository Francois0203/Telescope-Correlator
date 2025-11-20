"""Small CLI entrypoint for the correlator app.

Example:
    python -m correlator --help
"""
from __future__ import annotations

import argparse
import sys
import numpy as np
from .core import Correlator


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="correlator")
    parser.add_argument("--example", action="store_true", help="Run a tiny example")
    args = parser.parse_args(argv)

    if args.example:
        x = np.sin(np.linspace(0, 2 * np.pi, 128))
        y = np.roll(x, 5)
        c = Correlator()
        corr = c.correlate(x, y, mode="same")
        print(f"corr peak index: {np.argmax(corr)}")
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
