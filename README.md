# FX Radio Telescope Correlator

A modular, production-grade FX correlator pipeline for radio telescope arrays, simulating 4 antennas with user-configurable frequencies. The system is designed for easy extension and future real data input.

---

## 🚀 New! Teaching CLI for Everyone

**Start here if you want to learn and explore!**

- Use `cli.py` for a step-by-step, interactive, and highly explanatory experience.
- The CLI will walk you through each stage, explain what's happening, and show you real data at every step.
- No prior experience or hardware needed!

### **Run the Teaching CLI**
```sh
python cli.py run
```
- You'll be guided through the simulation, FFT, correlation, integration, and output.

### **View Output with Explanations**
```sh
python cli.py view output/vis_teaching.h5
```
- Prints datasets, metadata, and sample data in a user-friendly, educational way.

---

## How the Correlator Works

- **F-Engine**: Converts simulated time-domain signals from each antenna into frequency channels using FFT (Fourier Transform).
- **X-Engine**: Cross-correlates all pairs of antennas in the frequency domain, producing "visibilities" (complex numbers that encode how signals from different antennas relate).
- **Integrator**: Averages visibilities over time for better signal-to-noise.
- **Output**: Saves results and metadata in HDF5 files.

**Simulation:**
- If you don't have real antennas, the system generates fake signals (sine waves) for each antenna, so you can always run and test the pipeline. **No hardware needed!**

---

## Quick Start (Super Easy!)

### 1. **Build and Run with Docker (Advanced/Batch Use)**

```sh
# Build the Docker image
docker build -t correlator .

# Run the correlator simulation and save output to ./output
docker run --rm -v $(pwd)/output:/app/output correlator run
```

### 2. **Run Locally with Python (Advanced/Batch Use)**

```sh
pip install -r requirements.txt
python main.py run
```

---

## User-Friendly CLI

### **Run the Correlator Simulation**
```sh
python main.py run [options]
```
- All options have sensible defaults. Example:
  ```sh
  python main.py run --num_antennas 4 --sample_rate 1e6 --frame_size 4096 --fft_size 4096 --n_integrate 10 --frequencies 1e5 2e5 3e5 4e5 --output vis_example.h5
  ```

### **View Output HDF5 Files**
```sh
python main.py view output/vis_example.h5
```
- Prints datasets, metadata, and sample data in a user-friendly way.

---

## Output
- HDF5 files in `./output/` containing:
  - `visibilities`: (num_antennas, num_antennas, n_freq)
  - `frequencies`: (n_freq,)
  - `metadata`: run configuration

---

## Extending
- To add real data input: see TODO in `signal_reader.py`
- To increase antennas or FFT size: use command-line arguments
- To add PFB: see TODO in `fengine.py`

---

**Industry-grade, modular, and ready for research or production! Anyone can use it—no hardware or prior experience needed!**