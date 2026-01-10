from scanner.motion_controller import MotionControllerPlugin
from scanner.plugin_setting import PluginSettingString, PluginSettingInteger, PluginSettingFloat
import tkinter as tk

class motion_controller_plugin(MotionControllerPlugin):

    def __init__(self):

        super().__init__()

        print("Motion Controller Simulator: Initialized")
        self.address = PluginSettingString("Resource Address", "Motion Controller Simulator")
        self.add_setting_pre_connect(self.address)

        # Initialize positions at center of 300x300x300 grid
        self.current_x = 150.0
        self.current_y = 150.0
        self.current_z = 150.0

        # Define 300x300x300 grid limits
        self.min_x = 0.0
        self.max_x = 300.0
        self.min_y = 0.0
        self.max_y = 300.0
        self.min_z = 0.0
        self.max_z = 300.0

    def connect(self):
        print("Motor Controller Simulator: Connected")
        print(f"Grid limits: X[{self.min_x}-{self.max_x}], Y[{self.min_y}-{self.max_y}], Z[{self.min_z}-{self.max_z}]")

    def disconnect(self):
        print("Disconnected")

    def get_axis_display_names(self) -> tuple[str, ...]:
        return ("X", "Y", "Z")

    def get_axis_units(self) -> tuple[str, ...]:
        return ("mm", "mm", "mm")


    def set_velocity(self, velocities: dict[int, float] = None) -> None:
        print(f"Setting velocities: {velocities}")

    def set_acceleration(self, accels: dict[int, float] = None) -> None:
        print(f"Setting accelerations: {accels}")


    def move_relative(self, move_dist: dict[int, float]) -> dict[int, float] | None:
        """Move relative to current position."""
        for axis, distance in move_dist.items():
            if axis == 0:  # X axis
                self.current_x = max(self.min_x, min(self.max_x, self.current_x + distance))
            elif axis == 1:  # Y axis
                self.current_y = max(self.min_y, min(self.max_y, self.current_y + distance))
            elif axis == 2:  # Z axis
                self.current_z = max(self.min_z, min(self.max_z, self.current_z + distance))

        print(f"Moved relative by {move_dist}. New position: ({self.current_x:.2f}, {self.current_y:.2f}, {self.current_z:.2f})")
        return {0: self.current_x, 1: self.current_y, 2: self.current_z}

    def move_absolute(self, move_pos: dict[int, float]) -> dict[int, float] | None:
        """Move to absolute position."""
        for axis, position in move_pos.items():
            if axis == 0:  # X axis
                self.current_x = max(self.min_x, min(self.max_x, position))
            elif axis == 1:  # Y axis
                self.current_y = max(self.min_y, min(self.max_y, position))
            elif axis == 2:  # Z axis
                self.current_z = max(self.min_z, min(self.max_z, position))

        print(f"Moved to absolute position {move_pos}. Current: ({self.current_x:.2f}, {self.current_y:.2f}, {self.current_z:.2f})")
        return {0: self.current_x, 1: self.current_y, 2: self.current_z}


    def home(self):
        """Home all axes to minimum positions."""
        self.current_x = self.min_x
        self.current_y = self.min_y
        self.current_z = self.min_z
        print(f"Homed all axes to ({self.current_x}, {self.current_y}, {self.current_z})")



    def get_current_positions(self) -> tuple[float, ...]:
        """Return current positions of all axes."""
        return (self.current_x, self.current_y, self.current_z)

    def get_endstop_minimums(self) -> tuple[float, ...]:
        """Return minimum positions for all axes."""
        return (self.min_x, self.min_y, self.min_z)

    def get_endstop_maximums(self) -> tuple[float, ...]:
        """Return maximum positions for all axes."""
        return (self.max_x, self.max_y, self.max_z)

    def set_config(self, amps, idle_p, idle_time):
        print(f"Setting config: amps={amps}, idle_p={idle_p}, idle_time={idle_time}")

    def is_moving(self, axis=None) -> bool:
        """Return False since simulator moves instantly."""
        return False