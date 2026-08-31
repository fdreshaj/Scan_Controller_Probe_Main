"""ProbeController wraps the VNA driver and gates it behind a connection.

The scan loop calls into this once per measurement point, tens of thousands of
times per run, so the ordering contract (begin -> trigger/read per point -> end)
and the disconnected guard rails are what these tests hold onto.
"""

import pytest

from scanner.probe_controller import ProbeController, ProbePlugin
from tests.fakes import RecordingProbePlugin

pytestmark = pytest.mark.contract


@pytest.fixture
def controller(probe_plugin):
    return ProbeController(probe_plugin)


class TestConnectionLifecycle:
    def test_starts_disconnected(self, controller):
        assert controller.is_connected() is False

    def test_construction_does_not_touch_the_instrument(self, probe_plugin):
        ProbeController(probe_plugin)
        assert probe_plugin.call_names == []

    def test_connect_reaches_the_driver(self, controller, probe_plugin):
        controller.connect()
        assert controller.is_connected() is True
        assert probe_plugin.connected is True

    def test_disconnect_reaches_the_driver(self, controller, probe_plugin):
        controller.connect()
        controller.disconnect()
        assert controller.is_connected() is False
        assert probe_plugin.connected is False

    def test_disconnecting_twice_only_tells_the_instrument_once(self, controller, probe_plugin):
        controller.connect()
        controller.disconnect()
        controller.disconnect()
        assert probe_plugin.call_names.count("disconnect") == 1

    def test_disconnect_before_connect_never_reaches_the_instrument(self, controller, probe_plugin):
        controller.disconnect()
        assert "disconnect" not in probe_plugin.call_names

    def test_reconnecting_works(self, controller, probe_plugin):
        controller.connect()
        controller.disconnect()
        controller.connect()
        assert controller.is_connected() is True
        assert probe_plugin.call_names.count("connect") == 2


class TestGuardRails:
    @pytest.mark.parametrize(
        "call",
        [
            pytest.param(lambda c: c.scan_begin(), id="scan_begin"),
            pytest.param(lambda c: c.scan_trigger_and_wait(0, (0.0, 0.0)), id="trigger"),
            pytest.param(lambda c: c.scan_read_measurement(0, (0.0, 0.0)), id="read"),
            pytest.param(lambda c: c.scan_end(), id="scan_end"),
            pytest.param(lambda c: c.get_channel_names(), id="channel_names"),
            pytest.param(lambda c: c.get_xaxis_coords(), id="xaxis_coords"),
        ],
    )
    def test_refuses_while_disconnected(self, controller, probe_plugin, call):
        with pytest.raises(ConnectionError):
            call(controller)
        assert probe_plugin.call_names == [], "the instrument must not be touched"

    def test_a_scan_cannot_continue_after_a_mid_run_disconnect(self, controller):
        """A dropped VNA link must stop the run, not silently produce zeros."""
        controller.connect()
        controller.scan_begin()
        controller.scan_read_measurement(0, (0.0, 0.0))

        controller.disconnect()

        with pytest.raises(ConnectionError):
            controller.scan_read_measurement(1, (2.0, 0.0))


class TestScanSequence:
    def test_a_full_scan_issues_the_expected_call_order(self, controller, probe_plugin):
        points = [(0.0, 0.0), (2.0, 0.0), (2.0, 2.0)]

        controller.connect()
        controller.scan_begin()
        for index, location in enumerate(points):
            controller.scan_trigger_and_wait(index, location)
            controller.scan_read_measurement(index, location)
        controller.scan_end()
        controller.disconnect()

        assert probe_plugin.call_names == [
            "connect",
            "scan_begin",
            "scan_trigger_and_wait",
            "scan_read_measurement",
            "scan_trigger_and_wait",
            "scan_read_measurement",
            "scan_trigger_and_wait",
            "scan_read_measurement",
            "scan_end",
            "disconnect",
        ]

    def test_every_point_is_measured_exactly_once(self, controller, probe_plugin):
        points = [(x * 2.0, 0.0) for x in range(5)]

        controller.connect()
        controller.scan_begin()
        for index, location in enumerate(points):
            controller.scan_read_measurement(index, location)
        controller.scan_end()

        assert probe_plugin.visited == list(enumerate(points))

    def test_measurement_shape_matches_the_declared_channels_and_sweep(
        self, controller, probe_plugin
    ):
        controller.connect()
        channels = controller.get_channel_names()
        freqs = controller.get_xaxis_coords()

        data = controller.scan_read_measurement(0, (0.0, 0.0))

        assert len(data) == len(channels), "one trace per channel"
        for trace in data:
            assert len(trace) == len(freqs), "one sample per frequency point"

    def test_the_measurement_belongs_to_the_point_it_was_taken_at(self, controller):
        """Guards against off-by-one shuffling between motion and acquisition."""
        controller.connect()
        controller.scan_begin()

        first = controller.scan_read_measurement(0, (0.0, 0.0))
        second = controller.scan_read_measurement(1, (2.0, 0.0))

        assert first[0][0] == pytest.approx(0.0)
        assert second[0][0] == pytest.approx(1.0)

    def test_trigger_and_read_are_separable(self, controller, probe_plugin):
        """Some drivers trigger and read in one step and return None from trigger.

        The controller must pass that None straight through rather than treating
        it as a failure.
        """
        controller.connect()
        assert controller.scan_trigger_and_wait(0, (0.0, 0.0)) is None


class TestAbstractSurface:
    def test_the_abc_cannot_be_instantiated(self):
        with pytest.raises(TypeError):
            ProbePlugin()

    def test_a_partial_implementation_cannot_be_instantiated(self):
        class Incomplete(ProbePlugin):
            def connect(self) -> None:
                pass

        with pytest.raises(TypeError):
            Incomplete()

    def test_the_fake_implements_the_whole_abc(self, probe_plugin):
        assert not getattr(type(probe_plugin), "__abstractmethods__", frozenset())

    def test_settings_lists_are_per_instance(self):
        a, b = RecordingProbePlugin(), RecordingProbePlugin()
        a.add_setting_pre_connect(a.address)
        assert len(b.settings_pre_connect) == 1
