"""Hardware doubles for the scanner test suite.

These are not mocks in the "assert_called_with" sense. They are small, honest
implementations of the two plugin ABCs that keep enough internal state to answer
questions a real device would answer -- where is the gantry, is it moving, what
did it refuse -- and record every call so a test can assert on the *sequence* of
commands, which is what actually matters when driving a motion controller.

`RecordingMotionPlugin` deliberately enforces soft travel limits. A driver that
silently accepts an out-of-range move is the failure mode that crashes a gantry
into its endstop, so the fake refuses and the controller tests can pin down what
the layer above does about it.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from scanner.motion_controller import MotionControllerPlugin
from scanner.plugin_setting import PluginSettingFloat, PluginSettingString
from scanner.probe_controller import ProbePlugin


class OutOfTravelError(ValueError):
    """The requested position lies outside the configured soft limits."""


@dataclass
class Call:
    """One recorded interaction with the fake device."""

    name: str
    args: tuple = ()
    kwargs: dict = field(default_factory=dict)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"{self.name}{self.args!r}"


class RecordingMotionPlugin(MotionControllerPlugin):
    """A 3-axis motion driver that moves instantly and remembers everything.

    Implements every abstract method on `MotionControllerPlugin` -- that is the
    point: it is the reference for what a conformant plugin looks like.
    """

    AXIS_NAMES = ("X", "Y", "Z")
    AXIS_UNITS = ("mm", "mm", "mm")

    def __init__(self, limits=((0.0, 300.0), (0.0, 300.0), (0.0, 300.0))) -> None:
        self.address = PluginSettingString("Resource Address", "fake://motion")
        self.max_velocity = PluginSettingFloat("Max Velocity", 50.0, value_min=0.0)
        super().__init__()
        self.add_setting_pre_connect(self.address)
        self.add_setting_post_connect(self.max_velocity)

        self._limits = tuple(limits)
        self.position = [0.0] * len(self._limits)
        self.calls: list[Call] = []
        self.connected = False
        self.homed = False
        self.estopped = False
        self.velocities: dict[int, float] = {}
        self.accelerations: dict[int, float] = {}
        self.rejected: list[dict[int, float]] = []

    # -- bookkeeping -------------------------------------------------------

    def _record(self, name, *args, **kwargs):
        self.calls.append(Call(name, args, kwargs))

    @property
    def call_names(self) -> list[str]:
        return [c.name for c in self.calls]

    def _check_travel(self, axis: int, value: float) -> None:
        low, high = self._limits[axis]
        if not (low <= value <= high):
            raise OutOfTravelError(
                f"axis {axis} target {value} outside [{low}, {high}]"
            )

    # -- MotionControllerPlugin -------------------------------------------

    def connect(self) -> None:
        self._record("connect")
        self.connected = True

    def disconnect(self) -> None:
        self._record("disconnect")
        self.connected = False

    def get_axis_display_names(self) -> tuple[str, ...]:
        return self.AXIS_NAMES

    def get_axis_units(self) -> tuple[str, ...]:
        return self.AXIS_UNITS

    # NOTE: the default of None mirrors every shipped plugin. MotionController
    # .connect() calls these with no arguments even though the ABC declares a
    # required parameter -- see test_motion_controller.py.
    def set_velocity(self, velocities: dict[int, float] = None) -> None:
        self._record("set_velocity", velocities)
        if velocities:
            self.velocities.update(velocities)

    def set_acceleration(self, accels: dict[int, float] = None) -> None:
        self._record("set_acceleration", accels)
        if accels:
            self.accelerations.update(accels)

    def move_relative(self, move_dist: dict[int, float]) -> dict[int, float] | None:
        self._record("move_relative", dict(move_dist))
        targets = {ax: self.position[ax] + d for ax, d in move_dist.items()}
        return self._apply(targets, move_dist)

    def move_absolute(self, move_pos: dict[int, float]) -> dict[int, float] | None:
        self._record("move_absolute", dict(move_pos))
        return self._apply(dict(move_pos), move_pos)

    def _apply(self, targets, requested):
        try:
            for axis, value in targets.items():
                self._check_travel(axis, value)
        except OutOfTravelError:
            self.rejected.append(dict(requested))
            raise
        for axis, value in targets.items():
            self.position[axis] = value
        return dict(targets)

    def home(self, axes: list[int] = None) -> dict[int, float]:
        axes = list(range(len(self.position))) if axes is None else list(axes)
        self._record("home", tuple(axes))
        for axis in axes:
            self.position[axis] = 0.0
        self.homed = True
        return {axis: 0.0 for axis in axes}

    def get_current_positions(self) -> tuple[float, ...]:
        return tuple(self.position)

    def is_moving(self, axis=None) -> bool:
        # Instant motion: never busy. Real drivers poll, so the controller must
        # cope with a driver that answers immediately.
        return False

    def get_endstop_minimums(self) -> tuple[float, ...]:
        return tuple(low for low, _ in self._limits)

    def get_endstop_maximums(self) -> tuple[float, ...]:
        return tuple(high for _, high in self._limits)

    def set_config(self, amps, idle_p, idle_time) -> None:
        self._record("set_config", amps, idle_p, idle_time)

    def emergency_stop(self) -> None:
        self._record("emergency_stop")
        self.estopped = True

    def show_radar(self) -> None:
        self._record("show_radar")


class RecordingProbePlugin(ProbePlugin):
    """A VNA stand-in returning deterministic, shape-correct sweeps."""

    def __init__(self, channels=("S11", "S21"), num_points=11) -> None:
        self.address = PluginSettingString("Resource Address", "fake://vna")
        super().__init__()
        self.add_setting_pre_connect(self.address)

        self._channels = tuple(channels)
        self._num_points = num_points
        self.calls: list[Call] = []
        self.connected = False
        self.visited: list[tuple[int, tuple]] = []

    def _record(self, name, *args):
        self.calls.append(Call(name, args))

    @property
    def call_names(self) -> list[str]:
        return [c.name for c in self.calls]

    def connect(self) -> None:
        self._record("connect")
        self.connected = True

    def disconnect(self) -> None:
        self._record("disconnect")
        self.connected = False

    def get_xaxis_coords(self) -> tuple[float, ...]:
        # A 1-11 GHz sweep, in Hz, like the Anritsu drivers report.
        start, stop = 1e9, 11e9
        step = (stop - start) / (self._num_points - 1)
        return tuple(start + i * step for i in range(self._num_points))

    def get_xaxis_units(self) -> str:
        return "Hz"

    def get_yaxis_units(self) -> tuple[str, ...] | str:
        return "dB"

    def get_channel_names(self) -> tuple[str, ...]:
        return self._channels

    def scan_begin(self) -> None:
        self._record("scan_begin")

    def scan_trigger_and_wait(self, scan_index, scan_location):
        self._record("scan_trigger_and_wait", scan_index, scan_location)
        return None

    def scan_read_measurement(self, scan_index, scan_location):
        self._record("scan_read_measurement", scan_index, scan_location)
        self.visited.append((scan_index, tuple(scan_location)))
        # Value encodes the point index so a test can prove data landed at the
        # coordinate it was measured at, rather than being shuffled.
        return [
            [float(scan_index) + c_ind / 100.0 for _ in range(self._num_points)]
            for c_ind in range(len(self._channels))
        ]

    def scan_end(self) -> None:
        self._record("scan_end")
