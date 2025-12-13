"""Development Mode CLI

Interactive command-line interface for development, testing, and learning.
Supports simulated data generation, algorithm testing, and visualization.

This mode is for DEVELOPMENT ONLY - uses simulated telescope signals.
"""
import cmd
import sys
from pathlib import Path
import shlex

from correlator.config import CorrelatorConfig
from correlator.cli.runner import run_correlator


class DevelopmentCLI(cmd.Cmd):
    """Interactive CLI for development mode."""
    
    intro = """
╔══════════════════════════════════════════════════════════════╗
║      TELESCOPE CORRELATOR - DEVELOPMENT MODE                 ║
║            Simulation & Testing Environment                  ║
╚══════════════════════════════════════════════════════════════╝

🔬 DEVELOPMENT MODE - For testing, learning, and algorithm development

QUICK START:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  run                    → Run simulation with current settings
  run --n-ants 8 --sim-duration 2.0 → Run with parameters
  config                 → View/edit configuration
  visualize              → Plot simulation results
  test                   → Run validation tests
  help                   → Show all commands

📝 NOTE: This mode uses SIMULATED telescope data for safe testing.
         For real telescope operations, use 'correlator prod' instead.

Type 'help' for full command reference.
"""
    prompt = "dev> "
    
    def __init__(self):
        super().__init__()
        self.config = CorrelatorConfig()
        self.config.operation_mode = "development"
        self.config.data_source = "simulated"
        self.last_run_successful = False
    
    def do_run(self, arg):
        """Run correlation simulation.
        
        USAGE: run [OPTIONS]
        
        SIMULATION OPTIONS:
          --n-ants N          Number of antennas (2-16, default: 4)
          --n-channels N      Frequency channels (32-1024, default: 256)
          --sim-duration SEC  Simulation time (0.1-60s, default: 10.0)
          --sim-snr DB        Signal-to-noise ratio (0-50 dB, default: 20)
          --sim-realtime      Simulate real-time streaming delays
          
        PROCESSING OPTIONS:
          --integration-time S  Integration time (default: 1.0s)
          --window-type TYPE    Window function (default: hanning)
          --n-channels N        FFT channels (default: 256)
          
        EXAMPLES:
          run
          run --n-ants 8 --n-channels 512
          run --sim-duration 5.0 --sim-snr 15
          run --sim-realtime
          
        This command runs a simulated telescope correlation for testing purposes.
        """
        # Implementation similar to previous interactive CLI
        print("\\n🔬 Running development simulation...")
        print("   Using simulated telescope data")
        # ... rest of implementation
    
    def do_config(self, arg):
        """View and modify development configuration."""
        # Show dev-specific config
        pass
    
    def do_visualize(self, arg):
        """Visualize simulation results."""
        pass
    
    def do_test(self, arg):
        """Run validation tests.
        
        USAGE: test [TEST_SUITE]
        
        TEST SUITES:
          all           Run all tests (default)
          unit          Unit tests only
          integration   Integration tests only
          pipeline      End-to-end pipeline test
          
        EXAMPLES:
          test
          test unit
          test pipeline
          
        Runs the test suite to validate correlator functionality.
        """
        print("\\n🧪 Running tests...")
        print("   Development mode - full test suite")
        # Run pytest
        pass
    
    def do_generate(self, arg):
        """Generate example data for testing.
        
        USAGE: generate [OPTIONS]
        
        OPTIONS:
          --type TYPE       Data type: simple, complex, rfi (default: simple)
          --duration SEC    Duration in seconds (default: 10.0)
          --output DIR      Output directory (default: workspace/inputs/)
          
        EXAMPLES:
          generate
          generate --type complex --duration 30
          generate --type rfi --output test_data/
          
        Generates simulated telescope data files for testing and development.
        """
        print("\\n📊 Generating example data...")
        pass
    
    def do_help(self, arg):
        """Show help information."""
        if not arg:
            print("\\n🔧 DEVELOPMENT MODE COMMANDS")
            print("="*60)
            print("run              Run simulation")
            print("config           View/edit configuration")
            print("visualize        Plot results")
            print("test             Run validation tests")
            print("generate         Create example data")
            print("list             Show output files")
            print("status           System status")
            print("")
            print("help             This help")
            print("exit             Exit CLI")
            print("")
            print("💡 Type 'help <command>' for detailed information")
        else:
            super().do_help(arg)
    
    def do_exit(self, arg):
        """Exit development CLI."""
        print("\\n👋 Exiting development mode.\\n")
        return True
    
    def do_quit(self, arg):
        """Exit development CLI."""
        return self.do_exit(arg)
    
    def do_EOF(self, arg):
        """Handle Ctrl+D."""
        print()
        return self.do_exit(arg)


def start_development_cli():
    """Start the development mode CLI."""
    try:
        DevelopmentCLI().cmdloop()
    except KeyboardInterrupt:
        print("\\n\\n⚠️  Interrupted. Exiting...\\n")
        sys.exit(0)
