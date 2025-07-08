
from scanner.scan_file_controller import ScanFileControllerPlugin
from scanner.plugin_setting import PluginSettingString, PluginSettingInteger, PluginSettingFloat
import tkinter as tk
from tkinter import filedialog



class ScanFile(ScanFileControllerPlugin):
    
    _is_connected:bool 
    
    def __init__(self):
        super().__init__()
        
        self._is_connected = False
        
        self.file_type = PluginSettingString("File Type: ", "CSV", select_options=["CSV","HDF5",".Scan File"], restrict_selections=True)
        
        self.file_name = PluginSettingString("File Name: ", "Scan File")
        
        self.file_directory =PluginSettingString("File Directory: ", "File Dir")
         
        self.file_scan_dimensions = PluginSettingString(" Scan Dimensions: ", "Scan Dimensions")
       
        self.file_frequency_band = PluginSettingString(" Scan Frequency Band: ", "Frequency Band")
        
        self.file_material_descrip = PluginSettingString(" Scan Material Description: ", "Material Description")
        
        self.file_additional_info = PluginSettingString(" Additional Info: ", "N/A if not needed")

        self.add_setting_pre_connect(self.file_type)
        
        self.add_setting_pre_connect(self.file_name)
        
        self.add_setting_pre_connect(self.file_frequency_band)
        
        self.add_setting_pre_connect(self.file_scan_dimensions)

        self.add_setting_pre_connect(self.file_material_descrip)
        
        
        self.add_setting_pre_connect(self.file_additional_info)
        
        
        
        self.add_setting_post_connect(self.file_directory)
        
       
        
    def connect(self) -> None:
        self._is_connected = True
    
    
    def disconnect(self) -> None:
        self._is_connected = False
    
    
    def is_connected(self) -> bool:
        print(f"Connected Status Backend _is_connected: {self._is_connected}")
        return self._is_connected