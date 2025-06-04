from scanner.probe_controller import ProbePlugin
from scanner.plugin_setting import PluginSettingString, PluginSettingInteger, PluginSettingFloat
from itertools import product
import time

from scanner.plugin_setting import PluginSetting

from scanner.motion_controller import MotionController
from scanner.gcode_simulator import GcodeSimulator
from scanner.probe_simulator import ProbeSimulator
from scanner.VNA_Plugin import VNAProbePlugin

import csv

class PluginSwitcher(ProbePlugin):
    # _probe_controller: ProbeController
    
    def __init__(self):
        
        super().__init__()

        self.pluginMode = PluginSettingString(
                "Plugin Selection", "CHOOSE",
                select_options=["VNA MS46524B", "OTHER TBD","CHOOSE"], restrict_selections=True
            )
        self.add_setting_pre_connect(self.pluginMode)

    
    def connect(self) -> None:
        # if self.pluginMode == "VNA MS46524B":
        #    self._probe_controller = ProbePlugin(VNAProbePlugin())
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

