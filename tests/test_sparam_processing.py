"""Signal processing behind the FFT, filter and phase views.

These are physics assertions, not smoke tests. A reflection injected at a known
delay must come back out at that delay; a filter told to remove long paths must
actually remove them and leave the short ones alone. Getting this subtly wrong
produces a plausible-looking image of the wrong thing, which is worse than a
crash -- so the tests work from synthetic data whose right answer is known in
closed form.
"""

import numpy as np
import pytest

from scanner import sparam_processing as sp

pytestmark = pytest.mark.geometry


def sweep(start_ghz=1.0, stop_ghz=11.0, points=201):
    """A uniform frequency sweep in Hz."""
    return np.linspace(start_ghz * 1e9, stop_ghz * 1e9, points)


def reflection(freqs_hz, delay_s, amplitude=1.0):
    """An ideal point reflector at `delay_s`: a linear phase ramp in frequency."""
    return amplitude * np.exp(-2j * np.pi * np.asarray(freqs_hz) * delay_s)


class TestFrequencyAxis:
    def test_hz_passes_through_unchanged(self):
        freqs = sweep()
        assert np.allclose(sp.normalize_frequencies_to_hz(freqs), freqs)

    def test_ghz_is_scaled_up(self):
        """`Scanner.run_scan` writes /Frequencies/Range in GHz."""
        result = sp.normalize_frequencies_to_hz(np.linspace(1, 11, 201))
        assert result[0] == pytest.approx(1e9)
        assert result[-1] == pytest.approx(11e9)

    def test_an_empty_axis_is_handled(self):
        assert sp.normalize_frequencies_to_hz([]).size == 0

    def test_step_of_a_uniform_sweep(self):
        assert sp.frequency_step(sweep(1, 11, 101)) == pytest.approx(0.1e9)

    def test_a_segmented_sweep_is_rejected(self):
        """A gapped sweep would produce a confident, wrong range profile."""
        gapped = np.concatenate([np.linspace(1e9, 3e9, 50), np.linspace(6e9, 11e9, 50)])
        with pytest.raises(ValueError, match="uniform"):
            sp.frequency_step(gapped)

    def test_a_descending_sweep_is_rejected(self):
        with pytest.raises(ValueError):
            sp.frequency_step(sweep()[::-1])

    def test_a_single_point_is_rejected(self):
        with pytest.raises(ValueError):
            sp.frequency_step(np.array([1e9]))

    def test_tiny_grid_jitter_is_tolerated(self):
        """Real instruments do not report perfectly spaced floats."""
        freqs = sweep(1, 11, 101)
        jittered = freqs + np.random.default_rng(0).normal(0, freqs[1] * 1e-9, freqs.size)
        sp.frequency_step(jittered)  # must not raise

    def test_unambiguous_delay_is_one_over_step(self):
        freqs = sweep(1, 11, 101)  # 100 MHz steps -> 10 ns
        assert sp.max_unambiguous_delay(freqs) == pytest.approx(10e-9)

    def test_delay_resolution_is_one_over_bandwidth(self):
        assert sp.delay_resolution(sweep(1, 11, 201)) == pytest.approx(0.1e-9)


class TestRangeConversion:
    def test_two_way_halves_the_distance(self):
        # 1 ns round trip is 15 cm away, not 30.
        assert sp.time_to_range(1e-9) == pytest.approx(0.1499, abs=1e-4)

    def test_one_way_does_not(self):
        assert sp.time_to_range(1e-9, two_way=False) == pytest.approx(0.2998, abs=1e-4)

    def test_velocity_factor_shortens_the_range(self):
        """In a dielectric the wave is slower, so the same delay is less distance."""
        in_air = sp.time_to_range(1e-9)
        in_material = sp.time_to_range(1e-9, velocity_factor=1 / np.sqrt(4.0))
        assert in_material == pytest.approx(in_air / 2)

    def test_zero_delay_is_zero_range(self):
        assert sp.time_to_range(0.0) == 0.0


class TestWindows:
    @pytest.mark.parametrize("name", sp.WINDOW_NAMES)
    def test_every_named_window_has_the_right_length(self, name):
        assert len(sp.window_values(name, 64)) == 64

    def test_none_is_rectangular(self):
        assert np.all(sp.window_values(sp.WINDOW_NONE, 32) == 1.0)

    def test_hann_tapers_to_the_edges(self):
        w = sp.window_values(sp.WINDOW_HANN, 65, normalize=False)
        assert w[0] == pytest.approx(0.0, abs=1e-12)
        assert w[-1] == pytest.approx(0.0, abs=1e-12)
        assert w[32] == pytest.approx(1.0)

    @pytest.mark.parametrize("name", sp.WINDOW_NAMES)
    def test_windows_are_normalised_to_unit_coherent_gain(self, name):
        """So switching window changes sidelobes, not the amplitude scale."""
        assert sp.window_values(name, 128).mean() == pytest.approx(1.0)

    def test_normalisation_can_be_turned_off(self):
        # Odd length so the Hann peak lands exactly on a sample.
        assert sp.window_values(sp.WINDOW_HANN, 65, normalize=False).max() == pytest.approx(1.0)
        assert sp.window_values(sp.WINDOW_HANN, 65, normalize=False).mean() < 0.9

    def test_an_unknown_window_is_rejected(self):
        with pytest.raises(ValueError, match="unknown window"):
            sp.window_values("Kaiser", 16)


class TestTimeDomainTransform:
    """The FFT view."""

    @pytest.mark.parametrize("delay_ns", [0.5, 2.0, 5.0, 8.0])
    def test_a_reflector_appears_at_its_own_delay(self, delay_ns):
        freqs = sweep(1, 11, 401)
        times, response = sp.to_time_domain(
            reflection(freqs, delay_ns * 1e-9), freqs, pad_factor=8
        )
        peak_ns = times[np.argmax(np.abs(response))] * 1e9
        # Within one resolution cell (1/bandwidth = 0.1 ns).
        assert peak_ns == pytest.approx(delay_ns, abs=0.1)

    def test_two_reflectors_produce_two_peaks(self):
        freqs = sweep(1, 11, 401)
        signal = reflection(freqs, 1e-9) + 0.5 * reflection(freqs, 6e-9)
        times, response = sp.to_time_domain(signal, freqs, pad_factor=8)
        magnitude = np.abs(response)

        def peak_near(target_ns):
            window = np.abs(times * 1e9 - target_ns) < 0.5
            return magnitude[window].max()

        assert peak_near(1.0) == pytest.approx(1.0, rel=0.1)
        assert peak_near(6.0) == pytest.approx(0.5, rel=0.1)

    def test_amplitude_is_independent_of_padding(self):
        """Padding interpolates; it must not change how tall a peak is."""
        freqs = sweep(1, 11, 64)
        flat = np.ones(64)
        peaks = [
            np.abs(sp.to_time_domain(flat, freqs, window=sp.WINDOW_NONE, pad_factor=p)[1]).max()
            for p in (1, 2, 4, 8)
        ]
        assert peaks == pytest.approx([1.0] * 4)

    @pytest.mark.parametrize("window", sp.WINDOW_NAMES)
    def test_amplitude_is_independent_of_the_window(self, window):
        """Choosing a window trades resolution for sidelobes. It must not
        rescale the data, or the range profile's amplitude would depend on a
        display setting."""
        freqs = sweep(1, 11, 256)
        _, response = sp.to_time_domain(
            reflection(freqs, 0.0), freqs, window=window, pad_factor=4
        )
        assert np.abs(response).max() == pytest.approx(1.0, rel=0.02)

    def test_padding_only_refines_the_axis(self):
        freqs = sweep(1, 11, 101)
        coarse, _ = sp.to_time_domain(np.ones(101), freqs, pad_factor=1)
        fine, _ = sp.to_time_domain(np.ones(101), freqs, pad_factor=4)
        assert len(fine) == 4 * len(coarse)
        # Both span the same total delay.
        assert fine[-1] + (fine[1] - fine[0]) == pytest.approx(
            coarse[-1] + (coarse[1] - coarse[0])
        )

    def test_the_time_axis_spans_the_unambiguous_delay(self):
        freqs = sweep(1, 11, 101)
        times, _ = sp.to_time_domain(np.ones(101), freqs, pad_factor=1)
        step = times[1] - times[0]
        assert times[-1] + step == pytest.approx(sp.max_unambiguous_delay(freqs))

    def test_a_whole_scan_transforms_in_one_call(self):
        """The visualizer transforms every measurement point at once."""
        freqs = sweep(1, 11, 101)
        scan = np.stack([reflection(freqs, d * 1e-9) for d in (1, 2, 3, 4, 5)])
        times, response = sp.to_time_domain(scan, freqs, pad_factor=4)

        assert response.shape == (5, 101 * 4)
        for row, expected_ns in enumerate((1, 2, 3, 4, 5)):
            peak_ns = times[np.argmax(np.abs(response[row]))] * 1e9
            assert peak_ns == pytest.approx(expected_ns, abs=0.15)

    def test_windowing_suppresses_sidelobes(self):
        """The point of the window control: a rectangular window smears a
        strong reflection across the whole range axis."""
        freqs = sweep(1, 11, 201)
        signal = reflection(freqs, 3e-9)

        def worst_sidelobe(window):
            times, response = sp.to_time_domain(signal, freqs, window=window, pad_factor=8)
            magnitude = np.abs(response)
            far = np.abs(times * 1e9 - 3.0) > 1.0  # away from the main lobe
            return magnitude[far].max() / magnitude.max()

        assert worst_sidelobe(sp.WINDOW_HANN) < worst_sidelobe(sp.WINDOW_NONE) / 5

    def test_a_mismatched_frequency_axis_is_rejected(self):
        with pytest.raises(ValueError, match="frequency axis"):
            sp.to_time_domain(np.ones(50), sweep(1, 11, 101))

    def test_pad_factor_must_be_at_least_one(self):
        with pytest.raises(ValueError, match="pad_factor"):
            sp.to_time_domain(np.ones(101), sweep(1, 11, 101), pad_factor=0)


class TestFilterMask:
    def test_off_is_all_ones(self):
        delays = np.linspace(0, 10e-9, 50)
        assert np.all(sp.filter_mask(delays, sp.FILTER_OFF, 1e-9) == 1.0)

    def test_low_and_high_pass_are_complementary(self):
        """Nothing is lost or double-counted between the two modes."""
        delays = np.linspace(0, 10e-9, 50)
        low = sp.filter_mask(delays, sp.FILTER_LOW_PASS, 4e-9)
        high = sp.filter_mask(delays, sp.FILTER_HIGH_PASS, 4e-9)
        assert np.allclose(low + high, 1.0)

    def test_low_pass_keeps_short_delays_and_drops_long_ones(self):
        delays = np.array([0.0, 1e-9, 9e-9])
        mask = sp.filter_mask(delays, sp.FILTER_LOW_PASS, 4e-9)
        assert mask[0] == pytest.approx(1.0)
        assert mask[1] == pytest.approx(1.0)
        assert mask[2] == pytest.approx(0.0)

    def test_high_pass_does_the_opposite(self):
        delays = np.array([0.0, 1e-9, 9e-9])
        mask = sp.filter_mask(delays, sp.FILTER_HIGH_PASS, 4e-9)
        assert mask[0] == pytest.approx(0.0)
        assert mask[2] == pytest.approx(1.0)

    def test_the_edge_is_gradual_by_default(self):
        """A brick wall in delay rings in frequency and looks like a resonance."""
        delays = np.linspace(0, 10e-9, 2001)
        mask = sp.filter_mask(delays, sp.FILTER_LOW_PASS, 4e-9, transition=0.25)
        partial = mask[(mask > 0.01) & (mask < 0.99)]
        assert partial.size > 10, "the roll-off should span many bins"

    def test_zero_transition_is_a_brick_wall(self):
        delays = np.linspace(0, 10e-9, 2001)
        mask = sp.filter_mask(delays, sp.FILTER_LOW_PASS, 4e-9, transition=0.0)
        assert set(np.unique(mask)) <= {0.0, 1.0}

    def test_the_mask_never_leaves_zero_to_one(self):
        delays = np.linspace(0, 10e-9, 500)
        for mode in (sp.FILTER_LOW_PASS, sp.FILTER_HIGH_PASS):
            mask = sp.filter_mask(delays, mode, 4e-9)
            assert mask.min() >= 0.0 and mask.max() <= 1.0

    def test_an_unknown_mode_is_rejected(self):
        with pytest.raises(ValueError, match="unknown filter mode"):
            sp.filter_mask(np.zeros(4), "Band Pass", 1e-9)

    def test_a_negative_cutoff_is_rejected(self):
        with pytest.raises(ValueError, match="cutoff"):
            sp.filter_mask(np.zeros(4), sp.FILTER_LOW_PASS, -1e-9)


class TestCircularDelays:
    def test_bin_zero_is_zero_delay(self):
        assert sp.circular_delays(64, 1e6)[0] == 0.0

    def test_delays_fold_symmetrically(self):
        """Bin k and bin n-k are the same delay with opposite sign, so a
        low-pass keeps short delays of either sign instead of half the trace."""
        delays = sp.circular_delays(64, 1e6)
        assert delays[1] == pytest.approx(delays[63])
        assert delays[10] == pytest.approx(delays[54])

    def test_the_maximum_is_at_the_midpoint(self):
        delays = sp.circular_delays(64, 1e6)
        assert np.argmax(delays) == 32


class TestApplyFilter:
    """The filter view, end to end."""

    def test_off_returns_the_input(self):
        freqs = sweep()
        signal = reflection(freqs, 2e-9)
        assert np.allclose(sp.apply_filter(signal, freqs, sp.FILTER_OFF, 1e-9), signal)

    def test_a_cutoff_beyond_the_span_is_a_no_op_for_low_pass(self):
        freqs = sweep()
        signal = reflection(freqs, 2e-9)
        span = sp.max_unambiguous_delay(freqs)
        filtered = sp.apply_filter(signal, freqs, sp.FILTER_LOW_PASS, span, transition=0.0)
        assert np.allclose(filtered, signal)

    def test_low_and_high_pass_sum_back_to_the_original(self):
        """The two halves reconstruct the input: the filter loses nothing."""
        freqs = sweep()
        signal = reflection(freqs, 1e-9) + 0.6 * reflection(freqs, 7e-9)
        low = sp.apply_filter(signal, freqs, sp.FILTER_LOW_PASS, 4e-9)
        high = sp.apply_filter(signal, freqs, sp.FILTER_HIGH_PASS, 4e-9)
        assert np.allclose(low + high, signal)

    def test_low_pass_removes_a_late_reflection(self):
        freqs = sweep(1, 11, 401)
        signal = reflection(freqs, 1e-9) + reflection(freqs, 8e-9)
        filtered = sp.apply_filter(signal, freqs, sp.FILTER_LOW_PASS, 4e-9)

        times, response = sp.to_time_domain(filtered, freqs, pad_factor=8)
        magnitude = np.abs(response)
        near = magnitude[np.abs(times * 1e9 - 1.0) < 0.5].max()
        far = magnitude[np.abs(times * 1e9 - 8.0) < 0.5].max()

        assert near > 0.9, "the short-delay reflection must survive"
        assert far < 0.01, "the long-delay reflection must be gone"

    def test_high_pass_removes_the_coupling_baseline(self):
        """The near-field case: direct antenna coupling buries the target."""
        freqs = sweep(1, 11, 401)
        coupling = 5.0 * reflection(freqs, 0.1e-9)
        target = reflection(freqs, 6e-9)
        filtered = sp.apply_filter(coupling + target, freqs, sp.FILTER_HIGH_PASS, 3e-9)

        times, response = sp.to_time_domain(filtered, freqs, pad_factor=8)
        magnitude = np.abs(response)
        early = magnitude[times * 1e9 < 1.0].max()
        late = magnitude[np.abs(times * 1e9 - 6.0) < 0.5].max()

        assert late > 0.9, "the target must survive"
        assert early < 0.05 * late, "the coupling must be suppressed"

    def test_a_whole_scan_filters_in_one_call(self):
        # 401 points -> 40 ns unambiguous span, so 8 ns is comfortably inside
        # the filterable range (see test_delays_beyond_half_the_span_alias).
        freqs = sweep(1, 11, 401)
        scan = np.stack([reflection(freqs, d * 1e-9) for d in (1, 2, 8)])
        filtered = sp.apply_filter(scan, freqs, sp.FILTER_LOW_PASS, 4e-9)
        assert filtered.shape == scan.shape

        _, response = sp.to_time_domain(filtered, freqs, pad_factor=4)
        peaks = np.abs(response).max(axis=1)
        assert peaks[0] > 0.9 and peaks[1] > 0.9, "short delays kept"
        assert peaks[2] < 0.05, "long delay removed"

    def test_the_output_stays_complex(self):
        """Downstream views take angle() and real(); a real array breaks them."""
        freqs = sweep()
        filtered = sp.apply_filter(reflection(freqs, 2e-9), freqs, sp.FILTER_LOW_PASS, 4e-9)
        assert np.iscomplexobj(filtered)

    def test_a_segmented_sweep_is_rejected(self):
        gapped = np.concatenate([np.linspace(1e9, 3e9, 50), np.linspace(6e9, 11e9, 50)])
        with pytest.raises(ValueError, match="uniform"):
            sp.apply_filter(np.ones(100), gapped, sp.FILTER_LOW_PASS, 1e-9)

    def test_suggested_cutoff_sits_inside_the_filterable_range(self):
        freqs = sweep()
        cutoff = sp.suggested_cutoff(freqs)
        assert 0 < cutoff < sp.max_filter_delay(freqs)

    def test_max_filter_delay_is_half_the_unambiguous_span(self):
        freqs = sweep(1, 11, 101)
        assert sp.max_filter_delay(freqs) == pytest.approx(
            sp.max_unambiguous_delay(freqs) / 2
        )

    def test_delays_beyond_half_the_span_alias_onto_short_ones(self):
        """A limit of the transform, asserted so nobody rediscovers it as a bug.

        `circular_delays` folds bin k onto bin n-k, so the filter's delay axis
        only runs to half the unambiguous span. With 101 points over 1-11 GHz
        the span is 10 ns, and an 8 ns reflection folds onto 2 ns -- a 4 ns
        low-pass keeps it, which looks wrong until you know why.

        This is exactly why the visualizer clamps its cutoff control to
        `max_filter_delay` and why a longer sweep is the real fix.
        """
        freqs = sweep(1, 11, 101)
        assert sp.max_unambiguous_delay(freqs) == pytest.approx(10e-9)
        assert sp.max_filter_delay(freqs) == pytest.approx(5e-9)

        signal = reflection(freqs, 8e-9)
        kept = sp.apply_filter(signal, freqs, sp.FILTER_LOW_PASS, 4e-9)
        assert np.abs(kept).max() > 0.9, "the aliased reflection survives"

        # With a finer frequency step the span doubles and the same reflection
        # is where you would expect it, so the filter removes it. The check is
        # made in the time domain: a delay that does not land exactly on a DFT
        # bin leaks across the sweep, so the residual |S(f)| stays non-zero
        # even though the reflection itself is gone.
        finer = sweep(1, 11, 401)
        assert sp.max_filter_delay(finer) == pytest.approx(20e-9)
        removed = sp.apply_filter(reflection(finer, 8e-9), finer,
                                  sp.FILTER_LOW_PASS, 4e-9)
        times, response = sp.to_time_domain(removed, finer, pad_factor=8)
        peak_at_8ns = np.abs(response)[np.abs(times * 1e9 - 8.0) < 0.5].max()
        assert peak_at_8ns < 0.01


class TestDisplayTransforms:
    """The phase view, and its neighbours."""

    def test_magnitude(self):
        assert sp.to_display(np.array([3 + 4j]), sp.DISPLAY_MAGNITUDE)[0] == pytest.approx(5.0)

    def test_magnitude_db(self):
        value = sp.to_display(np.array([0.1 + 0j]), sp.DISPLAY_MAGNITUDE_DB)[0]
        assert value == pytest.approx(-20.0)

    def test_db_of_zero_is_floored_not_infinite(self):
        """One zero sample would otherwise drag the whole colour scale to -inf."""
        value = sp.to_display(np.array([0 + 0j]), sp.DISPLAY_MAGNITUDE_DB)[0]
        assert np.isfinite(value)
        assert value < -200

    def test_phase_in_degrees(self):
        assert sp.to_display(np.array([1j]), sp.DISPLAY_PHASE_DEG)[0] == pytest.approx(90.0)

    def test_phase_in_radians(self):
        assert sp.to_display(np.array([1j]), sp.DISPLAY_PHASE_RAD)[0] == pytest.approx(np.pi / 2)

    def test_real_and_imaginary(self):
        value = np.array([3 - 4j])
        assert sp.to_display(value, sp.DISPLAY_REAL)[0] == pytest.approx(3.0)
        assert sp.to_display(value, sp.DISPLAY_IMAGINARY)[0] == pytest.approx(-4.0)

    def test_wrapped_phase_stays_within_half_a_turn(self):
        freqs = sweep(1, 11, 401)
        wrapped = sp.to_display(reflection(freqs, 3e-9), sp.DISPLAY_PHASE_DEG)
        assert np.all(np.abs(wrapped) <= 180.0 + 1e-9)

    def test_unwrapped_phase_escapes_it(self):
        """A 3 ns delay across 10 GHz is many full turns; wrapped phase hides
        that, which is the whole reason for the unwrapped mode."""
        freqs = sweep(1, 11, 401)
        unwrapped = sp.to_display(reflection(freqs, 3e-9), sp.DISPLAY_PHASE_UNWRAPPED)
        assert np.abs(unwrapped).max() > 1000

    def test_unwrapped_phase_slope_recovers_the_delay(self):
        """The physical check: d(phase)/df = -2*pi*tau."""
        freqs = sweep(1, 11, 401)
        delay = 2.5e-9
        radians = np.radians(
            sp.to_display(reflection(freqs, delay), sp.DISPLAY_PHASE_UNWRAPPED)
        )
        slope = np.polyfit(freqs, radians, 1)[0]
        assert -slope / (2 * np.pi) == pytest.approx(delay, rel=1e-6)

    def test_unwrapped_phase_is_monotonic_for_a_pure_delay(self):
        freqs = sweep(1, 11, 401)
        unwrapped = sp.to_display(reflection(freqs, 2e-9), sp.DISPLAY_PHASE_UNWRAPPED)
        assert np.all(np.diff(unwrapped) < 0)

    def test_unwrapping_runs_along_the_frequency_axis_of_a_scan(self):
        """Unwrapping across points instead of across frequency would mix
        unrelated pixels together and produce nonsense."""
        freqs = sweep(1, 11, 201)
        scan = np.stack([reflection(freqs, d * 1e-9) for d in (1, 3, 5)])
        unwrapped = sp.to_display(scan, sp.DISPLAY_PHASE_UNWRAPPED, axis=-1)

        assert unwrapped.shape == scan.shape
        for row, delay_ns in enumerate((1, 3, 5)):
            slope = np.polyfit(freqs, np.radians(unwrapped[row]), 1)[0]
            assert -slope / (2 * np.pi) == pytest.approx(delay_ns * 1e-9, rel=1e-6)

    def test_wrapped_and_unwrapped_agree_modulo_a_turn(self):
        freqs = sweep(1, 11, 401)
        signal = reflection(freqs, 2e-9)
        wrapped = sp.to_display(signal, sp.DISPLAY_PHASE_DEG)
        unwrapped = sp.to_display(signal, sp.DISPLAY_PHASE_UNWRAPPED)
        residue = (unwrapped - wrapped) % 360.0
        # 359.9999... is as close to a whole turn as 0.0000...; fold both ends.
        assert np.allclose(np.minimum(residue, 360.0 - residue), 0.0, atol=1e-6)

    @pytest.mark.parametrize("mode", sp.DISPLAY_MODES)
    def test_every_mode_returns_real_values_of_the_right_shape(self, mode):
        rng = np.random.default_rng(0)
        data = rng.random((7, 32)) + 1j * rng.random((7, 32))
        result = sp.to_display(data, mode)
        assert result.shape == data.shape
        assert not np.iscomplexobj(result)

    def test_an_unknown_mode_is_rejected(self):
        with pytest.raises(ValueError, match="unknown display mode"):
            sp.to_display(np.ones(4), "Group Delay")

    def test_sweep_dependent_modes_are_declared(self):
        """The visualizer uses this list to decide whether it can transform a
        single slider column or has to do the whole matrix."""
        assert sp.DISPLAY_PHASE_UNWRAPPED in sp.SWEEP_DEPENDENT_MODES
        assert sp.DISPLAY_MAGNITUDE not in sp.SWEEP_DEPENDENT_MODES

    @pytest.mark.parametrize("mode", sp.DISPLAY_MODES)
    def test_every_mode_has_a_unit_label(self, mode):
        assert isinstance(sp.display_units(mode), str)
        assert sp.display_units(mode)

    def test_phase_modes_are_identified(self):
        assert sp.is_phase_mode(sp.DISPLAY_PHASE_DEG)
        assert sp.is_phase_mode(sp.DISPLAY_PHASE_UNWRAPPED)
        assert not sp.is_phase_mode(sp.DISPLAY_MAGNITUDE)


class TestPipelineComposition:
    """Filter then FFT is how the visualizer chains them; the order matters."""

    def test_filtering_before_transforming_gates_the_range_profile(self):
        freqs = sweep(1, 11, 401)
        signal = reflection(freqs, 1e-9) + reflection(freqs, 7e-9)

        filtered = sp.apply_filter(signal, freqs, sp.FILTER_HIGH_PASS, 4e-9)
        times, response = sp.to_time_domain(filtered, freqs, pad_factor=8)

        magnitude = np.abs(response)
        assert magnitude[np.abs(times * 1e9 - 1.0) < 0.5].max() < 0.02
        assert magnitude[np.abs(times * 1e9 - 7.0) < 0.5].max() > 0.9

    def test_a_filter_does_not_move_a_surviving_reflection(self):
        """Gating must not shift the target it keeps -- that would corrupt the
        range reading the operator takes off the axis."""
        freqs = sweep(1, 11, 401)
        signal = reflection(freqs, 2e-9)

        def peak_ns(values):
            times, response = sp.to_time_domain(values, freqs, pad_factor=8)
            return times[np.argmax(np.abs(response))] * 1e9

        unfiltered = peak_ns(signal)
        filtered = peak_ns(sp.apply_filter(signal, freqs, sp.FILTER_LOW_PASS, 6e-9))
        assert filtered == pytest.approx(unfiltered, abs=0.05)
