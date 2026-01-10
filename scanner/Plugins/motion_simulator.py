from scanner.motion_controller import MotionControllerPlugin
from scanner.plugin_setting import PluginSettingString, PluginSettingInteger, PluginSettingFloat
import tkinter as tk

class motion_controller_plugin(MotionControllerPlugin):

    def __init__(self):

        super().__init__()

        print("Motion Controller Simulator: Initiallized")
        self.address = PluginSettingString("Resource Address", "Motion Controller Simulator")
        self.add_setting_pre_connect(self.address)
    def connect(self):
        print("Motor Controller Simulator: Connected")

    def disconnect(self):
        print("Disconnected")

    def get_axis_display_names(self) -> tuple[str, ...]:
        pass

    def get_axis_units(self) -> tuple[str, ...]:
        pass


    def set_velocity(self, velocities: dict[int, float] = None) -> None:
        pass

    def set_acceleration(self, accels: dict[int, float] = None) -> None:
        pass


    def move_relative(self, move_dist: dict[int, float]) -> dict[int, float] | None:
        pass

    def move_absolute(self, move_pos: dict[int, float]) -> dict[int, float] | None:

        self.get_current_positions()
        print(f"Moving to absolute position: {move_pos}")


    def home(self):
        print("Homing all axes")



    def get_current_positions(self) -> tuple[float, ...]:
        print("Getting current positions")
        response = "X:10.00 Y:20.00 Z:30.00"
        split_response = response.split()
        x_pos = float(split_response[0][2:-1])
        y_pos = float(split_response[1][2:-1])
        z_pos = float(split_response[2][2:-1])
        response_split = (x_pos, y_pos, z_pos)
        print(response_split)
        print(response_split[2])
        return response_split

    def get_endstop_minimums(self) -> tuple[float, ...]:
        pass

    def get_endstop_maximums(self) -> tuple[float, ...]:
        pass

    def set_config(self, amps,idle_p, idle_time):
        pass

    def is_moving(self, axis=None):
        movement = [False,False]
        return movement