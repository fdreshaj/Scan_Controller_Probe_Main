
from typing import Sequence, Any

from scanner.plugin_setting import PluginSettingString, PluginSettingInteger
from scanner.motion_controller import MotionControllerPlugin

import zmq



DEFAULT_PORT = 5556


class GcodeSimulator(MotionControllerPlugin):
    port: PluginSettingInteger
    number_of_axes: PluginSettingInteger
    
    _socket: zmq.Socket

    axis_names = ("X", "Y", "Z", "W")

    def __init__(self) -> None:
        self.port = PluginSettingInteger("Port Number", DEFAULT_PORT)
        self.number_of_axes = PluginSettingInteger("Number of Axes", 0, read_only=True)
        super().__init__()
        self.add_setting_pre_connect(self.port)
        self.add_setting_post_connect(self.number_of_axes)
    
    def write_line(self, line: str) -> None:
        self._socket.send_string(f"{line}\n")

    def read_line(self) -> str:
        return self._socket.recv_string()

    def format_axis_command(self, command: str, axis_vals: dict[int, float]) -> str:
        return f"{command} " + " ".join(f"{self.axis_names[axis]}{vel}" for axis,vel in axis_vals.items())
    
    def check_for_error(self, return_code: str) -> str:
        if return_code.startswith("Error"):
            raise ValueError(f"Device returned error message: '{return_code}'.")
        return return_code

    def connect(self) -> None:
        self._context = zmq.Context()
        self._socket = self._context.socket(zmq.PAIR)
        self._socket.connect(f"tcp://localhost:{self.port.value}")
        
        self.get_current_positions()
        self.number_of_axes.value = 4

    def disconnect(self) -> None:
        self.number_of_axes.value = 0
        # self.port.close()

    def get_axis_display_names(self) -> tuple[str, ...]:
        return self.axis_names
    
    def get_axis_units(self) -> tuple[str, ...]:
        return tuple(["mm"] * len(self.axis_names))
    
    def set_velocity(self, velocities: dict[int, float]) -> None:
        self.write_line(self.format_axis_command("V00", velocities))
        self.check_for_error(self.read_line())

    def set_acceleration(self, accel: dict[int, float]) -> None:
        self.write_line(self.format_axis_command("A00", accel))
        self.check_for_error(self.read_line())


    def move_relative(self, move_dist: dict[int, float]) -> dict[int, float] | None:
        self.write_line(self.format_axis_command("G01", move_dist))
        self.check_for_error(self.read_line())
        return None

    def move_absolute(self, move_pos: dict[int, float]) -> dict[int, float] | None:
        self.write_line(self.format_axis_command("G00", move_pos))
        self.check_for_error(self.read_line())
        return None

    def home(self, axes: list[int]) -> dict[int, float]:
        self.write_line("G28 + " " ".join(self.axis_names[axis] for axis in axes))
        self.check_for_error(self.read_line())
        return {axis:0.0 for axis in axes}


    def get_current_positions(self) -> tuple[float, ...]:
        self.write_line("G00?")
        ret = self.check_for_error(self.read_line())
        return tuple(float(pos.strip("XYZW")) for pos in ret.split())
    
    def is_moving(self) -> bool:
        self.write_line("Status?")
        ret = self.check_for_error(self.read_line())
        return ret == "Moving"

    def get_endstop_minimums(self) -> tuple[float, ...]:
        self.write_line("E00-?")
        ret = self.check_for_error(self.read_line())
        return tuple(float(pos.strip("XYZW")) for pos in ret.split())

    def get_endstop_maximums(self) -> tuple[float, ...]:
        self.write_line("E00+?")
        ret = self.check_for_error(self.read_line())
        return tuple(float(pos.strip("XYZW")) for pos in ret.split())





