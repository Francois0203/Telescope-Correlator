#!/usr/bin/env python3
"""Inspect test input data files."""
import numpy as np
from pathlib import Path
import sys

def inspect_file(filepath):
    """Display information about a data file."""
    try:
        data = np.load(filepath)
        
        print(f"\n{'='*70}")
        print(f"File: {filepath.name}")
        print(f"{'='*70}")
        print(f"Shape:        {data.shape}")
        print(f"Dtype:        {data.dtype}")
        print(f"Size:         {data.nbytes / 1024:.2f} KB")
        print(f"")
        print(f"Statistics:")
        print(f"  Real part:")
        print(f"    Mean:     {np.mean(data.real):.6f}")
        print(f"    Std dev:  {np.std(data.real):.6f}")
        print(f"    Min:      {np.min(data.real):.6f}")
        print(f"    Max:      {np.max(data.real):.6f}")
        print(f"  Imaginary part:")
        print(f"    Mean:     {np.mean(data.imag):.6f}")
        print(f"    Std dev:  {np.std(data.imag):.6f}")
        print(f"    Min:      {np.min(data.imag):.6f}")
        print(f"    Max:      {np.max(data.imag):.6f}")
        print(f"  Magnitude:")
        print(f"    Mean:     {np.mean(np.abs(data)):.6f}")
        print(f"    Max:      {np.max(np.abs(data)):.6f}")
        
        # Show a sample of the data
        print(f"\nFirst 5 samples of antenna 0:")
        for i in range(min(5, data.shape[1])):
            print(f"  [{i}] {data[0, i]:.6f}")
        
        return True
    except Exception as e:
        print(f"❌ Error reading {filepath}: {e}")
        return False


def list_input_files(input_dir='/workspace/inputs'):
    """List all .npy files in the input directory."""
    input_path = Path(input_dir)
    
    if not input_path.exists():
        print(f"❌ Input directory does not exist: {input_dir}")
        return []
    
    npy_files = sorted(input_path.glob('*.npy'))
    
    if not npy_files:
        print(f"📁 No .npy files found in {input_dir}")
        return []
    
    print(f"\n📁 Input data files in {input_dir}/:")
    print(f"{'='*70}")
    print(f"{'#':<4} {'Filename':<35} {'Size':<15}")
    print(f"{'='*70}")
    
    for i, f in enumerate(npy_files, 1):
        size_kb = f.stat().st_size / 1024
        print(f"{i:<4} {f.name:<35} {size_kb:>8.2f} KB")
    
    print(f"{'='*70}")
    
    return npy_files


def main():
    """Main function to inspect input data."""
    print("\n🔍 TEST INPUT DATA INSPECTOR")
    
    # List all files
    files = list_input_files()
    
    if not files:
        print("\nℹ️  No input data found. Generate it with:")
        print("   python /workspace/inputs/generate_test_data.py")
        return
    
    # If a filename is provided as argument, inspect it
    if len(sys.argv) > 1:
        filename = sys.argv[1]
        filepath = Path('/workspace/inputs') / filename
        if not filepath.exists():
            filepath = Path(filename)  # Try as absolute path
        
        if filepath.exists():
            inspect_file(filepath)
        else:
            print(f"\n❌ File not found: {filename}")
            print(f"\nAvailable files:")
            for f in files:
                print(f"  • {f.name}")
    else:
        # Inspect all files
        print("\n" + "="*70)
        print("DETAILED INSPECTION OF ALL FILES")
        print("="*70)
        
        for filepath in files:
            inspect_file(filepath)
    
    print(f"\n💡 Usage:")
    print(f"   Inspect specific file: python inspect_data.py <filename>")
    print(f"   Inspect all files:     python inspect_data.py")
    print()


if __name__ == '__main__':
    main()
