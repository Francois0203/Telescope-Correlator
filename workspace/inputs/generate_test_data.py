#!/usr/bin/env python3
"""Generate test input data for telescope correlator testing."""
import numpy as np
from pathlib import Path

def generate_simple_signal(n_ants=4, n_samples=4096, sample_rate=1024.0, 
                          signal_freq=10.0, snr_db=20.0):
    """Generate a simple test signal with known properties.
    
    Creates a sinusoidal signal received by multiple antennas with 
    added Gaussian noise.
    
    Parameters
    ----------
    n_ants : int
        Number of antennas
    n_samples : int
        Number of time samples
    sample_rate : float
        Sample rate in Hz
    signal_freq : float
        Signal frequency in Hz
    snr_db : float
        Signal-to-noise ratio in dB
        
    Returns
    -------
    data : ndarray
        Complex signal array, shape (n_ants, n_samples)
    metadata : dict
        Metadata about the signal
    """
    # Time array
    t = np.arange(n_samples) / sample_rate
    
    # Create base signal (complex sinusoid)
    signal = np.exp(2j * np.pi * signal_freq * t)
    
    # Calculate noise power from SNR
    signal_power = 1.0  # Unit amplitude signal
    snr_linear = 10 ** (snr_db / 10)
    noise_power = signal_power / snr_linear
    noise_std = np.sqrt(noise_power / 2)  # Divide by 2 for complex noise
    
    # Generate data for each antenna with phase delays
    data = np.zeros((n_ants, n_samples), dtype=np.complex128)
    phase_delays = np.linspace(0, np.pi/4, n_ants)  # Different phase for each antenna
    
    for i in range(n_ants):
        # Apply phase delay
        phase_shifted = signal * np.exp(1j * phase_delays[i])
        
        # Add complex Gaussian noise
        noise = noise_std * (np.random.randn(n_samples) + 1j * np.random.randn(n_samples))
        data[i, :] = phase_shifted + noise
    
    metadata = {
        'n_ants': n_ants,
        'n_samples': n_samples,
        'sample_rate': sample_rate,
        'signal_freq': signal_freq,
        'snr_db': snr_db,
        'phase_delays': phase_delays.tolist(),
        'description': 'Simple sinusoidal test signal with phase delays'
    }
    
    return data, metadata


def generate_dual_source_signal(n_ants=4, n_samples=4096, sample_rate=1024.0,
                                source1_freq=10.0, source2_freq=15.0, snr_db=15.0):
    """Generate signal from two sources at different frequencies.
    
    Parameters
    ----------
    n_ants : int
        Number of antennas
    n_samples : int
        Number of time samples
    sample_rate : float
        Sample rate in Hz
    source1_freq : float
        First source frequency in Hz
    source2_freq : float
        Second source frequency in Hz
    snr_db : float
        Signal-to-noise ratio in dB
        
    Returns
    -------
    data : ndarray
        Complex signal array, shape (n_ants, n_samples)
    metadata : dict
        Metadata about the signal
    """
    t = np.arange(n_samples) / sample_rate
    
    # Two sources
    source1 = 0.7 * np.exp(2j * np.pi * source1_freq * t)
    source2 = 0.5 * np.exp(2j * np.pi * source2_freq * t)
    combined = source1 + source2
    
    # Calculate noise
    signal_power = np.mean(np.abs(combined)**2)
    snr_linear = 10 ** (snr_db / 10)
    noise_power = signal_power / snr_linear
    noise_std = np.sqrt(noise_power / 2)
    
    # Generate antenna data
    data = np.zeros((n_ants, n_samples), dtype=np.complex128)
    angles = np.linspace(0, 2*np.pi, n_ants, endpoint=False)
    
    for i in range(n_ants):
        # Different phase for each source at each antenna
        phase1 = 0.5 * np.cos(angles[i])
        phase2 = 0.3 * np.sin(angles[i])
        
        signal = source1 * np.exp(1j * phase1) + source2 * np.exp(1j * phase2)
        noise = noise_std * (np.random.randn(n_samples) + 1j * np.random.randn(n_samples))
        data[i, :] = signal + noise
    
    metadata = {
        'n_ants': n_ants,
        'n_samples': n_samples,
        'sample_rate': sample_rate,
        'source1_freq': source1_freq,
        'source2_freq': source2_freq,
        'snr_db': snr_db,
        'description': 'Dual source signal at different frequencies'
    }
    
    return data, metadata


def generate_pulsed_signal(n_ants=4, n_samples=4096, sample_rate=1024.0,
                          carrier_freq=20.0, pulse_rate=5.0, duty_cycle=0.3):
    """Generate a pulsed signal (like a pulsar).
    
    Parameters
    ----------
    n_ants : int
        Number of antennas
    n_samples : int
        Number of time samples
    sample_rate : float
        Sample rate in Hz
    carrier_freq : float
        Carrier frequency in Hz
    pulse_rate : float
        Pulse repetition rate in Hz
    duty_cycle : float
        Fraction of time pulse is on (0-1)
        
    Returns
    -------
    data : ndarray
        Complex signal array, shape (n_ants, n_samples)
    metadata : dict
        Metadata about the signal
    """
    t = np.arange(n_samples) / sample_rate
    
    # Carrier signal
    carrier = np.exp(2j * np.pi * carrier_freq * t)
    
    # Pulse envelope (square wave)
    pulse_phase = (t * pulse_rate) % 1.0
    envelope = (pulse_phase < duty_cycle).astype(float)
    
    # Modulated signal
    signal = carrier * envelope
    
    # Add noise
    noise_std = 0.3
    
    data = np.zeros((n_ants, n_samples), dtype=np.complex128)
    for i in range(n_ants):
        phase_delay = i * np.pi / (2 * n_ants)
        shifted = signal * np.exp(1j * phase_delay)
        noise = noise_std * (np.random.randn(n_samples) + 1j * np.random.randn(n_samples))
        data[i, :] = shifted + noise
    
    metadata = {
        'n_ants': n_ants,
        'n_samples': n_samples,
        'sample_rate': sample_rate,
        'carrier_freq': carrier_freq,
        'pulse_rate': pulse_rate,
        'duty_cycle': duty_cycle,
        'description': 'Pulsed signal (pulsar-like)'
    }
    
    return data, metadata


def save_test_data(output_dir='./'):
    """Generate and save all test datasets."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("Generating test input data...")
    print("="*60)
    
    # 1. Simple signal
    print("\n1. Simple sinusoidal signal")
    data1, meta1 = generate_simple_signal(n_ants=4, n_samples=4096)
    np.save(output_dir / 'simple_signal.npy', data1)
    print(f"   Saved: simple_signal.npy")
    print(f"   Shape: {data1.shape}")
    print(f"   Type: {data1.dtype}")
    print(f"   Description: {meta1['description']}")
    
    # 2. Dual source
    print("\n2. Dual source signal")
    data2, meta2 = generate_dual_source_signal(n_ants=4, n_samples=4096)
    np.save(output_dir / 'dual_source_signal.npy', data2)
    print(f"   Saved: dual_source_signal.npy")
    print(f"   Shape: {data2.shape}")
    print(f"   Description: {meta2['description']}")
    
    # 3. Pulsed signal
    print("\n3. Pulsed signal")
    data3, meta3 = generate_pulsed_signal(n_ants=4, n_samples=4096)
    np.save(output_dir / 'pulsed_signal.npy', data3)
    print(f"   Saved: pulsed_signal.npy")
    print(f"   Shape: {data3.shape}")
    print(f"   Description: {meta3['description']}")
    
    # 4. Short test signal for quick tests
    print("\n4. Quick test signal (small)")
    data4, meta4 = generate_simple_signal(n_ants=4, n_samples=512)
    np.save(output_dir / 'quick_test.npy', data4)
    print(f"   Saved: quick_test.npy")
    print(f"   Shape: {data4.shape}")
    print(f"   Description: Small signal for quick testing")
    
    # 5. Large dataset for performance testing
    print("\n5. Large test signal (performance)")
    data5, meta5 = generate_simple_signal(n_ants=8, n_samples=16384)
    np.save(output_dir / 'large_test.npy', data5)
    print(f"   Saved: large_test.npy")
    print(f"   Shape: {data5.shape}")
    print(f"   Description: Large signal for performance testing")
    
    print("\n" + "="*60)
    print(f"✅ Generated 5 test datasets in {output_dir}/")
    print("\nTo use in correlator:")
    print("  1. Start container: ./correlator.bat dev")
    print("  2. Run: python /workspace/inputs/generate_test_data.py")
    print("  3. Use files in processing (example below)")
    print("\nAll files are accessible at /workspace/inputs/ inside the container")
    
    # Create a README
    readme_content = """# Test Input Data

This directory contains generated test signals for correlator testing.

## Files

1. **simple_signal.npy** (4 ants, 4096 samples)
   - Single sinusoidal signal with phase delays
   - Good for basic functionality testing
   
2. **dual_source_signal.npy** (4 ants, 4096 samples)
   - Two sources at different frequencies
   - Tests multi-source correlation
   
3. **pulsed_signal.npy** (4 ants, 4096 samples)
   - Pulsed carrier signal (pulsar-like)
   - Tests time-varying signals
   
4. **quick_test.npy** (4 ants, 512 samples)
   - Small dataset for quick tests
   - Fast execution
   
5. **large_test.npy** (8 ants, 16384 samples)
   - Large dataset for performance testing
   - Tests scalability

## Data Format

All files are numpy arrays (.npy format):
- Shape: (n_antennas, n_samples)
- Dtype: complex128
- Complex time-domain signals

## Usage

From within the container:

```bash
# View input data
ls -lh /workspace/inputs/

# Load in Python
import numpy as np
data = np.load('/workspace/inputs/simple_signal.npy')
print(f"Shape: {data.shape}")
```

## Regenerate Data

To regenerate all test data:

```bash
python /workspace/inputs/generate_test_data.py
```
"""
    
    with open(output_dir / 'README.md', 'w') as f:
        f.write(readme_content)
    print("\n📄 Created README.md with documentation")


if __name__ == '__main__':
    save_test_data('./')
