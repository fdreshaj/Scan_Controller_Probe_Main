from scanner.motion_controller import MotionControllerPlugin
from scanner.plugin_setting import PluginSettingString, PluginSettingInteger, PluginSettingFloat
import tkinter as tk

class motion_controller_plugin(MotionControllerPlugin):

    def __init__(self):

        super().__init__()

        print("Motion Controller Simulator: Initialized")

        # Scanner type selection for boundary checking
        self.scanner_type = PluginSettingString(
            "Scanner Type",
            "N-d Scanner",
            select_options=["Big Scanner", "N-d Scanner"],
            restrict_selections=True
        )

        self.address = PluginSettingString("Resource Address", "Motion Controller Simulator")

        self.add_setting_pre_connect(self.scanner_type)
        self.add_setting_pre_connect(self.address)

        # Position tracking variables
        self.current_position = [0.0, 0.0, 0.0]  # [X, Y, Z]
        self.is_homed = False

        # Boundary limits based on scanner type
        self.x_min = 0.0
        self.x_max = 0.0
        self.y_min = 0.0
        self.y_max = 0.0
        self.z_min = 0.0
        self.z_max = 0.0

    def connect(self):
        """Connect to simulator and set boundary limits based on scanner type."""
        print("Motor Controller Simulator: Connected")

        # Set boundary limits based on scanner type
        scanner_type_str = self.scanner_type.value
        if scanner_type_str == "Big Scanner":
            # Big Scanner: 600x600 mm (X, Y only)
            self.x_min = 0.0
            self.x_max = 600.0
            self.y_min = 0.0
            self.y_max = 600.0
            self.z_min = 0.0
            self.z_max = 0.0  # No Z axis for Big Scanner
            print("Scanner boundaries set: Big Scanner (600x600 mm, X-Y only)")
        else:  # "N-d Scanner"
            # N-d Scanner: 300x300x300 mm cube
            self.x_min = 0.0
            self.x_max = 300.0
            self.y_min = 0.0
            self.y_max = 300.0
            self.z_min = 0.0
            self.z_max = 300.0
            print("Scanner boundaries set: N-d Scanner (300x300x300 mm cube)")

    def disconnect(self):
        print("Disconnected")

    def get_axis_display_names(self) -> tuple[str, ...]:
        return ("X", "Y", "Z")

    def get_axis_units(self) -> tuple[str, ...]:
        return ("mm", "mm", "mm")


    def set_velocity(self, velocities: dict[int, float] = None) -> None:
        print(f"Simulator: Set velocity to {velocities}")

    def set_acceleration(self, accels: dict[int, float] = None) -> None:
        print(f"Simulator: Set acceleration to {accels}")


    def move_relative(self, move_dist: dict[int, float]) -> dict[int, float] | None:
        """
        Move relative distance with boundary checking.

        Args:
            move_dist: Dictionary mapping axis index to relative distance

        Raises:
            ValueError: If movement would violate endstop boundaries
        """
        if not self.is_homed:
            raise RuntimeError("Motors must be homed before relative movement. Call home() first.")

        if not isinstance(move_dist, dict) or not move_dist:
            raise ValueError("Error: Input must be a non-empty dictionary.")

        # Calculate target positions and check boundaries FIRST
        target_positions = {}
        for axis_idx, distance in move_dist.items():
            if axis_idx not in [0, 1, 2]:
                print(f"Warning: Unexpected axis index '{axis_idx}'. Skipping.")
                continue

            target_pos = self.current_position[axis_idx] + distance
            target_positions[axis_idx] = target_pos

            # Check boundaries
            if axis_idx == 0:  # X axis
                if target_pos < self.x_min or target_pos > self.x_max:
                    raise ValueError(
                        f"ENDSTOP VIOLATION: X-axis movement to {target_pos:.2f} mm "
                        f"exceeds boundaries [{self.x_min:.2f}, {self.x_max:.2f}] mm. "
                        f"Command stopped."
                    )
            elif axis_idx == 1:  # Y axis
                if target_pos < self.y_min or target_pos > self.y_max:
                    raise ValueError(
                        f"ENDSTOP VIOLATION: Y-axis movement to {target_pos:.2f} mm "
                        f"exceeds boundaries [{self.y_min:.2f}, {self.y_max:.2f}] mm. "
                        f"Command stopped."
                    )
            elif axis_idx == 2:  # Z axis
                if target_pos < self.z_min or target_pos > self.z_max:
                    raise ValueError(
                        f"ENDSTOP VIOLATION: Z-axis movement to {target_pos:.2f} mm "
                        f"exceeds boundaries [{self.z_min:.2f}, {self.z_max:.2f}] mm. "
                        f"Command stopped."
                    )

        # Only update positions after ALL boundary checks pass
        for axis_idx, target_pos in target_positions.items():
            self.current_position[axis_idx] = target_pos

        print(f"Simulator: Moved relative {move_dist}")
        print(f"Position updated: X={self.current_position[0]:.2f}, Y={self.current_position[1]:.2f}, Z={self.current_position[2]:.2f}")

        return None

    def move_absolute(self, move_pos: dict[int, float]) -> dict[int, float] | None:
        """
        Move to absolute position with boundary checking and position tracking.

        Args:
            move_pos: Dictionary mapping axis index to target position {0: x_pos, 1: y_pos, 2: z_pos}

        Raises:
            ValueError: If movement would violate endstop boundaries
        """
        if not self.is_homed:
            raise RuntimeError("Motors must be homed before absolute movement. Call home() first.")

        if not isinstance(move_pos, dict) or not move_pos:
            raise ValueError("Error: Input must be a non-empty dictionary.")

        # Check boundaries BEFORE executing movement
        for axis_idx, target_pos in move_pos.items():
            if axis_idx == 0:  # X axis
                if target_pos < self.x_min or target_pos > self.x_max:
                    raise ValueError(
                        f"ENDSTOP VIOLATION: X-axis movement to {target_pos:.2f} mm "
                        f"exceeds boundaries [{self.x_min:.2f}, {self.x_max:.2f}] mm. "
                        f"Command stopped."
                    )
            elif axis_idx == 1:  # Y axis
                if target_pos < self.y_min or target_pos > self.y_max:
                    raise ValueError(
                        f"ENDSTOP VIOLATION: Y-axis movement to {target_pos:.2f} mm "
                        f"exceeds boundaries [{self.y_min:.2f}, {self.y_max:.2f}] mm. "
                        f"Command stopped."
                    )
            elif axis_idx == 2:  # Z axis
                if target_pos < self.z_min or target_pos > self.z_max:
                    raise ValueError(
                        f"ENDSTOP VIOLATION: Z-axis movement to {target_pos:.2f} mm "
                        f"exceeds boundaries [{self.z_min:.2f}, {self.z_max:.2f}] mm. "
                        f"Command stopped."
                    )

        # Execute movement and update positions
        for axis_idx, target_pos in move_pos.items():
            if axis_idx in [0, 1, 2]:
                self.current_position[axis_idx] = target_pos

        print(f"Simulator: Moved to absolute position {move_pos}")
        print(f"Position updated: X={self.current_position[0]:.2f}, Y={self.current_position[1]:.2f}, Z={self.current_position[2]:.2f}")

        return None


    def home(self, axes=None):
        """
        Home the specified axes and initialize position tracking.

        After homing:
        - Big Scanner: Position is (0, 0, 0)
        - N-d Scanner: Position is (0, 0, 300) - Z starts at top

        Args:
            axes: List of axis indices to home (e.g., [0, 1, 2])

        Returns:
            Dictionary of homed positions
        """
        if axes is None:
            axes = [0, 1, 2]  # Home all axes by default

        print(f"Simulator: Homing axes {axes}")

        # Set initial position based on scanner type
        scanner_type_str = self.scanner_type.value
        if scanner_type_str == "N-d Scanner":
            # N-d Scanner: Z starts at 300 mm (top of cube)
            self.current_position = [0.0, 0.0, 300.0]
            print("Homing complete. Position initialized to (0, 0, 300) mm")
        else:
            # Big Scanner: All axes at 0
            self.current_position = [0.0, 0.0, 0.0]
            print("Homing complete. Position initialized to (0, 0, 0) mm")

        self.is_homed = True

        return {axis: self.current_position[axis] for axis in axes}



    def get_current_positions(self) -> tuple[float, ...]:
        """
        Return current tracked positions.

        Returns:
            tuple: (x, y, z) positions in mm
        """
        return tuple(self.current_position)

    def get_endstop_minimums(self) -> tuple[float, ...]:
        """Return minimum position limits for all axes."""
        return (self.x_min, self.y_min, self.z_min)

    def get_endstop_maximums(self) -> tuple[float, ...]:
        """Return maximum position limits for all axes."""
        return (self.x_max, self.y_max, self.z_max)

    def set_config(self, amps,idle_p, idle_time):
        print(f"Simulator: Set config - amps={amps}, idle_p={idle_p}, idle_time={idle_time}")

    def is_moving(self, axis=None):
        """
        Check if axes are moving.

        Returns:
            List of booleans for each axis [X_moving, Y_moving, Z_moving]
        """
        # Simulator: Always return False (not moving)
        return [False, False, False]