# Test Input Data

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
