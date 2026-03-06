from scanner.probe_controller import ProbePlugin
from scanner.plugin_setting import PluginSettingString, PluginSettingInteger, PluginSettingFloat
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import scanner.Plugins.VNA_List_Sparams as VNA_List_Sparams
import re
import numpy as np
import scanner.Plugins.fmcw_connection.TRA_240_097 as fmcw_connection   

class fmcw_Plugin(ProbePlugin):
    def __init__(self):
        super().__init__()
        self.fmcw = None
        self.frequency_data_query = []
        self.s_param_interest_data_query = []
        
        self.nFreqPoints = PluginSettingInteger("Number of Frequency Points", 201)
        self.startFreqGHz = PluginSettingFloat("Start Frequency (GHz)", 220.0)
        self.stopFreqGHz = PluginSettingFloat("Stop Frequency (GHz)", 269.5)
        self.sweepTime_ms = PluginSettingInteger("Sweep Time (ms)", 1)
        ## Need to write 
        ## self.adress =- 
        ## self.timeout = PluginSettingInteger("Timeout (ms)", )
        self.add_setting_pre_connect(self.nFreqPoints)
        self.add_setting_pre_connect(self.startFreqGHz)
        self.add_setting_pre_connect(self.stopFreqGHz)
        self.add_setting_pre_connect(self.sweepTime_ms)
        #self.add_setting_pre_connect(self.address)
        #self.add_setting_pre_connect(self.timeout)
        
        
    def connect(self):
        self.fmcw = fmcw_connection.TRA_240_097()
        args = [str(self.nFreqPoints.value), str(self.startFreqGHz.value), str(self.stopFreqGHz.value), str(self.sweepTime_ms.value)]
        self.kwargs = dict(zip(self.fmcw.get_parameters_list(), args))
        
        self.fmcw.initialize(self.kwargs)
        
        self.selected_params = self.fmcw.get_channel_names(self.kwargs)
        print("Initiallized FMCW radar")

    
    def disconnect(self):
        if self.fmcw:
            self.fmcw.close(self.kwargs)
            
            
    
    def get_xaxis_coords(self):
        
        #raw = #raw freq data coords 
        raw = self.fmcw.get_frequency_vector_GHz(self.kwargs)
        print(raw)
        if raw.startswith("#"):
            hdr_digits = int(raw[1])           
            raw = raw[2 + hdr_digits:]         

        
        parts = re.split(r"[,\s]+", raw.strip())
        return tuple(map(float, parts))
    
    def get_xaxis_units(self):
        return "Hz"

    def get_yaxis_units(self):
        pass

    def get_channel_names(self):
        return self.selected_params 
    
    def scan_begin(self):
       pass


    def scan_trigger_and_wait(self, scan_index=None, scan_location=None):
        
        pass

    def scan_end(self):
        pass

    def _strip_block(self, raw):
        if raw.startswith("#"):
            n = int(raw[1]); raw = raw[2+n:]
        return re.split(r"[,\s]+", raw.strip())

    def scan_read_measurement(self, scan_index=None, scan_location=None):
        results = {}
        for idx, name in enumerate(self.get_channel_names(), start=1):
           
            raw = self.fmcw.measure(self.kwargs)
            tokens = self._strip_block(raw)
            vals = list(map(float, tokens))
            results[name] = np.array([complex(vals[i], vals[i+1])
                            for i in range(0, len(vals), 2)])
        return results