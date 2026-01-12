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
    basename: str = ""

    def __init__(self):

        super().__init__()

        self.pluginMode = PluginSettingString(
                "Plugin Selection", "No Plugin Selected" if PluginSwitcher.plugin_name == "" else PluginSwitcher.plugin_name,
                select_options=["No Plugin Selected" if PluginSwitcher.plugin_name == "" else PluginSwitcher.plugin_name],
                restrict_selections=True
            )
        self.add_setting_pre_connect(self.pluginMode)

    @staticmethod
    def select_plugin() -> bool:
        """Open file dialog to select a plugin. Returns True if a plugin was selected, False otherwise."""
        filename = fd.askopenfilename(title="Select Probe Plugin", filetypes=[("Python files", "*.py")])

        if not filename:  # User cancelled
            return False

        basename = os.path.basename(filename)
        print(f"Selected plugin file: {basename}")

        import importlib.util
        import inspect

        spec = importlib.util.spec_from_file_location("plugin_mod", filename)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        from scanner.probe_controller import ProbePlugin

        plugin_cls = None
        for name, obj in inspect.getmembers(mod, inspect.isclass):
            if obj.__module__ == mod.__name__ and issubclass(obj, ProbePlugin) and obj is not ProbePlugin:
                plugin_cls = obj
                break

        if plugin_cls is None:
            print("Error: No ProbePlugin class found in selected file")
            return False

        s = str(plugin_cls)                        # "<class 'plugin_mod.VNAProbePlugin'>"
        PluginName = s.split('.')[-1].rstrip("'>")
        PluginSwitcher.plugin_name = PluginName
        PluginSwitcher.basename = basename

        print(f"Plugin selected: {PluginName}")
        return True

    def connect(self) -> None:
        """Connect is not used for PluginSwitcher - selection happens via select_plugin()"""
        pass

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

