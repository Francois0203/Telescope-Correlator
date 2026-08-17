"""F-Engine: Channeliser Module

Implements the channeliser (Fourier transform stage) of an FX correlator.
Performs windowed FFT to convert time-domain signals into frequency channels.

Key features:
- Configurable FFT size (number of channels)
- Window functions (Hanning, Hamming, Blackman, rectangular), normalised to
  unit coherent gain so the flux scale does not depend on the window choice
- Quantization emulation with configurable bit depths
- Polyphase filterbank mode (optional)

Amplitude convention
--------------------
Windows are scaled by ``n_channels / sum(w)``. A coherent tone of amplitude
``A`` landing exactly on a bin therefore produces ``|X[k]| = A * n_channels``
for every window type, and a visibility amplitude of ``(A * n_channels)**2``.
White noise of variance ``sigma**2`` produces ``<|X[k]|**2> = sigma**2 *
noise_gain``, which is window dependent because equivalent noise bandwidths
differ.

The FFT itself is unnormalised (no ``1/N``), so visibility amplitudes scale
as ``n_channels**2``. That is a deliberate, documented convention rather than
an oversight; flux calibration absorbs the constant.
"""
from __future__ import annotations

import numpy as np
from typing import Optional, Literal

WindowType = Literal["rectangular", "hanning", "hamming", "blackman"]


def get_window(window_type: WindowType, size: int) -> np.ndarray:
    """Generate window function.
    
    Args:
        window_type: Type of window
        size: Window length
    
    Returns:
        Window coefficients
    """
    if window_type == "rectangular":
        return np.ones(size)
    elif window_type == "hanning":
        return np.hanning(size)
    elif window_type == "hamming":
        return np.hamming(size)
    elif window_type == "blackman":
        return np.blackman(size)
    else:
        raise ValueError(f"Unknown window type: {window_type}")


def quantize_signal(
    signal: np.ndarray,
    n_bits: int,
    complex_quant: bool = True
) -> np.ndarray:
    """Quantize complex signal to fixed bit depth.
    
    Args:
        signal: Complex input signal
        n_bits: Number of bits per component (real/imag)
        complex_quant: If True, quantize real and imag separately
    
    Returns:
        Quantized signal
    """
    if n_bits <= 0:
        return signal  # No quantization
    
    # Number of quantization levels
    n_levels = 2 ** n_bits
    
    if complex_quant:
        # Quantize real and imaginary parts separately
        real_part = signal.real
        imag_part = signal.imag
        
        # Normalize to [-1, 1] based on signal statistics
        real_scale = 3 * np.std(real_part)  # 3-sigma clipping
        imag_scale = 3 * np.std(imag_part)
        
        real_norm = np.clip(real_part / real_scale, -1, 1)
        imag_norm = np.clip(imag_part / imag_scale, -1, 1)
        
        # Quantize to n_levels
        real_quant = np.round(real_norm * (n_levels / 2 - 1)) / (n_levels / 2 - 1)
        imag_quant = np.round(imag_norm * (n_levels / 2 - 1)) / (n_levels / 2 - 1)
        
        # Reconstruct
        return (real_quant * real_scale) + 1j * (imag_quant * imag_scale)
    else:
        # Magnitude-phase quantization (optional)
        mag = np.abs(signal)
        phase = np.angle(signal)
        
        mag_scale = 3 * np.std(mag)
        mag_norm = np.clip(mag / mag_scale, 0, 1)
        mag_quant = np.round(mag_norm * (n_levels - 1)) / (n_levels - 1)
        mag_quant = mag_quant * mag_scale
        
        return mag_quant * np.exp(1j * phase)


class FEngine:
    """F-Engine: Channeliser.
    
    Converts time-domain antenna signals into frequency channels using FFT.
    """
    
    def __init__(
        self,
        n_channels: int,
        window_type: WindowType = "hanning",
        quantize_bits: int = 0,
        overlap_factor: float = 0.0,
    ):
        """Initialize F-engine.
        
        Args:
            n_channels: Number of frequency channels (FFT size)
            window_type: Windowing function
            quantize_bits: Bit depth for quantization (0 = no quantization)
            overlap_factor: Overlap between consecutive FFTs (0.0 to 0.5)
        """
        self.n_channels = n_channels
        self.window_type = window_type
        self.quantize_bits = quantize_bits
        self.overlap_factor = overlap_factor

        # Pre-compute the window, normalised to unit coherent gain.
        #
        # An unnormalised taper attenuates coherent signals by sum(w)/N, about
        # 0.5 for Hanning. Without normalisation, changing the window would
        # rescale every visibility amplitude and the flux scale with it.
        # Scaling by N/sum(w) makes the coherent response identical for every
        # window, so the window only controls spectral leakage.
        #
        # Noise power cannot be window-independent at the same time. It scales
        # with ``noise_gain`` below, which differs per window because their
        # equivalent noise bandwidths differ. That is physics, not a choice.
        raw_window = get_window(window_type, n_channels)
        self.window = raw_window * (n_channels / np.sum(raw_window))

        # Response of one channel to a coherent tone on its exact bin
        # (== n_channels for every window, by the normalisation above) and to
        # white noise (window dependent).
        self.coherent_gain = float(np.sum(self.window))
        self.noise_gain = float(np.sum(self.window ** 2))

        # Compute stride (hop size)
        self.stride = int(n_channels * (1 - overlap_factor))
    
    def process_chunk(self, signals: np.ndarray) -> np.ndarray:
        """Process a chunk of time-domain signals.
        
        Args:
            signals: Complex array shape (n_ants, n_samples)
        
        Returns:
            Channelised data shape (n_ants, n_spectra, n_channels)
            where n_spectra = number of FFT windows that fit in n_samples
        """
        n_ants, n_samples = signals.shape
        
        # Apply quantization if requested
        if self.quantize_bits > 0:
            signals = quantize_signal(signals, self.quantize_bits)
        
        # Compute number of spectra
        n_spectra = (n_samples - self.n_channels) // self.stride + 1
        
        if n_spectra <= 0:
            raise ValueError(f"Chunk too small ({n_samples} samples) for FFT size {self.n_channels}")
        
        # Allocate output
        channelised = np.zeros((n_ants, n_spectra, self.n_channels), dtype=np.complex128)
        
        # Process each antenna
        for ant_idx in range(n_ants):
            for spec_idx in range(n_spectra):
                start = spec_idx * self.stride
                end = start + self.n_channels
                
                # Extract window, apply windowing function, and FFT
                windowed = signals[ant_idx, start:end] * self.window
                spectrum = np.fft.fft(windowed)
                
                channelised[ant_idx, spec_idx, :] = spectrum
        
        return channelised
    
    def get_channel_frequencies(self, sample_rate: float) -> np.ndarray:
        """Get the frequency of each channel.
        
        Args:
            sample_rate: Sample rate in Hz
        
        Returns:
            Array of frequencies (Hz) for each channel
        """
        return np.fft.fftfreq(self.n_channels, d=1/sample_rate)