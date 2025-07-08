
from abc import ABC, abstractmethod
from typing import Sequence

from scanner.plugin_setting import PluginSetting

class ScanFileControllerPlugin(ABC):
    
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
    def is_connected(self) -> bool:
        pass
