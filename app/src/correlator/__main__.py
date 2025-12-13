"""FX Correlator CLI entrypoint

Production-ready telescope correlator with dual operation modes:
- Development (dev): Simulation, testing, learning
- Production (prod): Real telescope data processing

Usage:
    correlator dev              # Development mode (simulations)
    correlator prod             # Production mode (real telescopes)
    correlator dev run --n-ants 8
    correlator prod stream --source tcp://host:port
"""
import sys
import argparse


def main():
    """Main entry point with mode selection."""
    parser = argparse.ArgumentParser(
        description="Telescope Correlator - FX Architecture",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Operation Modes:
  dev     Development mode - simulations, testing, learning
  prod    Production mode - real telescope data processing

Examples:
  correlator dev              Start interactive development CLI
  correlator prod             Start interactive production CLI
  correlator dev run --n-ants 8 --sim-duration 2.0
  correlator prod stream --source tcp://10.0.0.1:7148

For detailed help on each mode:
  correlator dev --help
  correlator prod --help
        """
    )
    
    parser.add_argument(
        'mode',
        nargs='?',
        choices=['dev', 'prod', 'development', 'production'],
        help='Operation mode: dev (simulation) or prod (real telescopes)'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version='Telescope Correlator v1.0.0'
    )
    
    # Parse just the mode argument first
    args, remaining = parser.parse_known_args()
    
    if not args.mode:
        # No mode specified - show help
        parser.print_help()
        print("\n⚠️  Please specify operation mode: 'dev' or 'prod'")
        print("   Examples:")
        print("     correlator dev   # Development mode (simulations)")
        print("     correlator prod  # Production mode (real data)")
        return 1
    
    # Normalize mode names
    mode = args.mode
    if mode == 'development':
        mode = 'dev'
    elif mode == 'production':
        mode = 'prod'
    
    # Route to appropriate mode handler
    if mode == 'dev':
        from correlator.cli.dev import start_development_cli
        start_development_cli()
        return 0
    elif mode == 'prod':
        from correlator.cli.prod import start_production_cli
        start_production_cli()
        return 0
    
    return 0


if __name__ == "__main__":
    sys.exit(main())