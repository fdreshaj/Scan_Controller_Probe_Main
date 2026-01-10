
from scanner.scan_file_controller import ScanFileControllerPlugin
from scanner.plugin_setting import PluginSettingString, PluginSettingInteger, PluginSettingFloat
import tkinter as tk
from tkinter import filedialog
from datetime import datetime


class ScanFile(ScanFileControllerPlugin):
    
    _is_connected:bool 
    
    def __init__(self):
        super().__init__()
        
        self._is_connected = False
        
        self.file_type = PluginSettingString("File Type: ", "HDF5", select_options=["Bin","HDF5"], restrict_selections=True)
        
        self.file_name = PluginSettingString("File Name: ", f"{datetime.now().strftime("ScanFile_%Y-%m-%d_%H_%M_%S_%f")}")
         
        self.file_scan_dimensions = PluginSettingString(" Scan Dimensions: ", "Scan Dimensions")
       
        self.file_frequency_band = PluginSettingString(" Scan Frequency Band: ", "Frequency Band")
        
        self.file_material_descrip = PluginSettingString(" Scan Material Description: ", "Material Description")
        
        self.progress = PluginSettingString("Progress: ", "0%")

        self.add_setting_pre_connect(self.file_type)
        
        self.add_setting_pre_connect(self.file_name)
        
        self.add_setting_pre_connect(self.file_frequency_band)
        
        self.add_setting_pre_connect(self.file_scan_dimensions)

        self.add_setting_pre_connect(self.file_material_descrip)
        
        
    
        
    
       
        
    def connect(self) -> None:
        self._is_connected = True
    
    
    def disconnect(self) -> None:
        self._is_connected = False
    
    
    def is_connected(self) -> bool:
        print(f"Connected Status Backend _is_connected: {self._is_connected}")
        return self._is_connected
    
    def csv(self):
        pass

    def hdf5(self): 
        pass