"""Development Mode CLI

Interactive command-line interface for development, testing, and learning.
Supports simulated data generation, algorithm testing, and visualization.

This mode is for DEVELOPMENT ONLY - uses simulated telescope signals.
"""
import cmd
import sys
import os
import subprocess
from pathlib import Path
import shlex
import numpy as np

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
          --output-format FMT   Output format: npy, hdf5, fits (default: npy)
          
        EXAMPLES:
          run
          run --n-ants 8 --n-channels 512
          run --sim-duration 5.0 --sim-snr 15
          run --output-format fits
          run --sim-realtime
          
        This command runs a simulated telescope correlation for testing purposes.
        """
        try:
            args = shlex.split(arg) if arg else []
            
            # Create run config based on current config
            run_config = CorrelatorConfig()
            run_config.operation_mode = "development"
            run_config.mode = "simulated"
            
            # Copy from current config
            run_config.n_ants = self.config.n_ants
            run_config.n_channels = self.config.n_channels
            run_config.sim_duration = self.config.sim_duration
            run_config.sim_snr = self.config.sim_snr
            run_config.integration_time = self.config.integration_time
            run_config.window_type = self.config.window_type
            run_config.output_format = self.config.output_format
            
            # Parse arguments
            i = 0
            while i < len(args):
                if args[i] == '--n-ants' and i + 1 < len(args):
                    run_config.n_ants = int(args[i + 1])
                    i += 2
                elif args[i] == '--n-channels' and i + 1 < len(args):
                    run_config.n_channels = int(args[i + 1])
                    i += 2
                elif args[i] == '--sim-duration' and i + 1 < len(args):
                    run_config.sim_duration = float(args[i + 1])
                    i += 2
                elif args[i] == '--sim-snr' and i + 1 < len(args):
                    run_config.sim_snr = float(args[i + 1])
                    i += 2
                elif args[i] == '--integration-time' and i + 1 < len(args):
                    run_config.integration_time = float(args[i + 1])
                    i += 2
                elif args[i] == '--window-type' and i + 1 < len(args):
                    run_config.window_type = args[i + 1]
                    i += 2
                elif args[i] == '--output-format' and i + 1 < len(args):
                    fmt = args[i + 1].lower()
                    if fmt in ['npy', 'hdf5', 'h5', 'fits']:
                        run_config.output_format = fmt
                    else:
                        print(f"❌ Invalid output format: {fmt} (use: npy, hdf5, fits)")
                        return
                    i += 2
                elif args[i] == '--sim-realtime':
                    run_config.sim_realtime = True
                    i += 1
                else:
                    print(f"❌ Unknown option: {args[i]}")
                    return
            
            print("\\n🔬 RUNNING DEVELOPMENT SIMULATION")
            print("="*50)
            print(f"   Antennas: {run_config.n_ants}")
            print(f"   Channels: {run_config.n_channels}")
            print(f"   Duration: {run_config.sim_duration}s")
            print(f"   SNR: {run_config.sim_snr} dB")
            print(f"   Integration: {run_config.integration_time}s")
            print(f"   Output format: {run_config.output_format}")
            print(f"   Output dir: {run_config.output_dir}")
            print(f"="*50)
            
            exit_code = run_correlator(run_config)
            
            if exit_code == 0:
                self.last_run_successful = True
                print(f"\\n✅ SIMULATION COMPLETED SUCCESSFULLY!")
                print(f"   Results saved to: {run_config.output_dir}")
                print(f"   Use 'list' to see files, 'visualize' to plot")
            else:
                self.last_run_successful = False
                print(f"\\n❌ SIMULATION FAILED")
                
        except Exception as e:
            print(f"\\n❌ ERROR: {e}")
            self.last_run_successful = False
    
    def do_config(self, arg):
        """View and modify development configuration.
        
        USAGE:
          config              Show all settings
          config set KEY VALUE  Change a setting
        """
        args = shlex.split(arg) if arg else []
        
        if not args:
            print(f"\\n⚙️  DEVELOPMENT CONFIGURATION")
            print(f"{'='*60}")
            print(f"{'Setting':<20} {'Value':<15} {'Description'}")
            print(f"{'='*60}")
            print(f"{'n_ants':<20} {self.config.n_ants:<15} Number of antennas")
            print(f"{'n_channels':<20} {self.config.n_channels:<15} Frequency channels")
            print(f"{'sim_duration':<20} {self.config.sim_duration:<15} Simulation time (s)")
            print(f"{'sim_snr':<20} {self.config.sim_snr:<15} Signal SNR (dB)")
            print(f"{'integration_time':<20} {self.config.integration_time:<15} Integration time (s)")
            print(f"{'window_type':<20} {self.config.window_type:<15} Window function")
            print(f"{'output_format':<20} {self.config.output_format:<15} Output format")
            print(f"{'output_dir':<20} {str(self.config.output_dir):<15} Output directory")
            print(f"{'='*60}")
            print(f"💡 Use 'config set <key> <value>' to change\\n")
            
        elif args[0] == "set" and len(args) >= 3:
            key = args[1]
            value = args[2]
            
            if not hasattr(self.config, key):
                print(f"❌ Unknown setting: {key}")
                return
            
            try:
                current_value = getattr(self.config, key)
                
                if isinstance(current_value, int):
                    new_value = int(value)
                elif isinstance(current_value, float):
                    new_value = float(value)
                else:
                    new_value = value
                
                setattr(self.config, key, new_value)
                print(f"✅ Set {key} = {new_value}")
                
            except ValueError as e:
                print(f"❌ Invalid value for {key}: {value}")
        else:
            print("❌ Usage: config [set KEY VALUE]")
    
    def do_set(self, arg):
        """Quick set command. Usage: set KEY VALUE"""
        if arg:
            self.do_config(f"set {arg}")
        else:
            print("❌ Usage: set KEY VALUE")
    
    def do_list(self, arg):
        """Show output files."""
        output_path = Path(self.config.output_dir)
        if not output_path.exists():
            print(f"❌ Output directory does not exist: {output_path}")
            return
        
        files = sorted(output_path.glob("*"))
        if not files:
            print(f"📁 No files in {output_path.name}/")
            return
        
        print(f"\\n📁 Files in {output_path.name}/:")
        print(f"{'='*70}")
        print(f"{'Filename':<35} {'Size':<10} {'Type'}")
        print(f"{'='*70}")
        
        for f in files:
            if f.is_file():
                size_kb = f.stat().st_size / 1024
                file_type = 'Visibility' if f.suffix == '.npy' else f.suffix[1:].upper()
                print(f"{f.name:<35} {size_kb:>8.1f} KB {file_type:<15}")
        
        print(f"{'='*70}\\n")
    
    def do_visualize(self, arg):
        """Visualize simulation results.
        
        USAGE: visualize [FILENAME]
        
        Interactive file selection if no filename provided.
        """
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        
        output_path = Path(self.config.output_dir)
        if not output_path.exists():
            print(f"❌ Output directory does not exist")
            print("   Run 'run' first to generate data")
            return
        
        vis_files = sorted(output_path.glob("visibility_*.npy"))
        if not vis_files:
            print("❌ No visibility files found")
            print("   Run 'run' first to generate data")
            return
        
        # Select file
        if arg:
            filename = arg if arg.endswith('.npy') else f"{arg}.npy"
            vis_file = output_path / filename
            if not vis_file.exists():
                print(f"❌ File not found: {filename}")
                return
        else:
            print(f"\\n📁 Available files:")
            for i, f in enumerate(vis_files, 1):
                print(f"  {i}. {f.name}")
            
            try:
                choice = input(f"\\nChoose file (1-{len(vis_files)}): ").strip()
                idx = int(choice) - 1
                if 0 <= idx < len(vis_files):
                    vis_file = vis_files[idx]
                else:
                    print("❌ Invalid choice")
                    return
            except (ValueError, KeyboardInterrupt):
                print("\\nCancelled")
                return
        
        # Load and plot
        try:
            print(f"\\n📊 Loading {vis_file.name}...")
            vis = np.load(vis_file)
            print(f"   Shape: {vis.shape}")
            
            # Create plots
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
            
            ax1.imshow(np.abs(vis), aspect='auto', cmap='viridis')
            ax1.set_title('Visibility Amplitude')
            ax1.set_xlabel('Channel')
            ax1.set_ylabel('Baseline')
            
            ax2.imshow(np.angle(vis), aspect='auto', cmap='twilight')
            ax2.set_title('Visibility Phase')
            ax2.set_xlabel('Channel')
            ax2.set_ylabel('Baseline')
            
            plot_file = output_path / f"{vis_file.stem}_plot.png"
            plt.tight_layout()
            plt.savefig(plot_file, dpi=150)
            plt.close()
            
            print(f"✅ Plot saved: {plot_file.name}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
    
    def do_test(self, arg):
        """Run validation tests.
        
        USAGE: test [TEST_SUITE]
        
        TEST SUITES:
          all           Run all tests (default)
          unit          Unit tests only
          integration   Integration tests only
          
        EXAMPLES:
          test
          test unit
          test integration
        """
        print("\\n🧪 Running tests...")
        
        test_suite = arg.strip() if arg else "all"
        
        try:
            if test_suite == "unit":
                print("   Running unit tests...")
                result = subprocess.run(
                    ["pytest", "/workspace/tests_harness/unit/", "-v"],
                    capture_output=True, text=True
                )
            elif test_suite == "integration":
                print("   Running integration tests...")
                result = subprocess.run(
                    ["pytest", "/workspace/tests_harness/integration/", "-v"],
                    capture_output=True, text=True
                )
            else:
                print("   Running all tests...")
                result = subprocess.run(
                    ["pytest", "/workspace/tests_harness/", "-v"],
                    capture_output=True, text=True
                )
            
            print(result.stdout)
            if result.stderr:
                print(result.stderr)
            
            if result.returncode == 0:
                print("\\n✅ Tests passed!")
            else:
                print("\\n❌ Some tests failed")
                
        except FileNotFoundError:
            print("❌ pytest not found. Install with: pip install pytest")
        except Exception as e:
            print(f"❌ Error running tests: {e}")
    
    def do_status(self, arg):
        """Show system status."""
        print("\\n📊 SYSTEM STATUS")
        print("="*50)
        print(f"Mode: Development")
        print(f"Last run: {'Success ✅' if self.last_run_successful else 'Not run or failed ❌'}")
        print(f"Output directory: {self.config.output_dir}")
        print(f"="*50)
        print()
    
    def do_clear(self, arg):
        """Clear the terminal screen."""
        os.system('cls' if os.name == 'nt' else 'clear')
    
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
            print("set              Quick set: set KEY VALUE")
            print("list             Show output files")
            print("visualize        Plot results")
            print("test             Run validation tests")
            print("status           System status")
            print("clear            Clear terminal screen")
            print("")
            print("help             This help")
            print("exit             Exit CLI")
            print("")
            print("💡 Type 'help <command>' for detailed information")
        else:
            super().do_help(arg)
    
    def emptyline(self):
        """Do nothing on empty line."""
        pass
    
    def default(self, line):
        """Handle unknown commands."""
        print(f"❌ Unknown command: '{line}'. Type 'help' for available commands.")
    
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
