"""The shipped ProbeSimulator, driven end-to-end through ProbeController.

This is the closest thing the project has to an integration test that runs with
no instruments attached: a real plugin, a real controller, a full scan loop.
"""

import pytest

from scanner.probe_controller import ProbeController
from scanner.probe_simulator import ProbeSimulator

pytestmark = pytest.mark.contract


class TestSweepAxis:
    def test_returns_the_requested_number_of_points(self, probe_simulator):
        probe_simulator.num_points_per_channel.value = 51
        assert len(probe_simulator.get_xaxis_coords()) == 51

    def test_spans_the_configured_range_inclusively(self, probe_simulator):
        probe_simulator.xaxis_min.value = 2.0
        probe_simulator.xaxis_max.value = 18.0
        coords = probe_simulator.get_xaxis_coords()
        assert coords[0] == pytest.approx(2.0)
        assert coords[-1] == pytest.approx(18.0)

    def test_points_are_evenly_spaced(self, probe_simulator):
        coords = probe_simulator.get_xaxis_coords()
        gaps = [b - a for a, b in zip(coords, coords[1:])]
        assert gaps == pytest.approx([gaps[0]] * len(gaps))

    def test_points_ascend(self, probe_simulator):
        coords = probe_simulator.get_xaxis_coords()
        assert list(coords) == sorted(coords)

    def test_two_points_is_the_minimum(self, probe_simulator):
        """One point would divide by zero when computing the step."""
        with pytest.raises(ValueError):
            probe_simulator.num_points_per_channel.set_value_from_string("1")


class TestChannels:
    def test_names_match_the_channel_count(self, probe_simulator):
        probe_simulator.num_channels.value = 4
        names = probe_simulator.get_channel_names()
        assert len(names) == 4
        assert names == ("Channel 1", "Channel 2", "Channel 3", "Channel 4")

    def test_names_are_unique(self, probe_simulator):
        probe_simulator.num_channels.value = 8
        names = probe_simulator.get_channel_names()
        assert len(set(names)) == len(names)

    def test_at_least_one_channel_is_required(self, probe_simulator):
        with pytest.raises(ValueError):
            probe_simulator.num_channels.set_value_from_string("0")

    def test_units_are_reported(self, probe_simulator):
        assert probe_simulator.get_xaxis_units() == "GHz"
        assert probe_simulator.get_yaxis_units() == "V"


class TestMeasurement:
    def test_shape_is_channels_by_points(self, probe_simulator):
        probe_simulator.num_channels.value = 3
        probe_simulator.num_points_per_channel.value = 7

        data = probe_simulator.scan_read_measurement(0, (0.0, 0.0))

        assert len(data) == 3
        assert all(len(trace) == 7 for trace in data)

    def test_values_are_finite(self, probe_simulator):
        """A NaN here would poison the HDF5 file and every image built from it."""
        for trace in probe_simulator.scan_read_measurement(0, (0.0, 0.0)):
            for value in trace:
                assert value == value
                assert abs(value) != float("inf")

    def test_the_simulated_waveform_is_bounded(self, probe_simulator):
        """It is a cosine, so every sample belongs in [-1, 1]."""
        for trace in probe_simulator.scan_read_measurement(0, (0.0, 0.0)):
            assert all(-1.0 <= value <= 1.0 for value in trace)

    def test_measurement_is_repeatable(self, probe_simulator):
        """The simulator is deterministic, which is what makes it testable."""
        first = probe_simulator.scan_read_measurement(0, (0.0, 0.0))
        second = probe_simulator.scan_read_measurement(0, (0.0, 0.0))
        assert first == second

    def test_trigger_returns_nothing(self, probe_simulator):
        assert probe_simulator.scan_trigger_and_wait(0, (0.0, 0.0)) is None

    def test_the_measurement_respects_a_changed_channel_count(self, probe_simulator):
        """Settings changed between runs must take effect without a reconstruct."""
        probe_simulator.num_channels.value = 2
        assert len(probe_simulator.scan_read_measurement(0, ())) == 2

        probe_simulator.num_channels.value = 5
        assert len(probe_simulator.scan_read_measurement(0, ())) == 5


class TestFullScanThroughTheController:
    def test_a_complete_raster_produces_one_measurement_per_point(self, probe_simulator):
        points = [(x * 2.0, y * 2.0) for y in range(3) for x in range(4)]
        controller = ProbeController(probe_simulator)

        controller.connect()
        controller.scan_begin()
        collected = []
        for index, location in enumerate(points):
            controller.scan_trigger_and_wait(index, location)
            collected.append(controller.scan_read_measurement(index, location))
        controller.scan_end()
        controller.disconnect()

        assert len(collected) == len(points)
        channels = len(probe_simulator.get_channel_names())
        sweep = len(probe_simulator.get_xaxis_coords())
        for measurement in collected:
            assert len(measurement) == channels
            assert all(len(trace) == sweep for trace in measurement)

    def test_the_dataset_matches_the_declared_axes(self, probe_simulator):
        """What the file writer relies on: shape is knowable before the scan."""
        controller = ProbeController(probe_simulator)
        controller.connect()

        expected_channels = controller.get_channel_names()
        expected_sweep = controller.get_xaxis_coords()
        measurement = controller.scan_read_measurement(0, (0.0, 0.0))

        assert len(measurement) == len(expected_channels)
        assert len(measurement[0]) == len(expected_sweep)

    def test_settings_appear_after_connect_not_before(self, probe_simulator):
        """The simulator's settings are all post-connect, so the GUI shows them
        only once the instrument is live."""
        assert probe_simulator.settings_pre_connect == []
        labels = [s.display_label for s in probe_simulator.settings_post_connect]
        assert "Number of Channels" in labels
        assert "Points Per Channel" in labels


class TestTimingSettings:
    def test_delays_default_to_something_nonzero(self):
        """The un-doctored simulator imitates a slow instrument on purpose."""
        fresh = ProbeSimulator()
        assert fresh.measure_time.value > 0
        assert fresh.init_time.value > 0

    def test_delays_can_be_zeroed_for_tests(self, probe_simulator):
        assert probe_simulator.measure_time.value == 0
        assert probe_simulator.init_time.value == 0

    def test_negative_delays_are_rejected(self, probe_simulator):
        with pytest.raises(ValueError):
            probe_simulator.measure_time.set_value_from_string("-1")
