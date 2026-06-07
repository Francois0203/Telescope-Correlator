"""Telescope Correlator — FX Architecture

Start the interactive shell:
    python -m correlator
"""
import sys
from correlator.shell import Shell


def main():
    try:
        Shell().cmdloop()
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(0)


if __name__ == "__main__":
    main()
