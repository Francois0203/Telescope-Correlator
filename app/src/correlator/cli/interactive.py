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

Type 'help' or '?' to list commands.
Type 'exit' or 'quit' to exit the shell.
"""
    prompt = "correlator> "
    
    def __init__(self):
        super().__init__()
        self.config = CorrelatorConfig()
        self.last_run_successful = False
    
    def do_run(self, arg):
        """Run the correlator with specified parameters.
        
        Usage: run [OPTIONS]
        
        Options:
            --n-ants N             Number of antennas (default: 4)
            --n-channels N         Number of frequency channels (default: 128)
            --sim-duration SEC     Simulation duration in seconds (default: 1.0)
            --output-dir PATH      Output directory (default: /app/outputs)
            --mode MODE            Data source mode: simulated or file (default: simulated)
            
        Examples:
            run
            run --n-ants 4 --n-channels 256 --sim-duration 2.0
            run --mode simulated --n-ants 8 --sim-duration 0.5
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
                    run_config.n_ants = int(args[i + 1])
                    i += 2
                elif args[i] == '--n-channels' and i + 1 < len(args):
                    run_config.n_channels = int(args[i + 1])
                    i += 2
                elif args[i] == '--sim-duration' and i + 1 < len(args):
                    run_config.sim_duration = float(args[i + 1])
                    i += 2
                elif args[i] == '--output-dir' and i + 1 < len(args):
                    run_config.output_dir = args[i + 1]
                    i += 2
                elif args[i] == '--mode' and i + 1 < len(args):
                    run_config.mode = args[i + 1]
                    i += 2
                else:
                    print(f"Unknown argument: {args[i]}")
                    return
            
            # Run correlator
            print(f"\n{'='*60}")
            print("STARTING CORRELATOR RUN")
            print(f"{'='*60}\n")
            
            exit_code = run_correlator(run_config)
            
            if exit_code == 0:
                self.last_run_successful = True
                print(f"\n{'='*60}")
                print("✓ CORRELATOR RUN COMPLETED SUCCESSFULLY")
                print(f"{'='*60}\n")
            else:
                self.last_run_successful = False
                print(f"\n{'='*60}")
                print("✗ CORRELATOR RUN FAILED")
                print(f"{'='*60}\n")
                
        except Exception as e:
            print(f"Error running correlator: {e}")
            self.last_run_successful = False
    
    def do_config(self, arg):
        """Show or modify configuration settings.
        
        Usage: 
            config              - Show current configuration
            config set KEY VALUE - Set a configuration value
            
        Examples:
            config
            config set n_ants 8
            config set n_channels 256
        """
        args = shlex.split(arg) if arg else []
        
        if not args:
            # Show current config
            print("\n" + "="*60)
            print("CURRENT CONFIGURATION")
            print("="*60)
            print(f"Antennas:          {self.config.n_ants}")
            print(f"Channels:          {self.config.n_channels}")
            print(f"Sample Rate:       {self.config.sample_rate} Hz")
            print(f"Center Frequency:  {self.config.center_freq / 1e6} MHz")
            print(f"Mode:              {self.config.mode}")
            print(f"Output Directory:  {self.config.output_dir}")
            print(f"Sim Duration:      {self.config.sim_duration} s")
            print(f"Window Type:       {self.config.window_type}")
            print("="*60 + "\n")
        elif args[0] == "set" and len(args) >= 3:
            key = args[1]
            value = args[2]
            try:
                if hasattr(self.config, key):
                    # Try to convert value to correct type
                    current_value = getattr(self.config, key)
                    if isinstance(current_value, int):
                        setattr(self.config, key, int(value))
                    elif isinstance(current_value, float):
                        setattr(self.config, key, float(value))
                    else:
                        setattr(self.config, key, value)
                    print(f"✓ Set {key} = {value}")
                else:
                    print(f"✗ Unknown configuration key: {key}")
            except ValueError as e:
                print(f"✗ Invalid value for {key}: {value}")
        else:
            print("Usage: config [set KEY VALUE]")
    
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
    
    def do_clear(self, arg):
        """Clear the terminal screen."""
        import os
        os.system('cls' if os.name == 'nt' else 'clear')
    
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
