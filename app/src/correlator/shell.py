"""Interactive shell for the Telescope Correlator."""
from __future__ import annotations

import cmd
import shlex
import sys
from pathlib import Path

import numpy as np

from correlator.config import Config
from correlator import pipeline

# ── Setting registry ─────────────────────────────────────────────────────────
# key: (description, type, min, max)   min/max = None means no numeric bound
_SETTINGS: dict[str, tuple[str, type, object, object]] = {
    "n_ants":           ("Number of antennas",              int,   2,    64),
    "ant_radius":       ("Array radius (metres)",            float, 1.0,  10_000.0),
    "n_channels":       ("FFT channels — must be power of 2", int, 32,   4096),
    "window":           ("Window function",                  str,   None, None),
    "integration_time": ("Integration time (seconds)",       float, 0.1,  3600.0),
    "sample_rate":      ("Sample rate (Hz)",                 float, 1.0,  1e9),
    "center_freq":      ("Centre frequency (Hz)",            float, 1.0,  1e12),
    "mode":             ("Input mode: simulate or file",     str,   None, None),
    "input_file":       ("Input .npy file  (mode=file)",     str,   None, None),
    "duration":         ("Simulation duration (seconds)",    float, 0.1,  86400.0),
    "snr":              ("Signal-to-noise ratio (dB)",       float, 0.0,  100.0),
    "output_format":    ("Output format: npy / hdf5 / fits", str,   None, None),
    "output_dir":       ("Output directory",                 str,   None, None),
}

_BANNER = """\

Telescope Correlator  —  FX Architecture
=========================================
  run             Run the correlator with current settings
  set KEY VALUE   Change a setting
  config          Show all settings
  list            List output files
  plot [FILE]     Plot visibility amplitude and phase
  help [CMD]      Show help
  quit            Exit
"""


class Shell(cmd.Cmd):
    prompt = "correlator> "
    intro  = _BANNER

    def __init__(self):
        super().__init__()
        self.cfg = Config()

    # ─── run ────────────────────────────────────────────────────────────────
    def do_run(self, _arg):
        """Run the FX correlator with current settings."""
        print()
        try:
            pipeline.run(self.cfg)
        except Exception as exc:
            print(f"Error: {exc}")
        print()

    # ─── set ────────────────────────────────────────────────────────────────
    def do_set(self, arg):
        """Change a setting.

Usage:  set <key> <value>

Examples:
  set n_ants 8
  set duration 30.0
  set mode file
  set input_file /workspace/inputs/data.npy
  set output_format hdf5
  set window hamming

Type 'config' to see all settings and their current values."""
        parts = shlex.split(arg) if arg else []
        if len(parts) != 2:
            print("Usage: set <key> <value>  |  type 'config' to see all keys")
            return

        key, raw = parts
        if key not in _SETTINGS:
            print(f"Unknown setting '{key}'.  Type 'config' to see valid keys.")
            return

        desc, typ, lo, hi = _SETTINGS[key]
        try:
            value = typ(raw)
        except (ValueError, TypeError):
            print(f"'{raw}' is not a valid {typ.__name__} for '{key}'")
            return

        if lo is not None and value < lo:
            print(f"{key} must be >= {lo}")
            return
        if hi is not None and value > hi:
            print(f"{key} must be <= {hi}")
            return

        if key == "n_channels":
            v = int(value)
            if v < 2 or (v & (v - 1)) != 0:
                print("n_channels must be a power of 2  (e.g. 64, 128, 256, 512, 1024)")
                return

        if key == "window" and value not in ("rectangular", "hanning", "hamming", "blackman"):
            print("window must be: rectangular, hanning, hamming, or blackman")
            return

        if key == "mode" and value not in ("simulate", "file"):
            print("mode must be: simulate  or  file")
            return

        if key == "output_format" and value not in ("npy", "hdf5", "fits"):
            print("output_format must be: npy, hdf5, or fits")
            return

        setattr(self.cfg, key, value)
        print(f"  {key} = {value}")

    # ─── config ─────────────────────────────────────────────────────────────
    def do_config(self, _arg):
        """Show all current settings."""
        print()
        print(f"  {'Setting':<20} {'Value':<22} Description")
        print(f"  {'-'*20} {'-'*22} {'-'*35}")
        for key, (desc, *_) in _SETTINGS.items():
            val = getattr(self.cfg, key)
            print(f"  {key:<20} {str(val):<22} {desc}")
        print()

    # ─── list ───────────────────────────────────────────────────────────────
    def do_list(self, _arg):
        """List output files."""
        path = Path(self.cfg.output_dir)
        if not path.exists():
            print("Output directory does not exist yet. Run 'run' first.")
            return
        files = sorted(f for f in path.iterdir() if f.is_file())
        if not files:
            print("Output directory is empty. Run 'run' to generate data.")
            return
        print()
        for f in files:
            kb = f.stat().st_size / 1024
            print(f"  {f.name:<45} {kb:7.1f} KB")
        print()

    # ─── plot ───────────────────────────────────────────────────────────────
    def do_plot(self, arg):
        """Plot a visibility file as amplitude and phase images.

Usage:
  plot                    choose from available files
  plot visibility_0001    plot a specific file (with or without .npy)"""
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
        except ImportError:
            print("matplotlib is not installed.")
            return

        output_path = Path(self.cfg.output_dir)
        vis_files = sorted(output_path.glob("visibility_*.npy"))
        if not vis_files:
            print("No visibility files found. Run 'run' first.")
            return

        if arg:
            name = arg if arg.endswith(".npy") else f"{arg}.npy"
            vis_file = output_path / name
            if not vis_file.exists():
                print(f"File not found: {name}")
                print("Available files:")
                for f in vis_files:
                    print(f"  {f.name}")
                return
        else:
            print()
            for i, f in enumerate(vis_files, 1):
                print(f"  {i:3d}.  {f.name}")
            try:
                choice = input("\nFile number: ").strip()
                vis_file = vis_files[int(choice) - 1]
            except (ValueError, IndexError, KeyboardInterrupt):
                print("Cancelled.")
                return

        vis = np.load(vis_file)
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
        fig.suptitle(vis_file.name, fontsize=12)

        im1 = ax1.imshow(np.abs(vis), aspect="auto", cmap="viridis", origin="lower")
        ax1.set(title="Amplitude", xlabel="Frequency channel", ylabel="Baseline index")
        plt.colorbar(im1, ax=ax1)

        im2 = ax2.imshow(np.angle(vis), aspect="auto", cmap="twilight", origin="lower",
                         vmin=-np.pi, vmax=np.pi)
        ax2.set(title="Phase (radians)", xlabel="Frequency channel", ylabel="Baseline index")
        plt.colorbar(im2, ax=ax2, label="rad")

        plt.tight_layout()
        out = output_path / f"{vis_file.stem}_plot.png"
        plt.savefig(out, dpi=150, bbox_inches="tight")
        plt.close()
        print(f"Saved: {out.name}")

    # ─── help ───────────────────────────────────────────────────────────────
    def do_help(self, arg):
        """Show help.  Usage: help [command]"""
        if arg:
            super().do_help(arg)
        else:
            print("""
Commands
--------
  run              Run the FX correlator with current settings
  set KEY VALUE    Change a setting  (type 'config' to see all keys)
  config           Show all settings and their current values
  list             List files in the output directory
  plot [FILE]      Save amplitude + phase plot of a visibility file
  help [CMD]       Show this help, or help for a specific command
  quit             Exit

Quick start
-----------
  correlator> run                    # run with defaults (4 antennas, 10s simulation)
  correlator> set n_ants 8           # change to 8 antennas
  correlator> set duration 30.0      # 30 second simulation
  correlator> run                    # run again
  correlator> list                   # see what was saved
  correlator> plot                   # visualise a visibility file

Output files land in workspace/outputs/ on the host.
""")

    # ─── clear ──────────────────────────────────────────────────────────────
    def do_clear(self, _arg):
        """Clear the terminal screen."""
        import os
        os.system("cls" if os.name == "nt" else "clear")

    do_cls = do_clear

    # ─── quit / exit / EOF ──────────────────────────────────────────────────
    def do_quit(self, _arg):
        """Exit the correlator."""
        print("Goodbye.")
        return True

    do_exit = do_quit

    def do_EOF(self, _arg):
        print()
        return self.do_quit(_arg)

    def emptyline(self):
        pass

    def default(self, line):
        print(f"Unknown command '{line}'.  Type 'help' to see available commands.")
