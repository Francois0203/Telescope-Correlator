"""Interactive CLI shell for telescope correlator."""
import cmd
import sys
from pathlib import Path
from typing import Optional
import shlex

from correlator.config import CorrelatorConfig
from correlator.cli.runner import run_correlator


class CorrelatorShell(cmd.Cmd):
    """Interactive shell for telescope correlator operations."""
    
    intro = """
╔══════════════════════════════════════════════════════════════╗
║         Telescope Correlator - Interactive CLI               ║
║                    FX Architecture                           ║
╚══════════════════════════════════════════════════════════════╝

Welcome! This CLI helps you run radio telescope correlation simulations.

QUICK START GUIDE:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  run                    → Run correlator with current settings
  run --n-ants 8         → Run with 8 antennas
  set n_ants 6           → Change number of antennas to 6
  config                 → View all current settings
  list                   → Show output files
  visualize              → Create plots (choose file interactively)
  visualize visibility_0001 → Plot specific file
  status                 → Show system info and last run status
  help                   → Show detailed help for all commands

TIPS:
• Type 'help <command>' for detailed info about any command
• Parameters are remembered between runs
• Output files are saved to /app/outputs (mounted to dev_workspace/outputs)
• Use 'exit' or Ctrl+D to quit

Type 'help' for full command reference.
"""
    prompt = "correlator> "
    
    def __init__(self):
        super().__init__()
        self.config = CorrelatorConfig()
        self.last_run_successful = False
    
    def do_run(self, arg):
        """Run the correlator simulation with current or specified parameters.
        
        USAGE: run [OPTIONS]
        
        COMMON OPTIONS:
          --n-ants N          Number of antennas (2-16, default: 4)
          --n-channels N      Frequency channels (32-1024, default: 64)  
          --sim-duration SEC  Simulation time in seconds (0.1-60, default: 1.0)
          --sim-snr DB        Signal-to-noise ratio (0-50 dB, default: 20)
          
        ADVANCED OPTIONS:
          --array-radius M    Antenna array radius in meters (default: 10.0)
          --sample-rate HZ    Sample rate in Hz (default: 1024.0)
          --center-freq HZ    Center frequency in Hz (default: 1.42e9)
          --integration-time S Integration time per output (default: 1.0)
          --output-dir PATH   Where to save results (default: /app/outputs)
          --mode MODE         Data source: 'simulated' or 'file' (default: simulated)
          
        EXAMPLES:
          run                           # Use current/default settings
          run --n-ants 8                # 8 antennas, other defaults
          run --n-ants 4 --n-channels 256 --sim-duration 2.0
          run --sim-snr 10 --sim-duration 0.5
          
        NOTES:
        • Results are saved as .npy files in the output directory
        • A config.yaml file is also saved for reproducibility
        • Use 'list' to see output files, 'visualize' to plot them
        """
        try:
            # Parse arguments
            args = shlex.split(arg) if arg else []
            
            # Create a new config for this run
            run_config = CorrelatorConfig()
            
            # Parse simple arguments
            i = 0
            while i < len(args):
                if args[i] == '--n-ants' and i + 1 < len(args):
                    try:
                        val = int(args[i + 1])
                        if 2 <= val <= 16:
                            run_config.n_ants = val
                            print(f"✓ Set antennas: {val}")
                        else:
                            print(f"✗ Antennas must be 2-16, got {val}")
                            return
                    except ValueError:
                        print(f"✗ Invalid number for antennas: {args[i + 1]}")
                        return
                    i += 2
                elif args[i] == '--n-channels' and i + 1 < len(args):
                    try:
                        val = int(args[i + 1])
                        if 32 <= val <= 1024:
                            run_config.n_channels = val
                            print(f"✓ Set channels: {val}")
                        else:
                            print(f"✗ Channels must be 32-1024, got {val}")
                            return
                    except ValueError:
                        print(f"✗ Invalid number for channels: {args[i + 1]}")
                        return
                    i += 2
                elif args[i] == '--sim-duration' and i + 1 < len(args):
                    try:
                        val = float(args[i + 1])
                        if 0.1 <= val <= 60:
                            run_config.sim_duration = val
                            print(f"✓ Set duration: {val}s")
                        else:
                            print(f"✗ Duration must be 0.1-60s, got {val}")
                            return
                    except ValueError:
                        print(f"✗ Invalid number for duration: {args[i + 1]}")
                        return
                    i += 2
                elif args[i] == '--sim-snr' and i + 1 < len(args):
                    try:
                        val = float(args[i + 1])
                        if 0 <= val <= 50:
                            run_config.sim_snr = val
                            print(f"✓ Set SNR: {val} dB")
                        else:
                            print(f"✗ SNR must be 0-50 dB, got {val}")
                            return
                    except ValueError:
                        print(f"✗ Invalid number for SNR: {args[i + 1]}")
                        return
                    i += 2
                elif args[i] == '--output-dir' and i + 1 < len(args):
                    run_config.output_dir = args[i + 1]
                    print(f"✓ Set output dir: {args[i + 1]}")
                    i += 2
                elif args[i] == '--mode' and i + 1 < len(args):
                    if args[i + 1] in ['simulated', 'file']:
                        run_config.mode = args[i + 1]
                        print(f"✓ Set mode: {args[i + 1]}")
                    else:
                        print(f"✗ Mode must be 'simulated' or 'file', got {args[i + 1]}")
                        return
                    i += 2
                elif args[i] == '--array-radius' and i + 1 < len(args):
                    try:
                        val = float(args[i + 1])
                        run_config.ant_radius = val
                        print(f"✓ Set array radius: {val}m")
                    except ValueError:
                        print(f"✗ Invalid number for array radius: {args[i + 1]}")
                        return
                    i += 2
                elif args[i] == '--sample-rate' and i + 1 < len(args):
                    try:
                        val = float(args[i + 1])
                        run_config.sample_rate = val
                        print(f"✓ Set sample rate: {val} Hz")
                    except ValueError:
                        print(f"✗ Invalid number for sample rate: {args[i + 1]}")
                        return
                    i += 2
                elif args[i] == '--center-freq' and i + 1 < len(args):
                    try:
                        val = float(args[i + 1])
                        run_config.center_freq = val
                        print(f"✓ Set center freq: {val} Hz")
                    except ValueError:
                        print(f"✗ Invalid number for center freq: {args[i + 1]}")
                        return
                    i += 2
                elif args[i] == '--integration-time' and i + 1 < len(args):
                    try:
                        val = float(args[i + 1])
                        run_config.integration_time = val
                        print(f"✓ Set integration time: {val}s")
                    except ValueError:
                        print(f"✗ Invalid number for integration time: {args[i + 1]}")
                        return
                    i += 2
                else:
                    print(f"✗ Unknown option: {args[i]}")
                    print("Type 'help run' for available options")
                    return
            
            # Show what will be run
            print(f"\n🚀 STARTING CORRELATION RUN")
            print(f"   Antennas: {run_config.n_ants}")
            print(f"   Channels: {run_config.n_channels}")
            print(f"   Duration: {run_config.sim_duration}s")
            print(f"   SNR: {run_config.sim_snr} dB")
            print(f"   Output: {run_config.output_dir}")
            print(f"   Mode: {run_config.mode}")
            print(f"{'='*50}\n")
            
            exit_code = run_correlator(run_config)
            
            if exit_code == 0:
                self.last_run_successful = True
                print(f"\n✅ CORRELATION COMPLETED SUCCESSFULLY!")
                print(f"   Results saved to: {run_config.output_dir}")
                print(f"   Use 'list' to see files, 'visualize' to plot")
            else:
                self.last_run_successful = False
                print(f"\n❌ CORRELATION FAILED")
                print(f"   Check parameters and try again")
                
        except Exception as e:
            print(f"❌ ERROR: {e}")
            print("Type 'help run' for usage information")
                
        except Exception as e:
            print(f"Error running correlator: {e}")
            self.last_run_successful = False
    
    def do_config(self, arg):
        """View and modify configuration settings.
        
        USAGE:
          config                    # Show all current settings
          config set KEY VALUE      # Change a setting
          
        COMMON SETTINGS:
          n_ants          - Number of antennas (2-16)
          n_channels      - Frequency channels (32-1024)
          sim_duration    - Simulation time in seconds (0.1-60)
          sim_snr         - Signal-to-noise ratio in dB (0-50)
          output_dir      - Where results are saved
          
        ADVANCED SETTINGS:
          sample_rate     - Sample rate in Hz
          center_freq     - Center frequency in Hz
          window_type     - Window function (rectangular/hanning/hamming/blackman)
          integration_time - Integration time per output in seconds
          
        EXAMPLES:
          config                    # Show current settings
          config set n_ants 8       # Set 8 antennas
          config set sim_duration 2.0  # Set 2 second simulation
          config set n_channels 512    # Set 512 channels
          
        NOTES:
        • Changes are remembered for future runs
        • Use 'run' to execute with current settings
        • Type 'help config' for this detailed help
        """
        args = shlex.split(arg) if arg else []
        
        if not args:
            # Show current config with descriptions
            print(f"\n⚙️  CURRENT CONFIGURATION SETTINGS")
            print(f"{'='*60}")
            print(f"{'Setting':<20} {'Value':<15} {'Description'}")
            print(f"{'='*60}")
            print(f"{'n_ants':<20} {self.config.n_ants:<15} Number of antennas")
            print(f"{'n_channels':<20} {self.config.n_channels:<15} Frequency channels")
            print(f"{'sim_duration':<20} {self.config.sim_duration:<15} Simulation time (s)")
            print(f"{'sim_snr':<20} {self.config.sim_snr:<15} Signal SNR (dB)")
            print(f"{'sample_rate':<20} {self.config.sample_rate:<15} Sample rate (Hz)")
            print(f"{'center_freq':<20} {self.config.center_freq/1e6:<14.1f} MHz {'Center frequency'}")
            print(f"{'window_type':<20} {self.config.window_type:<15} Window function")
            print(f"{'integration_time':<20} {self.config.integration_time:<15} Integration time (s)")
            print(f"{'mode':<20} {self.config.mode:<15} Data source mode")
            print(f"{'output_dir':<20} {str(self.config.output_dir):<15} Output directory")
            print(f"{'='*60}")
            print(f"💡 Tip: Use 'config set <key> <value>' to change settings")
            print(f"💡 Tip: Use 'run' to execute with these settings\n")
            
        elif args[0] == "set" and len(args) >= 3:
            key = args[1]
            value = args[2]
            
            # Validate key exists
            if not hasattr(self.config, key):
                print(f"❌ Unknown setting: {key}")
                print("   Type 'config' to see available settings")
                return
            
            try:
                # Get current value to determine type
                current_value = getattr(self.config, key)
                
                # Convert value to correct type
                if isinstance(current_value, int):
                    new_value = int(value)
                    # Add some validation for common settings
                    if key == 'n_ants' and not (2 <= new_value <= 16):
                        print(f"❌ n_ants must be 2-16, got {new_value}")
                        return
                    elif key == 'n_channels' and not (32 <= new_value <= 1024):
                        print(f"❌ n_channels must be 32-1024, got {new_value}")
                        return
                elif isinstance(current_value, float):
                    new_value = float(value)
                    if key == 'sim_duration' and not (0.1 <= new_value <= 60):
                        print(f"❌ sim_duration must be 0.1-60, got {new_value}")
                        return
                    elif key == 'sim_snr' and not (0 <= new_value <= 50):
                        print(f"❌ sim_snr must be 0-50, got {new_value}")
                        return
                else:
                    new_value = value
                    if key == 'window_type' and value not in ['rectangular', 'hanning', 'hamming', 'blackman']:
                        print(f"❌ window_type must be: rectangular, hanning, hamming, or blackman")
                        return
                    elif key == 'mode' and value not in ['simulated', 'file']:
                        print(f"❌ mode must be: simulated or file")
                        return
                
                setattr(self.config, key, new_value)
                print(f"✅ Set {key} = {new_value}")
                
            except ValueError as e:
                print(f"❌ Invalid value for {key}: {value} ({e})")
                
        else:
            print("❌ Usage: config [set KEY VALUE]")
            print("   Type 'config' to see current settings")
            print("   Type 'help config' for detailed help")
    
    def do_status(self, arg):
        """Show system status and last run information."""
        print("\n" + "="*60)
        print("SYSTEM STATUS")
        print("="*60)
        print(f"CLI Version:       1.0.0")
        print(f"Python:            {sys.version.split()[0]}")
        print(f"Working Directory: {Path.cwd()}")
        print(f"Last Run Status:   {'✓ Success' if self.last_run_successful else '✗ Not run or failed'}")
        print(f"Output Directory:  {self.config.output_dir}")
        
        # Check if output directory exists and has files
        output_path = Path(self.config.output_dir)
        if output_path.exists():
            npy_files = list(output_path.glob("*.npy"))
            config_files = list(output_path.glob("*.yaml"))
            print(f"Output Files:      {len(npy_files)} visibility files, {len(config_files)} config files")
        else:
            print(f"Output Files:      Directory not found")
        print("="*60 + "\n")
    
    def do_list(self, arg):
        """List files in the output directory.
        
        USAGE: list [PATTERN]
        
        Shows all files in the output directory with sizes and types.
        Use patterns to filter (supports wildcards).
        
        EXAMPLES:
          list              # Show all files
          list *.npy        # Show only visibility files
          list visibility_* # Show visibility files
          list *.png        # Show plot files
          list config*      # Show config files
          
        FILE TYPES:
          • visibility_*.npy    - Correlation results
          • *_visualization.png - Plot images
          • config.yaml         - Run configuration
        """
        output_path = Path(self.config.output_dir)
        if not output_path.exists():
            print(f"❌ Output directory does not exist: {output_path}")
            print("   Run 'run' first to generate data")
            return
        
        pattern = arg if arg else "*"
        files = sorted(output_path.glob(pattern))
        
        if not files:
            print(f"❌ No files found matching: {pattern}")
            print("   Try 'list' without arguments to see all files")
            return
        
        print(f"\n📁 Files in {output_path.name}/ (matching '{pattern}'):")
        print(f"{'='*70}")
        print(f"{'Filename':<35} {'Size':>10} {'Type':<15}")
        print(f"{'='*70}")
        
        total_size = 0
        file_counts = {'npy': 0, 'png': 0, 'yaml': 0, 'other': 0}
        
        for f in files:
            if f.is_file():
                size_kb = f.stat().st_size / 1024
                total_size += f.stat().st_size
                
                # Determine file type
                if f.suffix == '.npy':
                    file_type = 'Visibility'
                    file_counts['npy'] += 1
                elif f.suffix == '.png':
                    file_type = 'Plot'
                    file_counts['png'] += 1
                elif f.suffix == '.yaml':
                    file_type = 'Config'
                    file_counts['yaml'] += 1
                else:
                    file_type = 'Other'
                    file_counts['other'] += 1
                
                print(f"{f.name:<35} {size_kb:>8.1f} KB {file_type:<15}")
        
        print(f"{'='*70}")
        print(f"Total: {len(files)} files, {total_size/1024:.1f} KB")
        if file_counts['npy'] > 0:
            print(f"  • {file_counts['npy']} visibility files (use 'visualize' to plot)")
        if file_counts['png'] > 0:
            print(f"  • {file_counts['png']} plot images")
        if file_counts['yaml'] > 0:
            print(f"  • {file_counts['yaml']} config files")
        print()
    
    def do_visualize(self, arg):
        """Create visualization plots of visibility data.
        
        USAGE: visualize [FILENAME]
        
        If no filename is given, you'll be prompted to choose from available files.
        
        EXAMPLES:
          visualize                    # Interactive file selection
          visualize visibility_0001    # Plot specific file
          visualize visibility_0001.npy # Plot with .npy extension
          
        OUTPUT:
        • Saves amplitude and phase plots as PNG files
        • Plots show frequency vs baseline for each integration
        • Files are saved in the output directory
        """
        import numpy as np
        import matplotlib
        matplotlib.use('Agg')  # Non-interactive backend
        import matplotlib.pyplot as plt
        
        output_path = Path(self.config.output_dir)
        if not output_path.exists():
            print(f"❌ Output directory does not exist: {output_path}")
            print("   Run 'run' first to generate data")
            return
        
        # Get available visibility files
        vis_files = sorted(output_path.glob("visibility_*.npy"))
        if not vis_files:
            print("❌ No visibility files found in output directory")
            print("   Run 'run' first to generate data")
            return
        
        # Determine which file to visualize
        if arg:
            # User specified a file
            filename = arg if arg.endswith('.npy') else f"{arg}.npy"
            vis_file = output_path / filename
            if not vis_file.exists():
                print(f"❌ File not found: {filename}")
                print("Available files:")
                for f in vis_files:
                    print(f"  • {f.name}")
                return
        else:
            # Interactive selection
            print(f"\n📁 Available visibility files in {output_path.name}/:")
            for i, f in enumerate(vis_files, 1):
                size_kb = f.stat().st_size / 1024
                print(f"  {i}. {f.name} ({size_kb:.1f} KB)")
            
            while True:
                try:
                    choice = input(f"\nChoose file (1-{len(vis_files)}) or 'q' to cancel: ").strip()
                    if choice.lower() in ['q', 'quit', 'exit']:
                        print("Cancelled.")
                        return
                    idx = int(choice) - 1
                    if 0 <= idx < len(vis_files):
                        vis_file = vis_files[idx]
                        break
                    else:
                        print(f"❌ Please enter 1-{len(vis_files)}")
                except ValueError:
                    print("❌ Please enter a number or 'q'")
        
        # Load and visualize
        try:
            print(f"\n📊 Loading {vis_file.name}...")
            vis = np.load(vis_file)
            
            print(f"   Shape: {vis.shape} (baselines × channels × integrations)")
            print(f"   Data type: {vis.dtype}")
            
            # Create visualization
            fig, axes = plt.subplots(1, 2, figsize=(12, 5))
            fig.suptitle(f'Visibility Data: {vis_file.name}', fontsize=14)
            
            # For multi-integration data, show first integration
            if vis.ndim == 3:
                vis_plot = vis[:, :, 0]  # First integration
                integration_note = " (first integration)"
            else:
                vis_plot = vis
                integration_note = ""
            
            # Amplitude
            amp = np.abs(vis_plot)
            im1 = axes[0].imshow(amp, aspect='auto', cmap='viridis', origin='lower')
            axes[0].set_title(f'Visibility Amplitude{integration_note}')
            axes[0].set_xlabel('Frequency Channel')
            axes[0].set_ylabel('Baseline Index')
            plt.colorbar(im1, ax=axes[0], label='Amplitude')
            
            # Phase
            phase = np.angle(vis_plot)
            im2 = axes[1].imshow(phase, aspect='auto', cmap='twilight', origin='lower')
            axes[1].set_title(f'Visibility Phase{integration_note}')
            axes[1].set_xlabel('Frequency Channel')
            axes[1].set_ylabel('Baseline Index')
            plt.colorbar(im2, ax=axes[1], label='Phase (rad)')
            
            plt.tight_layout()
            
            # Save visualization
            output_name = vis_file.stem + '_visualization.png'
            output_file = output_path / output_name
            plt.savefig(output_file, dpi=150, bbox_inches='tight')
            plt.close()
            
            print(f"✅ Visualization saved: {output_name}")
            print(f"   Location: {output_path.name}/{output_name}")
            print(f"   Amplitude range: [{amp.min():.2e}, {amp.max():.2e}]")
            print(f"   Phase range: [{phase.min():.2f}, {phase.max():.2f}] rad")
            
        except Exception as e:
            print(f"❌ Error creating visualization: {e}")
            print("   Make sure the file is a valid visibility data file")
    
    def do_set(self, arg):
        """Quickly set a configuration parameter.
        
        USAGE: set KEY VALUE
        
        This is a shortcut for 'config set KEY VALUE'. Changes are remembered
        for future runs. Use 'config' to see all current settings.
        
        COMMON PARAMETERS:
          n_ants        - Number of antennas (2-16)
          n_channels    - Frequency channels (32-1024)  
          sim_duration  - Simulation time in seconds (0.1-60)
          sim_snr       - Signal SNR in dB (0-50)
          
        EXAMPLES:
          set n_ants 8         # Set 8 antennas
          set n_channels 512   # Set 512 frequency channels
          set sim_duration 2.0 # Set 2 second simulation
          set sim_snr 20       # Set 20 dB SNR
          
        NOTES:
        • Use 'config' to see all available parameters
        • Use 'run' to execute with current settings
        • Changes persist until you exit the CLI
        """
        args = shlex.split(arg) if arg else []
        if len(args) < 2:
            print("❌ Usage: set KEY VALUE")
            print("   Type 'config' to see available parameters")
            print("   Type 'help set' for examples")
            return
        
        key = args[0]
        value = args[1]
        
        # Check if key exists
        if not hasattr(self.config, key):
            print(f"❌ Unknown parameter: {key}")
            print("   Type 'config' to see all available parameters")
            return
        
        try:
            current_value = getattr(self.config, key)
            
            # Convert and validate value
            if isinstance(current_value, int):
                new_value = int(value)
                # Add validation for common parameters
                if key == 'n_ants' and not (2 <= new_value <= 16):
                    print(f"❌ n_ants must be 2-16 antennas, got {new_value}")
                    return
                elif key == 'n_channels' and not (32 <= new_value <= 1024):
                    print(f"❌ n_channels must be 32-1024, got {new_value}")
                    return
            elif isinstance(current_value, float):
                new_value = float(value)
                if key == 'sim_duration' and not (0.1 <= new_value <= 60):
                    print(f"❌ sim_duration must be 0.1-60 seconds, got {new_value}")
                    return
                elif key == 'sim_snr' and not (0 <= new_value <= 50):
                    print(f"❌ sim_snr must be 0-50 dB, got {new_value}")
                    return
            else:
                new_value = value
            
            setattr(self.config, key, new_value)
            print(f"✅ Set {key} = {new_value}")
            
        except ValueError as e:
            print(f"❌ Invalid value for {key}: {value}")
            print(f"   Expected type: {type(current_value).__name__}")
    
    def do_clear(self, arg):
        """Clear the terminal screen."""
        import os
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def do_help(self, arg):
        """Show help for commands.
        
        USAGE: help [COMMAND]
        
        Without arguments, shows all available commands.
        With a command name, shows detailed help for that command.
        
        EXAMPLES:
          help          # Show all commands
          help run      # Show detailed help for 'run'
          help config   # Show detailed help for 'config'
        """
        if arg:
            # Show help for specific command
            try:
                func = getattr(self, 'do_' + arg)
                if func.__doc__:
                    print(f"\nHelp for '{arg}':")
                    print(f"{'='*50}")
                    print(func.__doc__)
                else:
                    print(f"No detailed help available for '{arg}'")
            except AttributeError:
                print(f"Unknown command: '{arg}'")
        else:
            # Show general help
            print(f"\n🔧 TELESCOPE CORRELATOR COMMANDS")
            print(f"{'='*50}")
            print(f"{'Command':<15} {'Description'}")
            print(f"{'='*50}")
            
            # Core commands
            print(f"{'run':<15} Execute correlation with current settings")
            print(f"{'config':<15} View/modify all configuration settings")
            print(f"{'set':<15} Quickly change a setting")
            print(f"{'list':<15} Show output files")
            print(f"{'visualize':<15} Create plots from visibility data")
            print(f"{'status':<15} Show system status")
            print(f"")
            
            # Utility commands
            print(f"{'help':<15} Show this help (help <cmd> for details)")
            print(f"{'clear':<15} Clear the screen")
            print(f"{'exit':<15} Exit the CLI")
            print(f"")
            
            print(f"💡 TIPS:")
            print(f"   • Type 'help <command>' for detailed usage")
            print(f"   • Use 'run --help' for run options")
            print(f"   • Settings persist until you exit")
            print(f"   • Output files are in dev_workspace/outputs/")
            print(f"")
    
    def do_exit(self, arg):
        """Exit the correlator shell."""
        print("\nExiting Telescope Correlator CLI. Goodbye!\n")
        return True
    
    def do_quit(self, arg):
        """Exit the correlator shell."""
        return self.do_exit(arg)
    
    def do_EOF(self, arg):
        """Handle Ctrl+D (EOF) to exit."""
        print()
        return self.do_exit(arg)
    
    def emptyline(self):
        """Do nothing on empty line (don't repeat last command)."""
        pass
    
    def default(self, line):
        """Handle unknown commands."""
        print(f"Unknown command: '{line}'. Type 'help' for available commands.")


def start_interactive_shell():
    """Start the interactive correlator shell."""
    try:
        CorrelatorShell().cmdloop()
    except KeyboardInterrupt:
        print("\n\nInterrupted. Exiting...\n")
        sys.exit(0)
