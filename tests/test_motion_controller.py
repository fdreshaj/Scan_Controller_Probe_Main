"""MotionController is the last software layer before a motor turns.

Its job is to refuse to do anything while disconnected, to pass commands
through to the driver, and to keep travel inside the endstops. These tests pin
that contract down with a fake driver, and mark the places where the contract is
currently broken with `xfail(strict=True)` so a future fix flips them green
instead of going unnoticed.
"""

import pytest

from scanner.motion_controller import MotionController, MotionControllerPlugin
from tests.fakes import OutOfTravelError, RecordingMotionPlugin

pytestmark = pytest.mark.contract


@pytest.fixture
def controller(motion_plugin):
    return MotionController(motion_plugin)


class TestConnectionLifecycle:
    def test_starts_disconnected(self, controller):
        assert controller.is_connected() is False

    def test_construction_does_not_touch_the_driver(self, motion_plugin):
        MotionController(motion_plugin)
        assert "connect" not in motion_plugin.call_names

    def test_connect_reports_connected(self, controller):
        controller.connect()
        assert controller.is_connected() is True

    def test_connect_reaches_the_driver(self, controller, motion_plugin):
        controller.connect()
        assert motion_plugin.connected is True
        assert motion_plugin.call_names[0] == "connect"

    def test_connect_caches_the_endstops_from_the_driver(self, controller, motion_plugin):
        controller.connect()
        assert controller._endstop_minimums == motion_plugin.get_endstop_minimums()
        assert controller._endstop_maximums == motion_plugin.get_endstop_maximums()

    def test_disconnect_reaches_the_driver(self, controller, motion_plugin):
        controller.connect()
        controller.disconnect()
        assert controller.is_connected() is False
        assert motion_plugin.connected is False

    def test_disconnecting_twice_only_tells_the_driver_once(self, controller, motion_plugin):
        controller.connect()
        controller.disconnect()
        controller.disconnect()
        assert motion_plugin.call_names.count("disconnect") == 1

    def test_disconnect_before_connect_never_reaches_the_driver(self, controller, motion_plugin):
        controller.disconnect()
        assert "disconnect" not in motion_plugin.call_names

    def test_disconnect_clears_the_cached_endstops(self, controller):
        controller.connect()
        controller.disconnect()
        assert controller._endstop_minimums == ()
        assert controller._endstop_maximums == ()

    def test_swapping_the_plugin_disconnects_the_old_one(self, controller, motion_plugin):
        controller.connect()
        replacement = RecordingMotionPlugin()
        controller.swap_motion_plugin(replacement)

        assert motion_plugin.connected is False
        assert controller.is_connected() is False
        assert controller._driver is replacement


class TestGuardRails:
    """Nothing that moves a motor may run while disconnected."""

    @pytest.mark.parametrize(
        "call",
        [
            pytest.param(lambda c: c.set_velocity({0: 10.0}), id="set_velocity"),
            pytest.param(lambda c: c.set_acceleration({0: 5.0}), id="set_acceleration"),
            pytest.param(lambda c: c.move_absolute({0: 1.0}), id="move_absolute"),
            pytest.param(lambda c: c.home(), id="home"),
            pytest.param(lambda c: c.is_moving(), id="is_moving"),
            pytest.param(lambda c: c.emergency_stop(), id="emergency_stop"),
            pytest.param(lambda c: c.set_config(1.0, 50, 2.0), id="set_config"),
        ],
    )
    def test_refuses_while_disconnected(self, controller, motion_plugin, call):
        with pytest.raises(ConnectionError):
            call(controller)
        assert motion_plugin.position == [0.0, 0.0, 0.0]

    def test_the_same_calls_succeed_once_connected(self, controller, motion_plugin):
        controller.connect()
        controller.set_velocity({0: 10.0})
        controller.set_acceleration({0: 5.0})
        controller.move_absolute({0: 1.0})
        assert motion_plugin.velocities == {0: 10.0}
        assert motion_plugin.accelerations == {0: 5.0}
        assert motion_plugin.position[0] == pytest.approx(1.0)

    def test_get_current_positions_is_readable_while_disconnected(self, controller):
        """A read-only query is not gated, and must not raise.

        The GUI polls this to draw the position readout, including before a
        connection exists.
        """
        assert controller.get_current_positions() == (0.0, 0.0, 0.0)


class TestMotion:
    def test_move_absolute_reaches_the_commanded_position(self, controller, motion_plugin):
        controller.connect()
        controller.move_absolute({0: 25.0, 1: 40.0})
        assert motion_plugin.position == [25.0, 40.0, 0.0]

    def test_move_absolute_forwards_the_exact_axis_map(self, controller, motion_plugin):
        controller.connect()
        controller.move_absolute({1: 12.5})
        moves = [c for c in motion_plugin.calls if c.name == "move_absolute"]
        assert moves[-1].args[0] == {1: 12.5}

    def test_home_returns_the_axes_to_zero(self, controller, motion_plugin):
        controller.connect()
        controller.move_absolute({0: 100.0, 1: 100.0})
        controller.home()
        assert motion_plugin.position == [0.0, 0.0, 0.0]
        assert motion_plugin.homed is True

    def test_emergency_stop_reaches_the_driver(self, controller, motion_plugin):
        controller.connect()
        controller.emergency_stop()
        assert motion_plugin.estopped is True

    def test_a_driver_refusal_propagates(self, controller, motion_plugin):
        """An out-of-travel move must surface, not be swallowed."""
        controller.connect()
        with pytest.raises(OutOfTravelError):
            controller.move_absolute({0: 10_000.0})
        assert motion_plugin.position == [0.0, 0.0, 0.0]

    def test_a_refused_move_leaves_the_gantry_where_it_was(self, controller, motion_plugin):
        controller.connect()
        controller.move_absolute({0: 50.0})
        with pytest.raises(OutOfTravelError):
            controller.move_absolute({0: 50.0, 1: 10_000.0})
        assert motion_plugin.position == [50.0, 0.0, 0.0], (
            "a partially-applied move would leave the gantry somewhere neither "
            "the operator nor the software believes it to be"
        )


class TestKnownDefects:
    """Failures that exist in the shipped code today.

    These are `xfail(strict=True)`: they must keep failing until someone fixes
    the underlying bug, at which point pytest reports XPASS and the test should
    be promoted to an ordinary assertion.
    """

    @pytest.mark.xfail(
        strict=True,
        reason=(
            "MotionController.connect() calls self._driver.set_velocity() and "
            "set_acceleration() with no arguments, but MotionControllerPlugin "
            "declares set_velocity(self, velocities: dict[int, float]). It only "
            "works today because every shipped plugin quietly defaults the "
            "parameter to None. A plugin written to the published ABC signature "
            "raises TypeError the moment the operator hits Connect."
        ),
    )
    def test_connect_respects_the_declared_plugin_signature(self):
        class StrictlyConformantPlugin(RecordingMotionPlugin):
            # Exactly the ABC's signature: no default.
            def set_velocity(self, velocities: dict[int, float]) -> None:
                self._record("set_velocity", velocities)

            def set_acceleration(self, accels: dict[int, float]) -> None:
                self._record("set_acceleration", accels)

        MotionController(StrictlyConformantPlugin()).connect()

    @pytest.mark.xfail(
        strict=True,
        reason=(
            "move_relative() folds the current position in by iterating "
            "self._target_positions, but that list is only ever assigned [] -- "
            "the line in connect() that would populate it is commented out. The "
            "loop body never executes, so the offset is passed to "
            "move_absolute() unchanged and a relative move silently becomes an "
            "absolute one."
        ),
    )
    def test_move_relative_is_relative_to_the_current_position(self, controller, motion_plugin):
        controller.connect()
        controller.move_absolute({0: 100.0})
        controller.move_relative({0: 10.0})
        assert motion_plugin.position[0] == pytest.approx(110.0)

    def test_move_relative_currently_behaves_absolutely(self, controller, motion_plugin):
        """The flip side of the xfail above: this is what actually happens.

        Kept as a live assertion so the current behaviour is documented and any
        change to it -- fix or regression -- is caught by one of the two.
        """
        controller.connect()
        controller.move_absolute({0: 100.0})
        controller.move_relative({0: 10.0})
        assert motion_plugin.position[0] == pytest.approx(10.0)


class TestAbstractSurface:
    def test_the_abc_cannot_be_instantiated(self):
        with pytest.raises(TypeError):
            MotionControllerPlugin()

    def test_a_partial_implementation_cannot_be_instantiated(self):
        """This is what protects the operator from a half-written plugin."""

        class Incomplete(MotionControllerPlugin):
            def connect(self) -> None:
                pass

        with pytest.raises(TypeError):
            Incomplete()

    def test_the_fake_implements_the_whole_abc(self, motion_plugin):
        """If this fails, the fake has drifted from the interface it stands in for."""
        assert not getattr(type(motion_plugin), "__abstractmethods__", frozenset())

    def test_settings_are_registered_in_two_phases(self, motion_plugin):
        """The GUI shows pre-connect settings before Connect, post-connect after."""
        assert [s.display_label for s in motion_plugin.settings_pre_connect] == [
            "Resource Address"
        ]
        assert [s.display_label for s in motion_plugin.settings_post_connect] == [
            "Max Velocity"
        ]

    def test_settings_lists_are_per_instance(self):
        """Two drivers loaded in one session must not share a settings list."""
        a, b = RecordingMotionPlugin(), RecordingMotionPlugin()
        a.add_setting_pre_connect(a.max_velocity)
        assert len(b.settings_pre_connect) == 1
