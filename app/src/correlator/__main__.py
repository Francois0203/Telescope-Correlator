"""FX Correlator CLI entrypoint

Run the correlator from the command line:
    python -m correlator --help
    python -m correlator --n-ants 4 --n-channels 256
    python -m correlator --interactive  # Interactive shell mode
"""
from correlator.cli.commands import main


if __name__ == "__main__":
    raise SystemExit(main())
