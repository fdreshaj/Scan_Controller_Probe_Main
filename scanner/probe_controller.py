
from abc import ABC, abstractmethod
from typing import Sequence, Any

from scanner.plugin_setting import PluginSetting


class ProbePlugin(ABC):
    settings_pre_connect: list[PluginSetting]
    settings_post_connect: list[PluginSetting]

    def __init__(self) -> None:
        self.settings_pre_connect = []
        self.settings_post_connect = []

    def add_setting_pre_connect(self, setting: PluginSetting):
        self.settings_pre_connect.append(setting)
    
    def add_setting_post_connect(self, setting: PluginSetting):
        self.settings_post_connect.append(setting)

    @abstractmethod
    def connect(self) -> None:
        pass
    @abstractmethod
    def disconnect(self) -> None:
        pass

    @abstractmethod
    def get_xaxis_coords(self) -> tuple[float, ...]:
        pass
    @abstractmethod
    def get_xaxis_units(self) -> str:
        pass
    @abstractmethod
    def get_yaxis_units(self) -> tuple[str, ...] | str:
        pass
    @abstractmethod
    def get_channel_names(self) -> tuple[str, ...]:
        pass

    @abstractmethod
    def scan_begin(self) -> None:
        pass
    @abstractmethod
    def scan_trigger_and_wait(self, scan_index: int, scan_location: tuple[float, ...]) -> list[list[float]] | list[float] | None:
        pass
    @abstractmethod
    def scan_read_measurement(self, scan_index: int, scan_location: tuple[float, ...]) -> list[list[float]] | list[float] | None:
        pass
    @abstractmethod
    def scan_end(self) -> None:
        pass
        


class ProbeController:
    _probe: ProbePlugin
    _is_probe_connected: bool

    def __init__(self, probe: ProbePlugin) -> None:
        self._probe = probe
        self._is_probe_connected = False

    def connect(self) -> None:
        self._probe.connect()
        self._is_probe_connected = True
    
    def disconnect(self) -> None:
        was_connected = self._is_probe_connected
        self._is_probe_connected = False
        if was_connected:
            self._probe.disconnect()
    
    def must_be_connected(self) -> None:
        if not self._is_probe_connected:
            raise ConnectionError("Probe must be connected to use this functionality.")
        
    def is_connected(self) -> bool:
        return self._is_probe_connected
    
    def scan_begin(self) -> None:
        self.must_be_connected()
        self._probe.scan_begin()
    
    def scan_trigger_and_wait(self, scan_index: int, scan_location: tuple[float, ...]) -> list[list[float]] | list[float] | None:
        self.must_be_connected()
        return self._probe.scan_trigger_and_wait(scan_index, scan_location)
    
    def scan_read_measurement(self, scan_index: int, scan_location: tuple[float, ...]) -> list[list[float]] | list[float] | None:
        self.must_be_connected()
        return self._probe.scan_read_measurement(scan_index, scan_location)
    
    def scan_end(self) -> None:
        self.must_be_connected()
        self._probe.scan_end()