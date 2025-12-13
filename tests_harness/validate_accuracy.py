#!/usr/bin/env python3
"""
Accuracy Validation Demo for Telescope Correlator

This script demonstrates how to validate correlator accuracy using known analytical
solutions and synthetic test data, even without real antennas.

Usage:
    python validate_accuracy.py [test_case]

Test Cases:
    delay_test      - Test delay compensation accuracy
    fft_test        - Test FFT/channelization accuracy
    correlation_test - Test correlation accuracy with known signals
    astronomical_test - Test with realistic astronomical scenario
    all            - Run all tests
"""

import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import sys

# Add the correlator package to path
sys.path.insert(0, str(Path(__file__).parent.parent / "app" / "src"))

from correlator.core.fengine import FEngine
from correlator.core.xengine import XEngine
from correlator.core.delay import DelayEngine


def test_delay_accuracy():
    """Test delay compensation accuracy."""
    print("Testing delay compensation accuracy...")

    # Two antennas, 100m baseline
    ant_pos = np.array([[0, 0, 0], [100, 0, 0]], dtype=float)
    delay_engine = DelayEngine(ant_pos, reference_freq=1e9)  # 1 GHz

    # Source at 45 degrees elevation, 0 degrees azimuth
    source_dir = np.array([1, 0, 1]) / np.sqrt(2)
    delay_engine.set_phase_center(source_dir)

    delays = delay_engine.current_delays  # Access delays directly

    # Expected geometric delay in wavelength units
    # delay_wavelengths = (path_difference) / wavelength
    # path_difference = 100 * cos(45°) = 70.71 m
    # wavelength = c / freq = 3e8 / 1e9 = 0.3 m
    # expected_delay = 70.71 / 0.3 = 235.7
    c = 3e8  # speed of light
    wavelength = c / 1e9  # 0.3 m
    path_diff = 100 * np.cos(np.pi/4)  # 70.71 m
    expected_delay = path_diff / wavelength  # 235.7

    print(".3f")
    print(".3f")
    print(".2e")

    diff = abs(delays[1] - expected_delay)
    print(f"Absolute difference: {diff}")
    return diff < 1e-6  # More reasonable tolerance


def test_fft_accuracy():
    """Test FFT accuracy with pure tone."""
    print("Testing FFT/channelization accuracy...")

    n_channels = 256
    fengine = FEngine(n_channels=n_channels, window_type="rectangular")

    # Pure tone at channel 10
    freq_idx = 10
    freq = freq_idx / n_channels
    t = np.arange(n_channels)
    signal = np.exp(2j * np.pi * freq * t)

    input_data = signal.reshape(1, -1)  # Shape: (1, n_channels)
    output = fengine.process_chunk(input_data)
    spectrum = output[0, 0, :]

    peak_idx = np.argmax(np.abs(spectrum))
    peak_phase = np.angle(spectrum[peak_idx])

    print(f"Input frequency: channel {freq_idx}")
    print(f"Detected peak: channel {peak_idx}")
    print(".6f")

    success = (peak_idx == freq_idx) and (abs(peak_phase) < 1e-10)
    print(f"FFT accuracy test: {'PASS' if success else 'FAIL'}")
    return success


def test_correlation_accuracy():
    """Test correlation accuracy with known signals."""
    print("Testing correlation accuracy...")

    n_ants = 2
    n_channels = 64

    # Create identical signals (perfect correlation)
    signal = np.random.randn(n_channels) + 1j * np.random.randn(n_channels)
    spectrum = np.array([signal, signal])

    xengine = XEngine(n_ants=n_ants, n_channels=n_channels,
                     integration_time=1.0, sample_rate=256.0)

    vis = xengine.correlate_spectrum(spectrum)

    # Check autocorrelations
    expected_power = np.sum(np.abs(signal)**2)
    auto_0 = np.sum(vis[0, :].real)
    auto_1 = np.sum(vis[1, :].real)

    print(".6f")
    print(".6f")
    print(".2e")
    print(".2e")

    # Check cross-correlation
    cross_corr = vis[2, :]
    expected_cross = signal * np.conj(signal)

    cross_error = np.max(np.abs(cross_corr - expected_cross)) / np.max(np.abs(expected_cross))
    print(".2e")

    success = (abs(auto_0 - expected_power) / expected_power < 1e-10 and
               abs(auto_1 - expected_power) / expected_power < 1e-10 and
               cross_error < 1e-10)
    print(f"Correlation accuracy test: {'PASS' if success else 'FAIL'}")
    return success


def test_astronomical_scenario():
    """Test with realistic astronomical scenario."""
    print("Testing astronomical scenario accuracy...")

    # Simple 2-antenna case
    n_ants = 2
    n_channels = 128
    sample_rate = 256.0

    # Create synthetic point source at zenith
    ant_pos = np.array([[0, 0, 0], [50, 0, 0]], dtype=float)

    # Simulate high-SNR point source
    sim_signal = np.exp(2j * np.pi * 0.1 * np.arange(n_channels))  # 10% of Nyquist
    noise_level = 0.01
    ant0 = sim_signal + noise_level * (np.random.randn(n_channels) + 1j * np.random.randn(n_channels))
    ant1 = sim_signal + noise_level * (np.random.randn(n_channels) + 1j * np.random.randn(n_channels))

    spectrum = np.array([ant0, ant1])

    # Setup correlator
    fengine = FEngine(n_channels=n_channels, window_type="hanning")
    delay_engine = DelayEngine(ant_pos, reference_freq=1.0)
    delay_engine.set_phase_center(np.array([0, 0, 1]))  # Zenith

    xengine = XEngine(n_ants=n_ants, n_channels=n_channels,
                     integration_time=1.0, sample_rate=sample_rate)

    # Process (skip F-engine for simplicity, use pre-channelised data)
    freq_channels = np.fft.fftfreq(n_channels, 1/sample_rate)
    corrected = delay_engine.apply_delays(spectrum.reshape(n_ants, 1, n_channels), freq_channels)
    corrected = corrected[:, 0, :]  # Remove spectrum dimension

    vis = xengine.correlate_spectrum(corrected)
    xengine.accumulate(vis)
    integrated = xengine.get_integrated()

    # Validate results
    auto_0_real = np.mean(integrated[0, :].real)
    auto_1_real = np.mean(integrated[1, :].real)
    cross_power = np.mean(np.abs(integrated[2, :])**2)
    mean_phase = np.mean(np.angle(integrated[2, :]))

    print(".3f")
    print(".3f")
    print(".3f")
    print(".3f")

    # Check physical validity
    success = (auto_0_real > 0 and auto_1_real > 0 and cross_power > 0 and abs(mean_phase) < 0.1)
    print(f"Astronomical scenario test: {'PASS' if success else 'FAIL'}")
    return success


def create_accuracy_report():
    """Create a comprehensive accuracy report."""
    print("=" * 60)
    print("Telescope Correlator Accuracy Validation Report")
    print("=" * 60)

    tests = [
        ("Delay Compensation", test_delay_accuracy),
        ("FFT/Channelization", test_fft_accuracy),
        ("Correlation Engine", test_correlation_accuracy),
        ("Astronomical Scenario", test_astronomical_scenario),
    ]

    results = []
    for name, test_func in tests:
        print(f"\n{name}:")
        print("-" * 40)
        try:
            result = test_func()
            results.append((name, result))
            status = "PASS" if result else "FAIL"
            print(f"Result: {status}")
        except Exception as e:
            print(f"Error: {e}")
            results.append((name, False))

    print("\n" + "=" * 60)
    print("Summary:")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    print(f"Tests passed: {passed}/{total}")

    if passed == total:
        print("✓ All accuracy tests passed!")
        print("The correlator implementation appears to be working correctly.")
    else:
        print("✗ Some tests failed. Check implementation for issues.")

    print("\nValidation Methods Demonstrated:")
    print("1. Analytical solutions for delay compensation")
    print("2. Known sinusoidal inputs for FFT validation")
    print("3. Identical signals for perfect correlation testing")
    print("4. Realistic astronomical scenarios with geometric delays")
    print("5. Physical validity checks (autocorrelations real/positive)")

    return passed == total


def main():
    if len(sys.argv) > 1:
        test_case = sys.argv[1]
    else:
        test_case = "all"

    if test_case == "delay_test":
        test_delay_accuracy()
    elif test_case == "fft_test":
        test_fft_accuracy()
    elif test_case == "correlation_test":
        test_correlation_accuracy()
    elif test_case == "astronomical_test":
        test_astronomical_scenario()
    elif test_case == "all":
        create_accuracy_report()
    else:
        print(f"Unknown test case: {test_case}")
        print("Available: delay_test, fft_test, correlation_test, astronomical_test, all")


if __name__ == "__main__":
    main()