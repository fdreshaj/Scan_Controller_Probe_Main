"""The S-parameter visualizer window: FFT, filter and phase views.

These drive the real `VisualizerWindow` against a synthetic HDF5 scan whose
contents are known exactly -- a flat antenna-coupling term at 0.2 ns everywhere
plus a localised target at 3 ns near the middle of the grid. That lets the
tests assert on physics rather than on pixels: the 3 ns range bin must light up
where the target is, the coupling bin must be spatially flat, and a high-pass
filter must remove the coupling and leave the target.

Requires PySide6 and h5py; skips cleanly without them. Runs offscreen -- no
display, no window ever appears.
"""

from __future__ import annotations

import os

import numpy as np
import pytest

# A real display is never needed, and CI has none.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("h5py", reason="pip install -r requirements-dev.txt")
pytest.importorskip("PySide6", reason="pip install PySide6")

import h5py  # noqa: E402

from scanner import sparam_processing as sp  # noqa: E402
import scanner.S_param_visualizer as viz  # noqa: E402

pytestmark = pytest.mark.contract

#: Where the synthetic target and the synthetic antenna coupling sit.
TARGET_DELAY_NS = 3.0
COUPLING_DELAY_NS = 0.2
TARGET_XY = (8.0, 6.0)


def write_scan(path, nx=8, ny=6, n_freq=201, points_written=None):
    """A synthetic scan file in the layout `Scanner.run_scan` produces.

    Frequencies are written in **GHz**, as the real writer does, so the tests
    exercise the unit normalisation rather than sidestepping it.
    """
    freqs_ghz = np.linspace(1.0, 11.0, n_freq)
    freqs_hz = freqs_ghz * 1e9

    xs, ys, real, imag = [], [], [], []
    for iy in range(ny):
        for ix in range(nx):
            x, y = ix * 2.0, iy * 2.0
            # A Gaussian blob of target reflectivity centred on TARGET_XY.
            strength = np.exp(
                -(((x - TARGET_XY[0]) ** 2 + (y - TARGET_XY[1]) ** 2) / 8.0)
            )
            trace = (
                0.9 * np.exp(-2j * np.pi * freqs_hz * COUPLING_DELAY_NS * 1e-9)
                + strength * np.exp(-2j * np.pi * freqs_hz * TARGET_DELAY_NS * 1e-9)
            )
            xs.append(x)
            ys.append(y)
            real.append(trace.real)
            imag.append(trace.imag)

    real = np.array(real)
    imag = np.array(imag)
    if points_written is not None:
        # Simulate a scan still in progress: the file is pre-allocated and
        # zero-padded past the last written point.
        real[points_written:] = 0.0
        imag[points_written:] = 0.0

    with h5py.File(path, "w") as f:
        f.create_dataset("/Frequencies/Range", data=freqs_ghz)
        f.create_dataset("/Coords/x_data", data=np.array(xs))
        f.create_dataset("/Coords/y_data", data=np.array(ys))
        f.create_dataset("/Data/S11_real", data=real)
        f.create_dataset("/Data/S11_imag", data=imag)
    return path


@pytest.fixture
def window(qapp, tmp_path, request):
    """A visualizer on a fresh synthetic scan, with its polling timer stopped."""
    kwargs = getattr(request, "param", {})
    path = write_scan(tmp_path / "scan.h5", **kwargs)
    w = viz.VisualizerWindow(str(path))
    w.timer.stop()  # no background polling during a test
    yield w
    w.play_timer.stop()
    w.close()


def bin_nearest(axis, target):
    return int(np.argmin(np.abs(np.asarray(axis) - target)))


class TestLoading:
    def test_the_s_parameter_is_discovered(self, window):
        assert window.available_sparams == ["S11"]

    def test_frequencies_are_normalised_to_hz(self, window):
        """The file stores GHz. Every transform needs Hz, and the old label
        code divided the stored value by 1e9 a second time."""
        assert window.freqs_hz[0] == pytest.approx(1e9)
        assert window.freqs_hz[-1] == pytest.approx(11e9)

    def test_the_frequency_label_reads_correctly(self, window):
        window.freq_slider.setValue(0)
        assert "1.0000 GHz" in window.freq_value_label.text()

    def test_the_grid_is_detected(self, window):
        assert window.grid_label.text() == "Grid: 8 × 6"

    def test_the_heatmap_is_drawn(self, window):
        assert len(window.scene.items()) == 1


class TestFFTView:
    def test_switching_domain_relabels_the_slider(self, window):
        window.domain_combo.setCurrentText(viz.DOMAIN_TIME)
        assert window.axis_name_label.text() == "Range:"
        assert "ns" in window.freq_value_label.text()

    def test_the_label_shows_delay_and_two_way_distance(self, window):
        window.domain_combo.setCurrentText(viz.DOMAIN_TIME)
        axis = window.current_axis_values()
        window.freq_slider.setValue(bin_nearest(axis, 3e-9))
        text = window.freq_value_label.text()
        assert "ns" in text and "cm two-way" in text

    def test_the_axis_becomes_delay_in_seconds(self, window):
        window.domain_combo.setCurrentText(viz.DOMAIN_TIME)
        axis = window.current_axis_values()
        assert axis[0] == pytest.approx(0.0)
        assert axis[-1] < sp.max_unambiguous_delay(window.freqs_hz)

    def test_the_target_range_bin_localises_the_target(self, window):
        """The point of the FFT view: the 3 ns slice shows where the target is,
        which no single frequency slice can."""
        window.domain_combo.setCurrentText(viz.DOMAIN_TIME)
        window.datatype_combo.setCurrentText(sp.DISPLAY_MAGNITUDE)
        axis = window.current_axis_values()
        window.freq_slider.setValue(bin_nearest(axis, TARGET_DELAY_NS * 1e-9))

        values = window._display_slice()
        brightest = int(np.argmax(values))
        assert window.point_coordinates(brightest) == TARGET_XY

    def test_the_coupling_range_bin_is_spatially_flat(self, window):
        """Antenna coupling is identical at every pixel, so its range bin
        carries no spatial structure -- that is what makes it removable."""
        window.domain_combo.setCurrentText(viz.DOMAIN_TIME)
        window.datatype_combo.setCurrentText(sp.DISPLAY_MAGNITUDE)
        axis = window.current_axis_values()

        window.freq_slider.setValue(bin_nearest(axis, COUPLING_DELAY_NS * 1e-9))
        coupling_spread = float(np.std(window._display_slice()))
        window.freq_slider.setValue(bin_nearest(axis, TARGET_DELAY_NS * 1e-9))
        target_spread = float(np.std(window._display_slice()))

        # Not exactly zero: a finite sweep leaks a little of the target into
        # every other bin. Three orders of magnitude apart is the real claim.
        assert target_spread > 0.01
        assert coupling_spread < target_spread / 1000

    def test_each_range_bin_renders_a_different_image(self, window):
        window.domain_combo.setCurrentText(viz.DOMAIN_TIME)
        hashes = set()
        for index in (0, 10, 30, 60):
            window.freq_slider.setValue(index)
            item = window.scene.items()[0]
            hashes.add(hash(item.pixmap().toImage().bits().tobytes()))
        assert len(hashes) == 4

    @pytest.mark.parametrize("window_name", sp.WINDOW_NAMES)
    def test_every_window_function_renders(self, window, window_name):
        window.domain_combo.setCurrentText(viz.DOMAIN_TIME)
        window.window_combo.setCurrentText(window_name)
        assert window._display_slice() is not None

    def test_switching_back_to_frequency_restores_the_axis(self, window):
        window.domain_combo.setCurrentText(viz.DOMAIN_TIME)
        window.domain_combo.setCurrentText(viz.DOMAIN_FREQUENCY)
        assert window.axis_name_label.text() == "Frequency:"
        assert np.allclose(window.current_axis_values(), window.freqs_hz)


class TestFilterView:
    def test_the_cutoff_control_follows_the_filter_mode(self, window):
        assert not window.cutoff_spin.isEnabled()
        window.filter_combo.setCurrentText(sp.FILTER_LOW_PASS)
        assert window.cutoff_spin.isEnabled()
        window.filter_combo.setCurrentText(sp.FILTER_OFF)
        assert not window.cutoff_spin.isEnabled()

    def test_the_cutoff_is_clamped_to_the_filterable_range(self, window):
        """Past half the unambiguous span the delay bins fold, so a larger
        cutoff would silently do nothing."""
        expected = sp.max_filter_delay(window.freqs_hz) * 1e9
        assert window.cutoff_spin.maximum() == pytest.approx(expected)

    def test_the_default_cutoff_is_inside_that_range(self, window):
        assert 0 < window.cutoff_spin.value() < window.cutoff_spin.maximum()

    def test_the_cutoff_is_shown_as_a_distance(self, window):
        window.filter_combo.setCurrentText(sp.FILTER_LOW_PASS)
        window.cutoff_spin.setValue(2.0)
        assert "cm two-way" in window.cutoff_range_label.text()

    def test_high_pass_removes_the_coupling(self, window):
        """The near-field problem: coupling is 0.9 and swamps the target."""
        window.datatype_combo.setCurrentText(sp.DISPLAY_MAGNITUDE)
        window.freq_slider.setValue(100)
        unfiltered_mean = float(np.mean(window._display_slice()))

        window.filter_combo.setCurrentText(sp.FILTER_HIGH_PASS)
        window.cutoff_spin.setValue(1.5)
        filtered_mean = float(np.mean(window._display_slice()))

        assert unfiltered_mean > 0.8
        assert filtered_mean < unfiltered_mean / 3

    def test_low_pass_keeps_the_flat_coupling(self, window):
        window.datatype_combo.setCurrentText(sp.DISPLAY_MAGNITUDE)
        window.freq_slider.setValue(100)
        window.filter_combo.setCurrentText(sp.FILTER_LOW_PASS)
        window.cutoff_spin.setValue(1.5)

        window.filter_combo.setCurrentText(sp.FILTER_OFF)
        unfiltered_spread = float(np.std(window._display_slice()))
        window.filter_combo.setCurrentText(sp.FILTER_LOW_PASS)

        values = window._display_slice()
        assert float(np.mean(values)) == pytest.approx(0.9, abs=0.02)
        # The target's spatial structure is gone; only the flat coupling is
        # left, bar a little spectral leakage.
        assert float(np.std(values)) < unfiltered_spread / 1000

    def test_the_filter_composes_with_the_fft_view(self, window):
        """Filter first, then transform -- so gating shows up as a cleaned
        range profile rather than being applied twice."""
        window.domain_combo.setCurrentText(viz.DOMAIN_TIME)
        window.datatype_combo.setCurrentText(sp.DISPLAY_MAGNITUDE)
        window.filter_combo.setCurrentText(sp.FILTER_HIGH_PASS)
        window.cutoff_spin.setValue(1.5)

        axis = window.current_axis_values()
        window.freq_slider.setValue(bin_nearest(axis, COUPLING_DELAY_NS * 1e-9))
        coupling_peak = float(np.max(window._display_slice()))
        window.freq_slider.setValue(bin_nearest(axis, TARGET_DELAY_NS * 1e-9))
        target_peak = float(np.max(window._display_slice()))

        assert coupling_peak < 0.01
        assert target_peak > 0.3

    def test_changing_the_cutoff_changes_the_result(self, window):
        window.datatype_combo.setCurrentText(sp.DISPLAY_MAGNITUDE)
        window.filter_combo.setCurrentText(sp.FILTER_LOW_PASS)
        window.freq_slider.setValue(50)

        window.cutoff_spin.setValue(1.0)
        narrow = window._display_slice().copy()
        window.cutoff_spin.setValue(4.0)
        wide = window._display_slice().copy()

        assert not np.allclose(narrow, wide)


class TestPhaseView:
    def test_wrapped_phase_stays_within_half_a_turn(self, window):
        window.datatype_combo.setCurrentText(sp.DISPLAY_PHASE_DEG)
        window.freq_slider.setValue(200)
        assert np.all(np.abs(window._display_slice()) <= 180.0 + 1e-9)

    def test_unwrapped_phase_accumulates_past_a_turn(self, window):
        """A 3 ns delay across 10 GHz is many full turns. Wrapped phase hides
        that; the unwrapped mode is the only way to see the real ramp."""
        window.datatype_combo.setCurrentText(sp.DISPLAY_PHASE_UNWRAPPED)
        window.freq_slider.setValue(200)
        assert np.abs(window._display_slice()).max() > 360

    def test_unwrapping_runs_along_frequency_not_across_pixels(self, window):
        """Unwrapping across measurement points would mix unrelated pixels.
        The slope against frequency must recover the physical delay."""
        window.datatype_combo.setCurrentText(sp.DISPLAY_PHASE_UNWRAPPED)
        window._ensure_processed()
        matrix = sp.to_display(window._processed, sp.DISPLAY_PHASE_UNWRAPPED, axis=-1)

        # A corner pixel, far from the target, is almost pure coupling.
        corner = 0
        slope = np.polyfit(window.freqs_hz, np.radians(matrix[corner]), 1)[0]
        delay_ns = -slope / (2 * np.pi) * 1e9
        assert delay_ns == pytest.approx(COUPLING_DELAY_NS, abs=0.05)

    def test_phase_in_radians_is_bounded_by_pi(self, window):
        window.datatype_combo.setCurrentText(sp.DISPLAY_PHASE_RAD)
        window.freq_slider.setValue(120)
        assert np.all(np.abs(window._display_slice()) <= np.pi + 1e-9)

    def test_magnitude_db_is_finite_everywhere(self, window):
        window.datatype_combo.setCurrentText(sp.DISPLAY_MAGNITUDE_DB)
        window.freq_slider.setValue(100)
        assert np.all(np.isfinite(window._display_slice()))

    def test_switching_display_mode_invalidates_the_unwrap_cache(self, window):
        """The unwrapped matrix is cached; a mode change must not serve it up
        for a different mode."""
        window.datatype_combo.setCurrentText(sp.DISPLAY_PHASE_UNWRAPPED)
        window.freq_slider.setValue(150)
        unwrapped = window._display_slice().copy()

        window.datatype_combo.setCurrentText(sp.DISPLAY_PHASE_DEG)
        wrapped = window._display_slice().copy()

        assert not np.allclose(unwrapped, wrapped)
        assert np.all(np.abs(wrapped) <= 180.0 + 1e-9)

    @pytest.mark.parametrize("mode", sp.DISPLAY_MODES)
    def test_every_display_mode_renders(self, window, mode):
        window.datatype_combo.setCurrentText(mode)
        values = window._display_slice()
        assert values is not None
        assert values.shape == (len(window.all_x),)
        assert not np.iscomplexobj(values)


class TestTracePanel:
    def test_clicking_the_heatmap_selects_the_point_under_the_cursor(self, window):
        ix = bin_nearest(window.unique_x, TARGET_XY[0])
        iy = bin_nearest(window.unique_y, TARGET_XY[1])
        scale = window.heatmap_scale_factor

        # The renderer draws grid cell (ix, iy) at image column iy, row ix.
        window.on_heatmap_clicked(iy * scale + 1, ix * scale + 1)

        assert window.selected_point is not None
        assert window.point_coordinates(window.selected_point) == TARGET_XY

    def test_a_click_outside_the_image_is_ignored(self, window):
        window.on_heatmap_clicked(2, 2)
        before = window.selected_point
        window.on_heatmap_clicked(-100, -100)
        window.on_heatmap_clicked(1e6, 1e6)
        assert window.selected_point == before

    @pytest.mark.skipif(
        not viz.TRACE_PLOT_AVAILABLE, reason="matplotlib not installed"
    )
    def test_the_trace_plots_the_selected_point(self, window):
        window.on_heatmap_clicked(2, 2)
        window.trace_checkbox.setChecked(True)
        assert window.trace_axes.get_xlabel() == "Frequency (GHz)"
        assert len(window.trace_axes.lines) >= 1

    @pytest.mark.skipif(
        not viz.TRACE_PLOT_AVAILABLE, reason="matplotlib not installed"
    )
    def test_the_trace_follows_the_fft_view(self, window):
        window.on_heatmap_clicked(2, 2)
        window.trace_checkbox.setChecked(True)
        window.domain_combo.setCurrentText(viz.DOMAIN_TIME)
        assert window.trace_axes.get_xlabel() == "Delay (ns)"

    @pytest.mark.skipif(
        not viz.TRACE_PLOT_AVAILABLE, reason="matplotlib not installed"
    )
    def test_the_trace_overlays_filtered_against_unfiltered(self, window):
        """So the cutoff's effect is visible rather than inferred."""
        window.on_heatmap_clicked(2, 2)
        window.trace_checkbox.setChecked(True)
        window.filter_combo.setCurrentText(sp.FILTER_HIGH_PASS)

        labels = [line.get_label() for line in window.trace_axes.lines]
        assert "Unfiltered" in labels
        assert sp.FILTER_HIGH_PASS in labels

    @pytest.mark.skipif(
        not viz.TRACE_PLOT_AVAILABLE, reason="matplotlib not installed"
    )
    def test_the_trace_peaks_at_the_target_delay(self, window):
        """End-to-end: click the target pixel, gate out the coupling, and the
        range profile should peak at the delay the target was injected at."""
        ix = bin_nearest(window.unique_x, TARGET_XY[0])
        iy = bin_nearest(window.unique_y, TARGET_XY[1])
        scale = window.heatmap_scale_factor
        window.on_heatmap_clicked(iy * scale + 1, ix * scale + 1)

        window.trace_checkbox.setChecked(True)
        window.domain_combo.setCurrentText(viz.DOMAIN_TIME)
        window.datatype_combo.setCurrentText(sp.DISPLAY_MAGNITUDE)
        window.filter_combo.setCurrentText(sp.FILTER_HIGH_PASS)
        window.cutoff_spin.setValue(1.5)

        curve = [
            line for line in window.trace_axes.lines
            if line.get_label() == sp.FILTER_HIGH_PASS
        ][0]
        x, y = curve.get_xdata(), curve.get_ydata()
        assert x[np.argmax(y)] == pytest.approx(TARGET_DELAY_NS, abs=0.15)


class TestRendering:
    def test_the_vectorised_colormap_matches_get_color(self, qapp):
        """`create_heatmap_image` was rewritten from a per-pixel loop into a
        numpy path. It must produce exactly the same colours."""
        rng = np.random.default_rng(0)
        values = rng.random((16, 16))
        values[0, 0] = np.nan
        values[1, 1] = 0.0
        values[2, 2] = 1.0

        # A bare window is enough; no file needed for the colour maths.
        widget = viz.VisualizerWindow.__new__(viz.VisualizerWindow)
        for name in ("Jet", "Viridis", "Hot", "Cool", "Grayscale"):
            class _Combo:
                @staticmethod
                def currentText():
                    return name

            widget.colormap_combo = _Combo()
            fast = widget._colormap_rgb(values)
            for iy in range(values.shape[0]):
                for ix in range(values.shape[1]):
                    if np.isnan(values[iy, ix]):
                        expected = (128, 128, 128)
                    else:
                        colour = viz.VisualizerWindow.get_color(widget, values[iy, ix])
                        expected = (colour.red(), colour.green(), colour.blue())
                    assert tuple(int(c) for c in fast[iy, ix]) == expected, name

    def test_the_grid_mapping_matches_the_original_loop(self, window):
        data = np.arange(len(window.all_x), dtype=float)
        fast = window.map_to_grid(data)

        unique_x = np.sort(np.unique(window.all_x))
        unique_y = np.sort(np.unique(window.all_y))
        slow = np.full((len(unique_x), len(unique_y)), np.nan)
        for i in range(len(window.all_x)):
            ix = np.argmin(np.abs(unique_x - window.all_x[i]))
            iy = np.argmin(np.abs(unique_y - window.all_y[i]))
            slow[ix, iy] = data[i]

        assert np.array_equal(np.nan_to_num(fast, nan=-1), np.nan_to_num(slow, nan=-1))

    def test_the_image_is_scaled_by_the_scale_factor(self, window):
        pixmap = window.scene.items()[0].pixmap()
        scale = window.heatmap_scale_factor
        assert pixmap.width() == len(window.unique_y) * scale
        assert pixmap.height() == len(window.unique_x) * scale


class TestDegradedInputs:
    def test_a_segmented_sweep_reports_instead_of_guessing(self, qapp, tmp_path):
        """A gapped sweep breaks the DFT. Saying so beats drawing a confident
        picture of the wrong thing."""
        path = tmp_path / "gapped.h5"
        freqs = np.concatenate([np.linspace(1, 3, 50), np.linspace(6, 11, 50)])
        n_points = 12
        with h5py.File(path, "w") as f:
            f.create_dataset("/Frequencies/Range", data=freqs)
            f.create_dataset("/Coords/x_data", data=np.repeat(np.arange(4) * 2.0, 3))
            f.create_dataset("/Coords/y_data", data=np.tile(np.arange(3) * 2.0, 4))
            f.create_dataset("/Data/S11_real", data=np.ones((n_points, len(freqs))))
            f.create_dataset("/Data/S11_imag", data=np.ones((n_points, len(freqs))))

        w = viz.VisualizerWindow(str(path))
        w.timer.stop()
        try:
            # The plain frequency view does not need a uniform grid.
            assert w._display_slice() is not None

            w.domain_combo.setCurrentText(viz.DOMAIN_TIME)
            assert w._display_slice() is None
            assert "not uniformly spaced" in w.status_label.text()

            # And it recovers when the operator switches back.
            w.domain_combo.setCurrentText(viz.DOMAIN_FREQUENCY)
            assert w._display_slice() is not None
            assert "not uniformly spaced" not in w.status_label.text()
        finally:
            w.play_timer.stop()
            w.close()

    @pytest.mark.parametrize("window", [{"points_written": 9}], indirect=True)
    def test_a_scan_in_progress_still_transforms(self, window):
        """The visualizer is live during a scan, so every view has to cope with
        a file that is only partly written."""
        assert "Live" in window.status_label.text()
        assert window.last_point_read == 9

        window.domain_combo.setCurrentText(viz.DOMAIN_TIME)
        assert window._display_slice() is not None

        window.filter_combo.setCurrentText(sp.FILTER_HIGH_PASS)
        assert window._display_slice() is not None

    def test_the_play_button_walks_the_current_axis(self, window):
        window.domain_combo.setCurrentText(viz.DOMAIN_TIME)
        window.freq_slider.setValue(0)
        window.play_next_frame()
        assert window.freq_index == 1

    def test_play_wraps_at_the_end_of_the_axis(self, window):
        window.domain_combo.setCurrentText(viz.DOMAIN_TIME)
        window.freq_slider.setValue(window.freq_slider.maximum())
        window.play_next_frame()
        assert window.freq_index == 0
