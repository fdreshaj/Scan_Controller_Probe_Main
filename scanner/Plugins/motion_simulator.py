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
        
        pass
        
        
    def home(self, axes: list[int]) -> dict[int, float]:
        pass


    def get_current_positions(self) -> tuple[float, ...]:
        pass
    
    def get_endstop_minimums(self) -> tuple[float, ...]:
        pass
    
    def get_endstop_maximums(self) -> tuple[float, ...]:
        pass
    
    def set_config(self, amps,idle_p, idle_time):
        pass
    
    def is_moving(self, axis=None):
        movement = [False,False]
        return movement