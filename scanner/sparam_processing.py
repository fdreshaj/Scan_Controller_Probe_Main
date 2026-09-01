"""Signal processing for swept-frequency S-parameter data.

Pure numpy: no Qt, no HDF5, no file I/O. Everything the visualizer's FFT,
filter and phase views need lives here so it can be tested without a display or
an instrument -- see tests/test_sparam_processing.py.

Conventions
-----------
Data is complex ``S(f)`` sampled on a uniform frequency grid, shaped
``(..., n_freq)`` with frequency as the last axis. A whole scan is therefore
``(n_points, n_freq)`` and every function here broadcasts over the leading axes,
so one call transforms every measurement point at once.

Frequencies are handled in **Hz** throughout. The scan writer stores
``/Frequencies/Range`` in GHz, so use `normalize_frequencies_to_hz` at the
boundary rather than trusting the raw array.

The time-domain transform is the standard VNA **band-pass mode**: the measured
band is inverse-transformed as-is, giving the complex envelope of the impulse
response. The result is complex; take its magnitude for a range profile. Unlike
low-pass mode it needs no harmonically-related sweep and no DC extrapolation,
but the envelope carries no absolute phase reference, which is why the range
axis is a relative delay.
"""

from __future__ import annotations

import numpy as np

#: Speed of light in vacuum, m/s.
SPEED_OF_LIGHT = 299_792_458.0

# -- filter modes ----------------------------------------------------------
FILTER_OFF = "Off"
FILTER_LOW_PASS = "Low Pass"
FILTER_HIGH_PASS = "High Pass"
FILTER_MODES = (FILTER_OFF, FILTER_LOW_PASS, FILTER_HIGH_PASS)

# -- window functions ------------------------------------------------------
WINDOW_NONE = "None"
WINDOW_HANN = "Hann"
WINDOW_HAMMING = "Hamming"
WINDOW_BLACKMAN = "Blackman"
WINDOW_NAMES = (WINDOW_HANN, WINDOW_HAMMING, WINDOW_BLACKMAN, WINDOW_NONE)

# -- display transforms ----------------------------------------------------
DISPLAY_MAGNITUDE = "Magnitude"
DISPLAY_MAGNITUDE_DB = "Magnitude (dB)"
DISPLAY_PHASE_DEG = "Phase (deg)"
DISPLAY_PHASE_UNWRAPPED = "Phase unwrapped (deg)"
DISPLAY_PHASE_RAD = "Phase (rad)"
DISPLAY_REAL = "Real"
DISPLAY_IMAGINARY = "Imaginary"
DISPLAY_MODES = (
    DISPLAY_MAGNITUDE,
    DISPLAY_MAGNITUDE_DB,
    DISPLAY_PHASE_DEG,
    DISPLAY_PHASE_UNWRAPPED,
    DISPLAY_PHASE_RAD,
    DISPLAY_REAL,
    DISPLAY_IMAGINARY,
)

#: Modes whose value at one frequency depends on the whole sweep, so the
#: transform has to be applied across the frequency axis before a slice is
#: taken rather than to the slice itself.
SWEEP_DEPENDENT_MODES = (DISPLAY_PHASE_UNWRAPPED,)

#: Floor for the dB conversion, so log10(0) does not produce -inf and destroy
#: the colour scale of a whole image.
DB_FLOOR = 1e-12


# ==========================================================================
# Frequency axis
# ==========================================================================

def normalize_frequencies_to_hz(frequencies) -> np.ndarray:
    """Return the frequency axis in Hz, whatever unit it arrived in.

    `Scanner.run_scan` divides by 1e9 before writing ``/Frequencies/Range``, so
    files on disk hold GHz, while a probe plugin's ``get_xaxis_coords()``
    returns Hz. Both reach the visualizer.

    The discriminator is magnitude: a microwave sweep expressed in Hz is on the
    order of 1e9, and one expressed in GHz is on the order of 1e1. Anything
    below 1e6 is therefore treated as GHz and scaled up. That threshold leaves
    six orders of magnitude of headroom on both sides -- a real sweep never
    lands near it.
    """
    freqs = np.asarray(frequencies, dtype=float).ravel()
    if freqs.size == 0:
        return freqs
    if np.nanmax(np.abs(freqs)) < 1e6:
        return freqs * 1e9
    return freqs


def frequency_step(freqs_hz) -> float:
    """Spacing of a uniform frequency grid, in Hz.

    Raises when the grid is not uniform: every transform in this module is a
    DFT, which is only meaningful on evenly spaced samples. Silently accepting
    a segmented sweep would produce a plausible-looking but wrong range profile.
    """
    freqs = np.asarray(freqs_hz, dtype=float).ravel()
    if freqs.size < 2:
        raise ValueError("at least two frequency points are needed")

    steps = np.diff(freqs)
    step = float(np.mean(steps))
    if step <= 0:
        raise ValueError("frequency axis must be strictly increasing")

    # 1% of the mean step is far tighter than any real VNA's grid error and far
    # looser than float64 noise.
    if np.max(np.abs(steps - step)) > abs(step) * 0.01:
        raise ValueError(
            "frequency axis is not uniformly spaced; the FFT and filter views "
            "require an evenly spaced sweep"
        )
    return step


def max_unambiguous_delay(freqs_hz) -> float:
    """Longest delay the sweep can resolve without aliasing, in seconds.

    ``1 / df``. A reflection arriving later than this wraps around and appears
    at a short delay, so it is also the full span of the time axis.
    """
    return 1.0 / frequency_step(freqs_hz)


def max_filter_delay(freqs_hz) -> float:
    """Largest delay a filter cutoff can meaningfully address, in seconds.

    Half the unambiguous span. `circular_delays` folds bin ``k`` and bin
    ``n - k`` together, so the delay axis a filter sees runs from 0 to
    ``1 / (2 * df)`` and then back down again. A reflection arriving later than
    that folds onto a short delay and a low-pass filter will keep it -- not a
    bug, just what a DFT of a finite sweep can represent.

    Setting a cutoff above this value is meaningless: the mask is already 1
    everywhere. The visualizer clamps its cutoff control to this.
    """
    return max_unambiguous_delay(freqs_hz) / 2.0


def delay_resolution(freqs_hz) -> float:
    """Nominal delay resolution, in seconds: ``1 / bandwidth``."""
    freqs = np.asarray(freqs_hz, dtype=float).ravel()
    bandwidth = float(freqs[-1] - freqs[0])
    if bandwidth <= 0:
        raise ValueError("frequency span must be positive")
    return 1.0 / bandwidth


def time_to_range(times_s, velocity_factor: float = 1.0, two_way: bool = True):
    """Convert delay in seconds to distance in metres.

    `two_way` halves the result, which is what you want for a reflection
    measurement (S11): the wave travels to the target and back.
    `velocity_factor` scales for propagation slower than free space -- use
    ``1/sqrt(eps_r)`` for a dielectric.
    """
    times = np.asarray(times_s, dtype=float)
    distance = times * SPEED_OF_LIGHT * velocity_factor
    return distance / 2.0 if two_way else distance


# ==========================================================================
# Windowing
# ==========================================================================

def window_values(name: str, length: int, normalize: bool = True) -> np.ndarray:
    """Window of `length` samples for the named function.

    A rectangular window (``"None"``) gives the sharpest possible resolution
    and -13 dB sidelobes, which smear a strong reflection across the whole
    range axis. Hann is the default for that reason.

    With `normalize` set the window is scaled to unit coherent gain (mean 1).
    Without it, a Hann window would roughly halve every amplitude in the time
    domain, so switching windows to clean up sidelobes would also silently
    rescale the data and change the numbers an operator reads off the range
    profile. Normalised, the window control does one thing: trade resolution
    against sidelobes.
    """
    if length <= 0:
        raise ValueError("window length must be positive")
    if name == WINDOW_NONE:
        window = np.ones(length)
    elif name == WINDOW_HANN:
        window = np.hanning(length)
    elif name == WINDOW_HAMMING:
        window = np.hamming(length)
    elif name == WINDOW_BLACKMAN:
        window = np.blackman(length)
    else:
        raise ValueError(f"unknown window {name!r}; expected one of {WINDOW_NAMES}")

    if normalize:
        mean = window.mean()
        if mean > 0:
            window = window / mean
    return window


# ==========================================================================
# Time-domain transform (the FFT view)
# ==========================================================================

def to_time_domain(
    s_freq,
    freqs_hz,
    window: str = WINDOW_HANN,
    pad_factor: int = 4,
):
    """Transform ``S(f)`` to the time domain, band-pass mode.

    Parameters
    ----------
    s_freq:
        Complex array shaped ``(..., n_freq)``.
    freqs_hz:
        Uniform frequency axis in Hz, length ``n_freq``.
    window:
        Applied across the frequency axis before transforming, to suppress the
        sidelobes that the finite sweep would otherwise produce.
    pad_factor:
        Zero-padding multiplier. Padding interpolates the time axis -- it makes
        the peak easier to locate but adds no real resolution, which is fixed
        at ``1 / bandwidth`` by the sweep.

    Returns
    -------
    (times_s, s_time):
        `times_s` is the delay axis in seconds, spanning ``0`` to ``1 / df``.
        `s_time` is complex and shaped ``(..., n_freq * pad_factor)``; take
        ``abs()`` for a range profile.

    Amplitude is normalised so that padding does not change the height of a
    peak: a flat unity response transforms to a peak of 1.0 at zero delay for
    any `pad_factor`.
    """
    data = np.asarray(s_freq)
    if data.ndim == 0:
        raise ValueError("s_freq must have at least one dimension")

    n_freq = data.shape[-1]
    freqs = np.asarray(freqs_hz, dtype=float).ravel()
    if freqs.size != n_freq:
        raise ValueError(
            f"frequency axis has {freqs.size} points but data has {n_freq}"
        )
    if pad_factor < 1:
        raise ValueError("pad_factor must be at least 1")

    df = frequency_step(freqs)

    windowed = data * window_values(window, n_freq)

    n_padded = n_freq * int(pad_factor)
    # ifft's own 1/N is relative to the padded length, so scale it back out to
    # keep peak amplitude independent of pad_factor.
    s_time = np.fft.ifft(windowed, n=n_padded, axis=-1) * (n_padded / n_freq)

    dt = 1.0 / (n_padded * df)
    times = np.arange(n_padded) * dt
    return times, s_time


# ==========================================================================
# Filtering (the filter view)
# ==========================================================================

def circular_delays(n_bins: int, df: float) -> np.ndarray:
    """Delay magnitude of each DFT bin, in seconds.

    A DFT of ``S(f)`` is circular: bin ``k`` and bin ``n - k`` are the same
    delay with opposite sign. Folding them together is what makes a filter mask
    symmetric, so a low-pass keeps short delays of *either* sign instead of
    lopping off half the response.
    """
    if n_bins < 1:
        raise ValueError("n_bins must be positive")
    if df <= 0:
        raise ValueError("df must be positive")
    k = np.arange(n_bins)
    folded = np.minimum(k, n_bins - k)
    return folded / (n_bins * df)


def filter_mask(
    delays_s,
    mode: str,
    cutoff_s: float,
    transition: float = 0.25,
) -> np.ndarray:
    """Build the multiplicative mask a filter applies to the delay bins.

    The edge is a raised cosine spanning ``cutoff * transition`` rather than a
    brick wall. A hard edge in the delay domain rings in the frequency domain
    (Gibbs), which shows up as ripple across the sweep and is easy to mistake
    for a real resonance.

    `transition` is the full width of the roll-off as a fraction of the cutoff;
    0 gives a brick wall.
    """
    delays = np.asarray(delays_s, dtype=float)

    if mode == FILTER_OFF:
        return np.ones_like(delays)
    if mode not in (FILTER_LOW_PASS, FILTER_HIGH_PASS):
        raise ValueError(f"unknown filter mode {mode!r}; expected one of {FILTER_MODES}")
    if cutoff_s < 0:
        raise ValueError("cutoff must not be negative")
    if not 0.0 <= transition <= 1.0:
        raise ValueError("transition must be between 0 and 1")

    half = cutoff_s * transition / 2.0
    lower, upper = cutoff_s - half, cutoff_s + half

    if upper <= lower:  # brick wall, or a zero cutoff
        low_pass = (delays <= cutoff_s).astype(float)
    else:
        # 1 below `lower`, 0 above `upper`, raised cosine in between.
        ramp = np.clip((delays - lower) / (upper - lower), 0.0, 1.0)
        low_pass = 0.5 * (1.0 + np.cos(np.pi * ramp))

    return low_pass if mode == FILTER_LOW_PASS else 1.0 - low_pass


def apply_filter(
    s_freq,
    freqs_hz,
    mode: str,
    cutoff_s: float,
    transition: float = 0.25,
):
    """Filter ``S(f)`` along the frequency axis by delay content.

    The frequency sweep is transformed to the delay domain, masked, and
    transformed back, so the result is still ``S(f)`` and every downstream view
    keeps working unchanged.

    What the two modes mean physically:

    **Low pass** keeps short delays. It removes the fast ripple across the
    sweep that long paths produce -- multipath, chamber reflections, a target
    behind the one you care about. This is time gating expressed as a filter.

    **High pass** keeps long delays. It removes the slowly varying baseline:
    antenna mismatch, directional-coupler leakage and the direct
    transmitter-to-receiver coupling that otherwise dominates a near-field
    scan and buries the target return.

    No window and no padding are used here, unlike `to_time_domain` -- the
    transform has to be exactly invertible, and both would break that.
    """
    data = np.asarray(s_freq)
    if mode == FILTER_OFF:
        return data.astype(complex, copy=True)

    n_freq = data.shape[-1]
    freqs = np.asarray(freqs_hz, dtype=float).ravel()
    if freqs.size != n_freq:
        raise ValueError(
            f"frequency axis has {freqs.size} points but data has {n_freq}"
        )

    df = frequency_step(freqs)
    delays = circular_delays(n_freq, df)
    mask = filter_mask(delays, mode, cutoff_s, transition)

    delay_domain = np.fft.ifft(data, axis=-1)
    return np.fft.fft(delay_domain * mask, axis=-1)


def suggested_cutoff(freqs_hz) -> float:
    """A sane starting cutoff: halfway up the filterable delay range.

    Far enough out that a low-pass filter does not gut the data on first use,
    close enough in that the control visibly does something.
    """
    return max_filter_delay(freqs_hz) / 2.0


# ==========================================================================
# Display transforms (the phase view, and the rest)
# ==========================================================================

def to_display(values, mode: str, axis: int = -1) -> np.ndarray:
    """Convert complex data to the real quantity being plotted.

    `axis` is only consulted for `DISPLAY_PHASE_UNWRAPPED`, which needs a whole
    sweep rather than a single sample -- see `SWEEP_DEPENDENT_MODES`.
    """
    data = np.asarray(values)

    if mode == DISPLAY_MAGNITUDE:
        return np.abs(data)
    if mode == DISPLAY_MAGNITUDE_DB:
        return 20.0 * np.log10(np.maximum(np.abs(data), DB_FLOOR))
    if mode == DISPLAY_PHASE_RAD:
        return np.angle(data)
    if mode == DISPLAY_PHASE_DEG:
        return np.degrees(np.angle(data))
    if mode == DISPLAY_PHASE_UNWRAPPED:
        return np.degrees(np.unwrap(np.angle(data), axis=axis))
    if mode == DISPLAY_REAL:
        return np.real(data)
    if mode == DISPLAY_IMAGINARY:
        return np.imag(data)
    raise ValueError(f"unknown display mode {mode!r}; expected one of {DISPLAY_MODES}")


def display_units(mode: str, domain_is_time: bool = False) -> str:
    """Axis label for a display mode. `domain_is_time` is accepted so callers
    do not have to special-case the FFT view; the units are the same either way
    because the transform preserves the quantity being measured."""
    del domain_is_time
    if mode == DISPLAY_MAGNITUDE_DB:
        return "dB"
    if mode in (DISPLAY_PHASE_DEG, DISPLAY_PHASE_UNWRAPPED):
        return "deg"
    if mode == DISPLAY_PHASE_RAD:
        return "rad"
    return "linear"


def is_phase_mode(mode: str) -> bool:
    return mode in (DISPLAY_PHASE_DEG, DISPLAY_PHASE_UNWRAPPED, DISPLAY_PHASE_RAD)
