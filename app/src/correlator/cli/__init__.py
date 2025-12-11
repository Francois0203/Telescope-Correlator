"""CLI module for telescope correlator."""
from correlator.cli.commands import main
from correlator.cli.interactive import start_interactive_shell
from correlator.cli.runner import run_correlator

__all__ = ["main", "start_interactive_shell", "run_correlator"]
