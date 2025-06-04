from scanner.probe_controller import ProbePlugin
from scanner.plugin_setting import PluginSettingString, PluginSettingInteger, PluginSettingFloat
from itertools import product
import time

from scanner.plugin_setting import PluginSetting

from scanner.motion_controller import MotionController
from scanner.gcode_simulator import GcodeSimulator
from scanner.probe_simulator import ProbeSimulator
#from scanner.VNA_Plugin import VNAProbePlugin
import csv
import tkinter as tk
from tkinter import simpledialog
from tkinter import filedialog as fd
import os


class PluginSwitcher(ProbePlugin):
    # _probe_controller: ProbeController


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

        from scanner.probe_controller import ProbePlugin

        for name, obj in inspect.getmembers(mod, inspect.isclass):
            if obj.__module__ == mod.__name__ and issubclass(obj, ProbePlugin):
                
                plugin_cls = obj
                break
        
        s = str(plugin_cls)                        # "<class 'plugin_mod.VNAProbePlugin'>"
        PluginName = s.split('.')[-1].rstrip("'>")       
        PluginSwitcher.plugin_name = PluginName
        # from scanner.scanner import Scanner
        # self.scanner.scanner = Scanner()
        PluginSwitcher.basename = basename
        
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

    
    def scan_begin(self) -> None:
        pass
    
    def scan_trigger_and_wait(self, scan_index: int, scan_location: tuple[float, ...]) -> list[list[float]] | list[float] | None:
        pass
    
    def scan_read_measurement(self, scan_index: int, scan_location: tuple[float, ...]) -> list[list[float]] | list[float] | None:
        pass
    
    def scan_end(self) -> None:
        pass

