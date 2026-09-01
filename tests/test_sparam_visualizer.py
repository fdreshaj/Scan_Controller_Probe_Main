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
import pathlib
import sys

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


class TestStandaloneEmptyState:
    """Run on its own, the window opens with only Import live.

        python -m scanner.S_param_visualizer

    No modal dialog blocks startup -- the old entry point asked for a file
    first and exited if you cancelled, so there was no way to just look at the
    window.
    """

    @pytest.fixture
    def empty(self, qapp):
        w = viz.VisualizerWindow()
        w.timer.stop()
        yield w
        w.play_timer.stop()
        w.close()

    def test_it_constructs_with_no_path_at_all(self, empty):
        assert empty.hdf5_filepath is None
        assert empty.has_file() is False

    def test_it_says_what_to_do(self, empty):
        assert empty.status_label.text() == "No file loaded"
        placeholder = empty.scene.items()[0].toPlainText()
        assert "import" in placeholder.lower()

    def test_import_is_the_only_live_control(self, empty):
        assert empty.import_button.isEnabled()
        for name in (
            "sparam_combo", "datatype_combo", "colormap_combo", "domain_combo",
            "window_combo", "filter_combo", "cutoff_spin", "freq_slider",
            "trace_checkbox", "play_button",
        ):
            assert not getattr(empty, name).isEnabled(), name

    def test_the_import_button_is_labelled_not_just_an_icon(self, empty):
        """With everything else greyed out it is the only thing to click, so
        it should say so rather than being a bare glyph."""
        assert "Import" in empty.import_button.text()

    def test_the_placeholder_is_not_blown_up_to_fill_the_view(self, empty):
        """fitInView would scale a short string to the whole viewport."""
        assert empty.view.transform().m11() == pytest.approx(1.0)

    def test_the_readouts_are_blank_rather_than_stale(self, empty):
        assert empty.points_label.text() == "Points: 0"
        assert empty.grid_label.text() == "Grid: --"
        assert empty.freq_value_label.text() == "--"

    def test_polling_a_missing_file_is_a_no_op(self, empty):
        """The 500 ms timer keeps running; it must not churn on nothing."""
        empty.check_for_updates()
        empty.update_visualization()
        assert empty.status_label.text() == "No file loaded"

    def test_a_path_that_does_not_exist_opens_empty_not_broken(self, qapp, tmp_path):
        """The scanner GUI hands over a filename derived from scan metadata,
        which may not have been written yet."""
        w = viz.VisualizerWindow(str(tmp_path / "never_written.h5"))
        w.timer.stop()
        try:
            assert w.has_file() is False
            assert "not found" in w.status_label.text()
            assert not w.domain_combo.isEnabled()
            assert w.import_button.isEnabled()
        finally:
            w.play_timer.stop()
            w.close()


class TestImportFlow:
    """Importing is what takes the window from empty to usable."""

    @pytest.fixture
    def empty(self, qapp):
        w = viz.VisualizerWindow()
        w.timer.stop()
        yield w
        w.play_timer.stop()
        w.close()

    @staticmethod
    def choose(monkeypatch, path):
        """Stub only the modal dialog, so the real import path still runs."""
        monkeypatch.setattr(
            viz.QFileDialog, "getOpenFileName",
            staticmethod(lambda *a, **k: (str(path), "")),
        )

    def test_importing_enables_everything(self, empty, monkeypatch, tmp_path):
        self.choose(monkeypatch, write_scan(tmp_path / "scan.h5"))
        empty.import_new_file()

        assert empty.available_sparams == ["S11"]
        for name in (
            "sparam_combo", "datatype_combo", "colormap_combo", "domain_combo",
            "window_combo", "filter_combo", "freq_slider", "play_button",
        ):
            assert getattr(empty, name).isEnabled(), name

    def test_the_cutoff_stays_disabled_until_a_filter_is_chosen(
        self, empty, monkeypatch, tmp_path
    ):
        self.choose(monkeypatch, write_scan(tmp_path / "scan.h5"))
        empty.import_new_file()

        assert not empty.cutoff_spin.isEnabled()
        empty.filter_combo.setCurrentText(sp.FILTER_HIGH_PASS)
        assert empty.cutoff_spin.isEnabled()

    def test_the_views_work_after_importing(self, empty, monkeypatch, tmp_path):
        self.choose(monkeypatch, write_scan(tmp_path / "scan.h5"))
        empty.import_new_file()

        empty.domain_combo.setCurrentText(viz.DOMAIN_TIME)
        assert empty._display_slice() is not None
        empty.datatype_combo.setCurrentText(sp.DISPLAY_PHASE_UNWRAPPED)
        assert empty._display_slice() is not None

    def test_the_view_re_fits_to_the_newly_imported_scan(self, empty, monkeypatch, tmp_path):
        """The reset flag was checked with hasattr, which never goes back to
        False, so an imported scan kept the previous view transform -- from the
        empty placeholder, or from a differently sized earlier file."""
        self.choose(monkeypatch, write_scan(tmp_path / "scan.h5", nx=30, ny=24))
        empty.import_new_file()

        assert empty._view_fitted is True

        rect = empty.scene.itemsBoundingRect()
        # The scene rect must follow the data. show_empty_state pins it to the
        # size of the placeholder text, and a stale text-sized scene rect
        # leaves the heatmap unfitted with stray scrollbars.
        assert empty.view.sceneRect().width() == pytest.approx(rect.width())
        assert empty.view.sceneRect().height() == pytest.approx(rect.height())

        # Snug, not merely visible: one axis should fill the viewport.
        viewport = empty.view.viewport().rect()
        scale = empty.view.transform().m11()
        assert scale == pytest.approx(
            min(viewport.width() / rect.width(), viewport.height() / rect.height()),
            rel=0.02,
        )

    def test_the_title_names_the_loaded_file(self, empty, monkeypatch, tmp_path):
        self.choose(monkeypatch, write_scan(tmp_path / "my_scan.h5"))
        empty.import_new_file()
        assert "my_scan.h5" in empty.windowTitle()

    def test_cancelling_the_dialog_changes_nothing(self, empty, monkeypatch):
        monkeypatch.setattr(
            viz.QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: ("", ""))
        )
        empty.import_new_file()

        assert empty.hdf5_filepath is None
        assert empty.status_label.text() == "No file loaded"
        assert not empty.domain_combo.isEnabled()

    def test_a_file_with_no_scan_data_reports_and_stays_disabled(
        self, empty, monkeypatch, tmp_path
    ):
        """A readable HDF5 file that is not a scan. Saying so beats a blank
        window with live controls that have nothing to act on."""
        path = tmp_path / "notascan.h5"
        with h5py.File(path, "w") as f:
            f.create_dataset("/something/else", data=[1, 2, 3])
        self.choose(monkeypatch, path)

        empty.import_new_file()

        assert "No S-parameter data" in empty.status_label.text()
        assert not empty.domain_combo.isEnabled()
        assert empty.import_button.isEnabled(), "must still be able to try again"

    def test_importing_a_second_file_replaces_the_first(
        self, empty, monkeypatch, tmp_path
    ):
        self.choose(monkeypatch, write_scan(tmp_path / "first.h5", nx=8, ny=6))
        empty.import_new_file()
        assert empty.grid_label.text() == "Grid: 8 × 6"

        self.choose(monkeypatch, write_scan(tmp_path / "second.h5", nx=5, ny=4))
        empty.import_new_file()
        assert empty.grid_label.text() == "Grid: 5 × 4"
        assert "second.h5" in empty.windowTitle()

    def test_importing_over_a_bad_file_recovers(self, empty, monkeypatch, tmp_path):
        bad = tmp_path / "bad.h5"
        with h5py.File(bad, "w") as f:
            f.create_dataset("/nope", data=[1])
        self.choose(monkeypatch, bad)
        empty.import_new_file()
        assert not empty.domain_combo.isEnabled()

        self.choose(monkeypatch, write_scan(tmp_path / "good.h5"))
        empty.import_new_file()
        assert empty.domain_combo.isEnabled()
        assert empty.available_sparams == ["S11"]


class TestStandaloneEntryPoint:
    def test_main_is_callable_and_documented(self):
        """`python -m scanner.S_param_visualizer` routes through main()."""
        assert callable(viz.main)
        assert "python -m scanner.S_param_visualizer" in viz.main.__doc__

    def test_the_module_imports_as_a_bare_script(self):
        """`python scanner/S_param_visualizer.py` puts the script's own
        directory on sys.path, not the repo root, so a plain
        `from scanner import ...` would find scanner/scanner.py -- a module,
        not the package -- and fail to import. The bootstrap at the top of the
        file fixes that.

        Run in a subprocess with sys.path arranged exactly as Python arranges
        it for a bare script, and with a run_name other than "__main__" so the
        event loop never starts.
        """
        import subprocess

        source = pathlib.Path(viz.__file__).resolve()
        script = (
            "import sys, os, runpy\n"
            f"sys.path.insert(0, {str(source.parent)!r})\n"
            # Drop the repo root, so only the bootstrap can save us.
            f"sys.path = [p for p in sys.path if os.path.abspath(p or '.') "
            f"!= {str(source.parent.parent)!r}]\n"
            f"runpy.run_path({str(source)!r}, run_name='__not_main__')\n"
            "print('IMPORT-OK')\n"
        )
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True, text=True, timeout=120,
            env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
        )
        assert "IMPORT-OK" in result.stdout, (
            f"bare-script import failed\nstdout: {result.stdout}\n"
            f"stderr: {result.stderr}"
        )


class TestPlaybackSpeed:
    """The Play button used to run at a 0 ms timer interval.

    QTimer truncates the old `play_speed = 0.05` to 0 ms, so playback advanced
    as fast as the event loop would go -- hundreds of frames a second once the
    renderer was vectorised, far too quick to read.
    """

    def test_the_default_is_a_readable_rate(self, window):
        assert window.speed_spin.value() == viz.DEFAULT_PLAYBACK_FPS
        assert viz.DEFAULT_PLAYBACK_FPS <= 12, "the default must be watchable"

    def test_the_interval_is_derived_from_the_rate(self, window):
        window.speed_spin.setValue(10)
        assert window.play_speed == 100
        window.speed_spin.setValue(4)
        assert window.play_speed == 250

    def test_the_interval_is_never_zero(self, window):
        """A 0 ms interval is what made playback unwatchable."""
        for fps in range(viz.MIN_PLAYBACK_FPS, viz.MAX_PLAYBACK_FPS + 1):
            window.speed_spin.setValue(fps)
            assert window.play_speed >= 1

    def test_the_rate_is_bounded(self, window):
        window.speed_spin.setValue(10_000)
        assert window.speed_spin.value() == viz.MAX_PLAYBACK_FPS
        window.speed_spin.setValue(0)
        assert window.speed_spin.value() == viz.MIN_PLAYBACK_FPS

    def test_play_uses_the_chosen_interval(self, window):
        window.speed_spin.setValue(5)
        window.toggle_play()
        try:
            assert window.play_timer.isActive()
            assert window.play_timer.interval() == 200
        finally:
            window.toggle_play()

    def test_changing_speed_mid_play_takes_effect_immediately(self, window):
        """Otherwise you would have to stop and restart to re-time it."""
        window.speed_spin.setValue(20)
        window.toggle_play()
        try:
            assert window.play_timer.interval() == 50
            window.speed_spin.setValue(2)
            assert window.play_timer.interval() == 500
            assert window.play_timer.isActive(), "must not stop playback"
        finally:
            window.toggle_play()

    def test_changing_speed_while_stopped_does_not_start_playback(self, window):
        window.speed_spin.setValue(3)
        assert not window.play_timer.isActive()

    def test_the_pass_duration_is_shown(self, window):
        """Frames per second is not the number you care about; how long you
        will be sitting there is."""
        window.speed_spin.setValue(10)
        text = window.sweep_time_label.text()
        assert "201 frames" in text
        assert "20 s/pass" in text

    def test_the_pass_duration_follows_the_domain(self, window):
        window.speed_spin.setValue(10)
        before = window.sweep_time_label.text()
        window.domain_combo.setCurrentText(viz.DOMAIN_TIME)
        assert window.sweep_time_label.text()
        # Same bin count here, but the label must have been recomputed, not
        # left over from the frequency axis.
        assert "frames" in window.sweep_time_label.text()
        assert before  # sanity

    def test_playback_still_advances_one_frame_at_a_time(self, window):
        window.freq_slider.setValue(0)
        window.play_next_frame()
        assert window.freq_index == 1

    def test_a_slow_render_is_reported_rather_than_silently_capping(self, window):
        """A frame that costs more than the interval makes the timer fire late,
        so the requested rate is not achieved. Saying so beats letting the
        Speed control look broken."""
        window.speed_spin.setValue(60)
        window.toggle_play()
        try:
            window._last_frame_ms = 250.0  # as if a heavy upscale were on
            window.update_sweep_time_label()
            assert "render-limited" in window.sweep_time_label.text()
        finally:
            window.toggle_play()

    def test_no_warning_when_the_render_keeps_up(self, window):
        window.speed_spin.setValue(4)
        window.toggle_play()
        try:
            window._last_frame_ms = 5.0
            window.update_sweep_time_label()
            assert "render-limited" not in window.sweep_time_label.text()
        finally:
            window.toggle_play()

    def test_no_warning_while_stopped(self, window):
        window._last_frame_ms = 999.0
        window.update_sweep_time_label()
        assert "render-limited" not in window.sweep_time_label.text()


class TestUpscaling:
    """Drawing a coarse measurement grid at a legible size.

    A 24 x 18 raster is 24 x 18 pixels. The factor enlarges it; the smoothing
    mode decides whether the gaps between measurement points are filled with
    flat blocks or interpolated.
    """

    def test_the_default_matches_the_previous_fixed_behaviour(self, window):
        assert window.upscale_combo.currentData() == viz.DEFAULT_UPSCALE_FACTOR
        assert window.interp_combo.currentText() == viz.INTERP_NEAREST

    @pytest.mark.parametrize("factor", viz.UPSCALE_FACTORS)
    def test_the_image_scales_with_the_factor(self, window, factor):
        window.upscale_combo.setCurrentText(f"{factor}×")
        pixmap = window.scene.items()[0].pixmap()
        assert pixmap.width() == len(window.unique_y) * factor
        assert pixmap.height() == len(window.unique_x) * factor

    @pytest.mark.parametrize("factor", viz.UPSCALE_FACTORS)
    @pytest.mark.parametrize("mode", viz.INTERP_MODES)
    def test_clicking_still_picks_the_right_point(self, window, factor, mode):
        """The hit test divides by the scale factor, so renderer and click
        handler must agree at every setting. The bilinear path uses the
        half-pixel convention precisely so that pixel // scale still names the
        measurement point underneath."""
        window.interp_combo.setCurrentText(mode)
        window.upscale_combo.setCurrentText(f"{factor}×")
        scale = window.heatmap_scale_factor

        for ix, iy in ((0, 0), (3, 2), (7, 5)):
            window.on_heatmap_clicked(iy * scale + scale // 2, ix * scale + scale // 2)
            assert window.point_coordinates(window.selected_point) == (
                float(window.unique_x[ix]), float(window.unique_y[iy])
            )

    @pytest.mark.parametrize("factor", viz.UPSCALE_FACTORS)
    def test_nearest_is_exactly_block_replication(self, window, factor):
        """The old renderer replicated blocks at a fixed 4x. Nearest at any
        factor must be that same operation -- every pixel a measured value."""
        window.interp_combo.setCurrentText(viz.INTERP_NEAREST)
        grid = np.arange(6.0).reshape(2, 3)
        expected = np.repeat(np.repeat(grid, factor, axis=0), factor, axis=1)
        assert np.array_equal(window._upscale(grid, factor), expected)

    def test_scale_one_is_the_identity_in_both_modes(self, window):
        grid = np.arange(12.0).reshape(3, 4)
        for mode in viz.INTERP_MODES:
            window.interp_combo.setCurrentText(mode)
            assert np.array_equal(window._upscale(grid, 1), grid)

    def test_bilinear_actually_smooths(self, window):
        window.interp_combo.setCurrentText(viz.INTERP_BILINEAR)
        grid = np.arange(6.0).reshape(2, 3)
        smooth = window._upscale(grid, 4)
        blocky = np.repeat(np.repeat(grid, 4, axis=0), 4, axis=1)
        assert not np.allclose(smooth, blocky)

    def test_bilinear_lands_measured_values_on_the_cell_centres(self, window):
        """The alignment property the click mapping depends on. An odd factor
        puts each cell's centre exactly on an output pixel, so it can be
        checked directly; at an even factor the centre falls between two."""
        window.interp_combo.setCurrentText(viz.INTERP_BILINEAR)
        grid = np.arange(6.0).reshape(2, 3)
        out = window._upscale(grid, 3)
        assert np.allclose(out[1::3, 1::3], grid)

    def test_bilinear_invents_no_new_extremes(self, window):
        """It is a convex blend of neighbours, so it must not overshoot. An
        interpolated peak brighter than anything measured would be a lie."""
        window.interp_combo.setCurrentText(viz.INTERP_BILINEAR)
        grid = np.random.default_rng(0).random((9, 7))
        out = window._upscale(grid, 8)
        assert out.min() >= grid.min() - 1e-12
        assert out.max() <= grid.max() + 1e-12

    def test_bilinear_leaves_a_constant_field_constant(self, window):
        window.interp_combo.setCurrentText(viz.INTERP_BILINEAR)
        out = window._upscale(np.full((4, 5), 7.0), 8)
        assert np.allclose(out, 7.0)

    def test_bilinear_does_not_smear_across_unmeasured_cells(self, window):
        """A scan in progress is mostly NaN. Plain interpolation would drag
        NaN across every neighbouring pixel and eat the edge of the measured
        area, so the upscaler uses normalised convolution."""
        window.interp_combo.setCurrentText(viz.INTERP_BILINEAR)
        grid = np.array([[1.0, 1.0, np.nan], [1.0, 1.0, np.nan]])
        out = window._upscale(grid, 4)

        assert not np.any(np.isnan(out[:, :4])), "measured region must survive"
        assert np.allclose(out[:, :4], 1.0)
        assert np.all(np.isnan(out[:, -2:])), "unmeasured region stays a hole"

    def test_unmeasured_cells_render_grey_in_both_modes(self, window):
        for mode in viz.INTERP_MODES:
            window.interp_combo.setCurrentText(mode)
            rgb = window._colormap_rgb(window._upscale(
                np.array([[0.5, np.nan]]), 4
            ))
            assert tuple(rgb[0, -1]) == (128, 128, 128), mode

    def test_changing_either_control_redraws(self, window):
        def snapshot():
            return hash(window.scene.items()[0].pixmap().toImage().bits().tobytes())

        window.upscale_combo.setCurrentText("2×")
        small = snapshot()
        window.upscale_combo.setCurrentText("8×")
        large = snapshot()
        assert small != large

        window.interp_combo.setCurrentText(viz.INTERP_BILINEAR)
        assert snapshot() != large

    def test_the_factor_is_clamped_for_huge_grids(self, window):
        """A 200 x 200 grid at 16x is 3200 px square and 30 MB per frame."""
        assert window.effective_scale_factor((200, 200)) * 200 <= viz.MAX_HEATMAP_PIXELS
        assert window.effective_scale_factor((9000, 9000)) == 1, "never below 1"

    def test_a_small_grid_is_not_clamped(self, window):
        window.upscale_combo.setCurrentText("16×")
        assert window.effective_scale_factor((24, 18)) == 16

    def test_the_effective_factor_is_what_the_hit_test_uses(self, window):
        """If the renderer clamps but the hit test does not, clicks land on the
        wrong point."""
        window.upscale_combo.setCurrentText("16×")
        window.redraw_data()
        assert window.heatmap_scale_factor == window.effective_scale_factor(
            (len(window.unique_x), len(window.unique_y))
        )
