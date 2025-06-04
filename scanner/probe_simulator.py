
import math
import time

from scanner.probe_controller import ProbePlugin
from scanner.plugin_setting import PluginSettingInteger, PluginSettingFloat, PluginSettingString


class ProbeSimulator(ProbePlugin):
    num_channels: PluginSettingInteger
    num_points_per_channel: PluginSettingInteger
    xaxis_min: PluginSettingFloat
    xaxis_max: PluginSettingFloat
    xaxis_unit: PluginSettingString
    yaxis_unit: PluginSettingString
    measure_time: PluginSettingFloat
    init_time: PluginSettingFloat

    def __init__(self) -> None:
        self.num_channels = PluginSettingInteger("Number of Channels", 2, value_min=1)
        self.num_points_per_channel = PluginSettingInteger("Points Per Channel", 20, value_min=2)
        self.xaxis_min = PluginSettingFloat("X-axis Min", 1)
        self.xaxis_max = PluginSettingFloat("X-axis Max", 10)
        self.xaxis_unit = PluginSettingString("X-axis Unit", "GHz")
        self.yaxis_unit = PluginSettingString("Y-axis Unit", "V")
        self.measure_time = PluginSettingFloat("Measurement Time (s)", 0.5, value_min=0.0)
        self.init_time = PluginSettingFloat("Initialization Time (s)", 1.0, value_min=0.0)
        super().__init__()
        self.add_setting_post_connect(self.num_channels)
        self.add_setting_post_connect(self.num_points_per_channel)
        self.add_setting_post_connect(self.xaxis_min)
        self.add_setting_post_connect(self.xaxis_max)
        self.add_setting_post_connect(self.xaxis_unit)
        self.add_setting_post_connect(self.yaxis_unit)
        self.add_setting_post_connect(self.measure_time)
        self.add_setting_post_connect(self.init_time)
    
    def connect(self) -> None:
        pass
    
    def disconnect(self) -> None:
        pass
    
    
    def get_xaxis_coords(self) -> tuple[float, ...]:
        minVal = self.xaxis_min.value
        maxVal = self.xaxis_max.value
        num_points = self.num_points_per_channel.value
        step = (maxVal-minVal) / (num_points-1)
        return tuple(minVal + ii*step for ii in range(num_points))
    
    def get_xaxis_units(self) -> str:
        return self.xaxis_unit.value
    
    def get_yaxis_units(self) -> tuple[str, ...] | str:
        return self.yaxis_unit.value
    
    def get_channel_names(self) -> tuple[str, ...]:
        return tuple(f"Channel {ii+1}" for ii in range(self.num_channels.value))
    
    def scan_begin(self) -> None:
        time.sleep(self.init_time.value)
    
    def scan_trigger_and_wait(self, scan_index: int, scan_location: tuple[float, ...]) -> list[list[float]] | list[float] | None:
        return None
    
    def scan_read_measurement(self, scan_index: int, scan_location: tuple[float, ...]) -> list[list[float]] | list[float] | None:
        time.sleep(self.measure_time.value)
        num_channels = self.num_channels.value
        num_points = self.num_points_per_channel.value
        ret: list[list[float]] = []
        for c_ind in range(num_channels):
            ret.append([math.cos(c_ind * p_ind / (num_points - 1) * (2*math.pi)) for p_ind in range(num_points)])
        return ret
    
    def scan_end(self) -> None:
        pass






