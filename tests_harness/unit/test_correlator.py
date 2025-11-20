"""Unit tests for the correlator core using synthetic data."""
from __future__ import annotations

import numpy as np
from pathlib import Path

from correlator.core import Correlator
from tests_harness.generators.simulate import generate_delayed_sine


def test_correlator_detects_delay():
    x, y = generate_delayed_sine(duration=0.05, sample_rate=1024, delay_samples=7, noise_std=0.0)
    c = Correlator()
    corr = c.correlate(x, y, mode="full")
    peak = int(np.argmax(np.abs(corr)))
    zero_lag = len(y) - 1
    lag = peak - zero_lag
    assert lag == 7


def test_empty_inputs_return_empty():
    c = Correlator()
    out = c.correlate([], [], mode="full")
    assert out.size == 0
