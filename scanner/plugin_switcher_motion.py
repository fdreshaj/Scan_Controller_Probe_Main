from scanner.probe_controller import ProbePlugin
from scanner.plugin_setting import PluginSettingString, PluginSettingInteger, PluginSettingFloat
from itertools import product
import time

from scanner.plugin_setting import PluginSetting

from scanner.motion_controller import MotionController
from scanner.motion_controller import MotionControllerPlugin
from scanner.gcode_simulator import GcodeSimulator
from scanner.probe_simulator import ProbeSimulator
#from scanner.VNA_Plugin import VNAProbePlugin
import csv
import tkinter as tk
from tkinter import simpledialog
from tkinter import filedialog as fd
import os


class PluginSwitcherMotion(MotionControllerPlugin):
    


    plugin_name: str = ""
    def __init__(self):
        
        super().__init__()

        self.pluginMode = PluginSettingString(
                "Plugin Selection", "Connect to desired Plugin",
                select_options=["Connect to desired Plugin"], restrict_selections=True
            )
        self.add_setting_pre_connect(self.pluginMode)


    
    def connect(self) -> None:
        filename = fd.askopenfilename()
        basename = os.path.basename(filename)
        print(basename)
        
        import importlib.util

        spec = importlib.util.spec_from_file_location("plugin_mod", filename)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        import inspect

        from scanner.motion_controller import MotionControllerPlugin

        for name, obj in inspect.getmembers(mod, inspect.isclass):
            if obj.__module__ == mod.__name__ and issubclass(obj, MotionControllerPlugin):
                
                plugin_cls = obj
                break
        
        s = str(plugin_cls)                        
        PluginName = s.split('.')[-1].rstrip("'>")       
        PluginSwitcherMotion.plugin_name = PluginName
        # from scanner.scanner import Scanner
        # self.scanner.scanner = Scanner()
        PluginSwitcherMotion.basename = basename
        
    def disconnect(self) -> None:
        pass
    
    def get_xaxis_coords(self) -> tuple[float, ...]:
        pass
    
    def get_xaxis_units(self) -> str:
        pass
    
    def get_yaxis_units(self) -> tuple[str, ...] | str:
        pass
    
    def get_channel_names(self) -> tuple[str, ...]:
        pass

    def set_config(self, amps, idle_p, idle_time):
        pass
    def scan_begin(self) -> None:
        pass
    
    def scan_trigger_and_wait(self, scan_index: int, scan_location: tuple[float, ...]) -> list[list[float]] | list[float] | None:
        pass
    
    def scan_read_measurement(self, scan_index: int, scan_location: tuple[float, ...]) -> list[list[float]] | list[float] | None:
        pass
    
    def scan_end(self) -> None:
        pass

    def get_axis_display_names(self) -> tuple[str, ...]:
        pass
    
    def get_axis_units(self) -> tuple[str, ...]:
        pass

    
    def set_velocity(self) -> None:
        pass
    
    def set_acceleration(self) -> None:
        pass

    
    def move_relative(self, move_dist: dict[int, float]) -> dict[int, float] | None:
        pass
    
    def move_absolute(self, move_pos: dict[int, float]) -> dict[int, float] | None:
        pass
    
    def home(self, axes: list[int]) -> dict[int, float]:
        pass

    
    def get_current_positions(self) -> tuple[float, ...]:
        pass
    
    def is_moving(self) -> bool:
        pass
    
    def get_endstop_minimums(self) -> tuple[float, ...]:
        pass
    
    def get_endstop_maximums(self) -> tuple[float, ...]:
        pass
