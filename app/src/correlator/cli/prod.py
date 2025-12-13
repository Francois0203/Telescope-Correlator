"""Production Mode CLI

Command-line interface for production telescope operations.
Handles real telescope data from live streams or recorded files.

This mode is for PRODUCTION USE - processes real astronomical data.
NO SIMULATION FEATURES AVAILABLE.
"""
import cmd
import sys
from pathlib import Path
import shlex
import logging

from correlator.config import CorrelatorConfig
from correlator.streaming import create_stream_source, StreamIterator

logger = logging.getLogger(__name__)


class ProductionCLI(cmd.Cmd):
    """Interactive CLI for production telescope operations."""
    
    intro = """
╔══════════════════════════════════════════════════════════════╗
║      TELESCOPE CORRELATOR - PRODUCTION MODE                  ║
║          Real Telescope Data Processing                      ║
╚══════════════════════════════════════════════════════════════╝

🔭 PRODUCTION MODE - Processing real astronomical observations

QUICK START:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  stream                 → Start live data streaming
  process                → Process recorded data files
  monitor                → View real-time statistics
  calibrate              → Run calibration pipeline
  status                 → System health check
  help                   → Show all commands

DATA SOURCES:
  • Network streaming    - Live data from antennas (TCP/UDP/SPEAD)
  • File processing      - Recorded observations (HDF5/FITS/binary)
  • Batch processing     - Multiple observation files

⚠️  PRODUCTION MODE: No simulation features available.
    All operations process real telescope data.

Type 'help' for full command reference.
"""
    prompt = "prod> "
    
    def __init__(self):
        super().__init__()
        self.config = CorrelatorConfig()
        self.config.operation_mode = "production"
        self.config.enable_monitoring = True
        self.config.enable_logging = True
        self.config.enable_quality_checks = True
        self.stream_source = None
        self.is_streaming = False
        
        # Setup logging
        logging.basicConfig(
            level=getattr(logging, self.config.log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    def do_stream(self, arg):
        """Start live data streaming from telescope.
        
        USAGE: stream [OPTIONS]
        
        CONNECTION OPTIONS:
          --source ADDRESS    Network address (host:port or tcp://host:port)
          --protocol PROTO    Protocol: tcp, udp, spead (default: tcp)
          --timeout SEC       Connection timeout (default: 5.0)
          --buffer-size MB    Buffer size in MB (default: 10)
          
        PROCESSING OPTIONS:
          --integration SEC   Integration time (default: 1.0)
          --n-channels N      FFT channels (must match antenna config)
          --max-time SEC      Maximum processing time (default: unlimited)
          --output-dir DIR    Output directory (default: workspace/outputs/)
          
        EXAMPLES:
          stream --source tcp://10.0.0.1:7148
          stream --source 192.168.1.100:7148 --protocol udp
          stream --source antenna-server:7148 --integration 2.0
          stream --source localhost:7148 --max-time 3600
          
        NOTES:
        • Requires active network connection to telescope antennas
        • Data must be in expected format (interleaved complex float32)
        • Use Ctrl+C to stop streaming gracefully
        • Monitor statistics with 'monitor' command
        
        ⚠️  PRODUCTION FEATURE: Processes real telescope data in real-time.
        """
        args = shlex.split(arg) if arg else []
        
        # Parse arguments
        source_address = None
        protocol = 'tcp'
        timeout = 5.0
        buffer_mb = 10
        integration_time = 1.0
        max_time = None
        
        i = 0
        while i < len(args):
            if args[i] == '--source' and i + 1 < len(args):
                source_address = args[i + 1]
                i += 2
            elif args[i] == '--protocol' and i + 1 < len(args):
                protocol = args[i + 1]
                i += 2
            elif args[i] == '--timeout' and i + 1 < len(args):
                timeout = float(args[i + 1])
                i += 2
            elif args[i] == '--buffer-size' and i + 1 < len(args):
                buffer_mb = float(args[i + 1])
                i += 2
            elif args[i] == '--integration' and i + 1 < len(args):
                integration_time = float(args[i + 1])
                i += 2
            elif args[i] == '--max-time' and i + 1 < len(args):
                max_time = float(args[i + 1])
                i += 2
            else:
                print(f"❌ Unknown option: {args[i]}")
                print("   Type 'help stream' for usage")
                return
        
        if not source_address:
            print("❌ Error: --source ADDRESS required")
            print("   Example: stream --source tcp://10.0.0.1:7148")
            return
        
        # Parse address
        if '://' in source_address:
            proto, addr = source_address.split('://')
            protocol = proto
        else:
            addr = source_address
        
        if ':' in addr:
            host, port = addr.rsplit(':', 1)
            port = int(port)
        else:
            print("❌ Error: Port required (format: host:port)")
            return
        
        print(f"\\n🔭 STARTING LIVE STREAMING")
        print(f"   Protocol: {protocol.upper()}")
        print(f"   Source: {host}:{port}")
        print(f"   Buffer: {buffer_mb} MB")
        print(f"   Integration: {integration_time}s")
        print(f"   Timeout: {timeout}s")
        if max_time:
            print(f"   Max duration: {max_time}s")
        print(f"{'='*50}")
        
        try:
            # Create stream source
            self.stream_source = create_stream_source(
                protocol=protocol,
                host=host,
                port=port,
                buffer_size=int(buffer_mb * 1024 * 1024),
                timeout=timeout,
                expected_n_ants=self.config.n_ants
            )
            
            # Connect
            print(f"\\n📡 Connecting to {host}:{port}...")
            self.stream_source.connect()
            print(f"✅ Connected successfully")
            self.is_streaming = True
            
            # TODO: Implement actual streaming pipeline
            print(f"\\n⚠️  Streaming pipeline not yet implemented")
            print(f"   Connection established and ready")
            print(f"   Use Ctrl+C to disconnect")
            
            # Keep connection alive
            input("\\nPress Enter to stop streaming...")
            
        except ConnectionError as e:
            print(f"\\n❌ Connection failed: {e}")
            logger.error(f"Stream connection error: {e}")
        except KeyboardInterrupt:
            print(f"\\n\\n⚠️  Streaming interrupted by user")
        except Exception as e:
            print(f"\\n❌ Error: {e}")
            logger.error(f"Streaming error: {e}", exc_info=True)
        finally:
            if self.stream_source:
                self.stream_source.disconnect()
                self.is_streaming = False
                print(f"\\n✓ Disconnected from stream")
    
    def do_process(self, arg):
        """Process recorded telescope data files.
        
        USAGE: process [OPTIONS]
        
        INPUT OPTIONS:
          --input-dir DIR     Directory with data files (required)
          --input-file FILE   Single file to process
          --format FORMAT     File format: hdf5, fits, binary (auto-detect)
          --pattern GLOB      File pattern (default: *.hdf5)
          
        PROCESSING OPTIONS:
          --integration SEC   Integration time (default: 1.0)
          --n-channels N      FFT channels
          --output-dir DIR    Output directory (default: workspace/outputs/)
          --calibration FILE  Calibration file to apply
          
        QUALITY CONTROL:
          --enable-rfi        Enable RFI detection
          --quality-checks    Enable data quality validation
          --flag-threshold DB RFI flagging threshold (default: 3.0)
          
        EXAMPLES:
          process --input-dir workspace/inputs/
          process --input-file observation_001.hdf5
          process --input-dir data/ --pattern "obs_*.fits"
          process --input-dir raw/ --calibration cal.yaml --enable-rfi
          
        ⚠️  PRODUCTION FEATURE: Processes real recorded telescope data.
        """
        print("\\n📂 PROCESSING RECORDED DATA")
        print("   Mode: File-based processing")
        print("   ⚠️  Feature under development")
        print("   Use 'stream' for live data or check back in next release")
    
    def do_monitor(self, arg):
        """Display real-time processing statistics.
        
        USAGE: monitor [OPTIONS]
        
        OPTIONS:
          --refresh SEC      Update interval in seconds (default: 1.0)
          --duration SEC     Monitoring duration (default: continuous)
          --output FILE      Save statistics to file
          
        DISPLAYS:
          • Data throughput (samples/sec, MB/sec)
          • Processing performance (integrations/sec)
          • Buffer utilization
          • Data quality metrics
          • System resources (CPU, memory)
          
        EXAMPLES:
          monitor
          monitor --refresh 0.5
          monitor --duration 60 --output stats.log
          
        Press Ctrl+C to stop monitoring.
        """
        if not self.is_streaming:
            print("\\n⚠️  No active stream")
            print("   Start streaming first with 'stream' command")
            return
        
        print("\\n📊 REAL-TIME MONITORING")
        print("   Streaming statistics:")
        
        if self.stream_source:
            stats = self.stream_source.get_statistics()
            print(f"   • Packets: {stats['packets_received']}")
            print(f"   • Data: {stats['bytes_received'] / 1024 / 1024:.2f} MB")
            print(f"   • Rate: {stats['data_rate_mbps']:.2f} Mbps")
            print(f"   • Elapsed: {stats['elapsed_time']:.1f}s")
    
    def do_calibrate(self, arg):
        """Run calibration pipeline on data.
        
        USAGE: calibrate [OPTIONS]
        
        CALIBRATION TYPES:
          --bandpass         Bandpass (frequency response) calibration
          --phase            Phase calibration
          --delay            Delay calibration
          --all              All calibration types (default)
          
        INPUT:
          --input DIR        Directory with calibration observations
          --cal-source NAME  Calibrator source name
          --reference-ant N  Reference antenna (default: 0)
          
        OUTPUT:
          --output FILE      Calibration file (default: calibration.yaml)
          --apply            Apply calibration immediately
          
        EXAMPLES:
          calibrate --input cal_obs/ --cal-source 3C84
          calibrate --bandpass --input bandpass_scan/
          calibrate --all --output my_cal.yaml --apply
          
        ⚠️  PRODUCTION FEATURE: Requires calibrator observations.
        """
        print("\\n🎯 CALIBRATION PIPELINE")
        print("   ⚠️  Feature under development")
        print("   Will support bandpass, phase, and delay calibration")
    
    def do_status(self, arg):
        """Show system status and health check.
        
        USAGE: status
        
        DISPLAYS:
          • Operation mode (production)
          • Connection status
          • Configuration summary
          • Resource usage
          • Last processing run status
          • Output directory info
          
        This command provides an overview of the correlator system state.
        """
        print("\\n⚙️  SYSTEM STATUS")
        print(f"{'='*60}")
        print(f"Operation Mode:    PRODUCTION")
        print(f"Streaming:         {'Active' if self.is_streaming else 'Inactive'}")
        print(f"Data Source:       {self.config.data_source}")
        print(f"Antennas:          {self.config.n_ants}")
        print(f"Channels:          {self.config.n_channels}")
        print(f"Integration:       {self.config.integration_time}s")
        print(f"Output Directory:  {self.config.output_dir}")
        print(f"Monitoring:        {'Enabled' if self.config.enable_monitoring else 'Disabled'}")
        print(f"Quality Checks:    {'Enabled' if self.config.enable_quality_checks else 'Disabled'}")
        print(f"Logging:           {self.config.log_level}")
        print(f"{'='*60}")
        
        if self.stream_source and self.is_streaming:
            print(f"\\n📡 STREAMING STATISTICS:")
            stats = self.stream_source.get_statistics()
            for key, value in stats.items():
                print(f"   {key}: {value}")
    
    def do_config(self, arg):
        """View and modify production configuration.
        
        USAGE:
          config              View current configuration
          config load FILE    Load configuration from YAML file
          config save FILE    Save current configuration
          
        EXAMPLES:
          config
          config load workspace/configs/prod/array64.yaml
          config save my_config.yaml
          
        For real-time parameter changes, most settings require restart.
        """
        if not arg:
            print("\\n⚙️  PRODUCTION CONFIGURATION")
            print(f"{'='*60}")
            # Show production-specific config
            print(f"Mode:              {self.config.operation_mode}")
            print(f"Data Source:       {self.config.data_source}")
            print(f"Antennas:          {self.config.n_ants}")
            print(f"Channels:          {self.config.n_channels}")
            print(f"Integration:       {self.config.integration_time}s")
            print(f"Monitoring:        {self.config.enable_monitoring}")
            print(f"Quality Checks:    {self.config.enable_quality_checks}")
            print(f"RFI Detection:     {self.config.enable_rfi_detection}")
            print(f"{'='*60}")
        else:
            args = shlex.split(arg)
            if args[0] == 'load' and len(args) > 1:
                try:
                    self.config = CorrelatorConfig.from_yaml(args[1])
                    self.config.operation_mode = "production"
                    print(f"✅ Loaded configuration from {args[1]}")
                except Exception as e:
                    print(f"❌ Error loading config: {e}")
            elif args[0] == 'save' and len(args) > 1:
                try:
                    self.config.to_yaml(args[1])
                    print(f"✅ Saved configuration to {args[1]}")
                except Exception as e:
                    print(f"❌ Error saving config: {e}")
    
    def do_help(self, arg):
        """Show help information."""
        if not arg:
            print("\\n🔧 PRODUCTION MODE COMMANDS")
            print("="*60)
            print("stream           Start live data streaming")
            print("process          Process recorded files")
            print("monitor          Real-time statistics")
            print("calibrate        Calibration pipeline")
            print("status           System health check")
            print("config           View/edit configuration")
            print("")
            print("help             This help")
            print("exit             Exit CLI")
            print("")
            print("💡 Type 'help <command>' for detailed information")
            print("")
            print("⚠️  PRODUCTION MODE: No simulation features available")
        else:
            super().do_help(arg)
    
    def do_exit(self, arg):
        """Exit production CLI."""
        if self.is_streaming:
            print("\\n⚠️  Streaming is active")
            confirm = input("Stop streaming and exit? (yes/no): ")
            if confirm.lower() not in ['yes', 'y']:
                return False
            if self.stream_source:
                self.stream_source.disconnect()
        
        print("\\n👋 Exiting production mode.\\n")
        return True
    
    def do_quit(self, arg):
        """Exit production CLI."""
        return self.do_exit(arg)
    
    def do_EOF(self, arg):
        """Handle Ctrl+D."""
        print()
        return self.do_exit(arg)


def start_production_cli():
    """Start the production mode CLI."""
    print("\\n⚠️  PRODUCTION MODE")
    print("   This mode processes REAL telescope data.")
    print("   Simulation features are NOT available.\\n")
    
    confirm = input("Continue to production mode? (yes/no): ")
    if confirm.lower() not in ['yes', 'y']:
        print("Cancelled.\\n")
        return
    
    try:
        ProductionCLI().cmdloop()
    except KeyboardInterrupt:
        print("\\n\\n⚠️  Interrupted. Exiting...\\n")
        sys.exit(0)
