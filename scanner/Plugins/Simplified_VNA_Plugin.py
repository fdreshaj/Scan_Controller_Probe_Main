from scanner.probe_controller import ProbePlugin
from scanner.plugin_setting import PluginSettingString, PluginSettingInteger, PluginSettingFloat
from scanner.MS461xxVISA_Implementation import InstrumentConnection
import pyvisa
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import scanner.Plugins.VNA_List_Sparams as VNA_List_Sparams
import re
import h5py
import numpy as np
from datetime import datetime
import os
### This plugin is for the MS46524B 4 port VNA, 


class VNA_Plugin(ProbePlugin):
    

    def __init__(self):
        super().__init__()
        self.vna = None
        self.frequency_data_query = []
        self.s_param_interest_data_query = []
        
        #self.address = PluginSettingString("Resource Address", "TCPIP0::169.254.250.89::inst0::INSTR") Testing, this should be default for this VNA
        self.address = PluginSettingString("Resource Address", "TCPIP0::10.24.10.58::5001::SOCKET")
        self.timeout = PluginSettingInteger("Timeout (ms)", 20000)

        

        self.freq_mode = PluginSettingString(
            "Frequency Mode Query or Write", "Query",
            select_options=["Query", "Write"], restrict_selections=True
        )

        
        self.freq_start = PluginSettingFloat("Start Freq (Hz)", 1e9)
        
        self.freq_stop = PluginSettingFloat("Stop Freq (Hz)", 4e9)

        self.if_bandwidth = PluginSettingFloat("IF Bandwidth (Hz)", 10000)   
        self.vna_type = PluginSettingString(
            "Choose VNA", "MS46524B",
            select_options=["MS46524B", "MS46131A"], restrict_selections=True
        )

        self.add_setting_pre_connect(self.vna_type)
        self.add_setting_pre_connect(self.address)
        
        self.add_setting_pre_connect(self.timeout)
        
        self.add_setting_pre_connect(self.freq_mode)
        
        self.add_setting_pre_connect(self.freq_start)
        
        self.add_setting_pre_connect(self.freq_stop)

        self.add_setting_pre_connect(self.if_bandwidth)


    def connect(self):
        vna_pick = PluginSettingString.get_value_as_string(self.vna_type)
   
        self.vna=InstrumentConnection(self.address.value, self.timeout.value).connect()
        
        
            
        if self.freq_mode.value == "Query":

            start_Frequency = self.vna.query(":SENS1:FREQ:STAR?")
            stop_Frequency = self.vna.query(":SENS1:FREQ:STOP?")
            intermediate_Frequency = self.vna.query(":SENS1:BAND?")

            print(f"VNA start frequency is: {start_Frequency} Hz")
            print(f"VNA stop frequency is: {stop_Frequency} Hz")
            print(f"VNA IF bandwidth frequency is: {intermediate_Frequency} Hz")

            
            
            PluginSettingFloat.set_value_from_string(self.freq_start, f"{start_Frequency}")
            
            PluginSettingFloat.set_value_from_string(self.freq_stop, f"{stop_Frequency}")

            PluginSettingFloat.set_value_from_string(self.if_bandwidth, f"{intermediate_Frequency}")


        elif self.freq_mode.value == "Write":
            
            self.vna.write(f":SENS1:FREQ:STAR {self.freq_start.value}")
            self.vna.write(f":SENS1:FREQ:STOP {self.freq_stop.value}")
            self.vna.write(f":SENS1:BAND {self.if_bandwidth.value}")

        else:
            print("__Incorrect Input on frequency mode setting__")

        if vna_pick == "MS46524B":
           self.selected_params = VNA_List_Sparams.s_parameter_selection_VNA_n_channels(4)
        elif vna_pick == "MS46131A":
             self.selected_params = VNA_List_Sparams.s_parameter_selection_VNA_n_channels(1)
        
       
        self.vna.write(f":CALC1:PAR:COUN {len(self.selected_params)}")

        for i in range(1,len(self.selected_params)+1):
            
            self.vna.write(f"CALC1:PAR{i}:DEF {self.selected_params[i-1]}")
            self.vna.write(f":CALC1:PAR{i}:FORM: REIM")
            

        # maybe make user changable TODO:
        #self.vna.write(":SENS1:SWE:POIN 501")
        
        
        self.vna.write(":SENS1:HOLD:FUNC HOLD")
        
       
        opc_done = self.vna.query("*OPC?")

        if not (opc_done == "1"):
            print(f"Error, Opc returned unexpected value while waiting for a single sweep to finish (expected '1', received {opc_done}); ending code execution.")
            self.vna.close()

        self.frequency_data_query = self.vna.query(":SENS1:FREQ:DATA?")
    
        #2d array
        # self.s_param_interest_data_query=[]

        # for j in range(1,len(self.selected_params)+1):

        #     query_list = self.vna.query(f":CALC1:PAR{j}:DATA:SDAT?")

        #     self.s_param_interest_data_query.append(query_list)
            

    def disconnect(self):
        if self.vna:
            self.vna.close()

    def get_xaxis_coords(self):
        
        raw = self.vna.query(":SENS1:FREQ:DATA?")
        
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
        self.vna.write(":TRIG:SING")
        self.vna.query("*OPC?")


    def scan_trigger_and_wait(self, scan_index=None, scan_location=None):
        #currently using for hdf5 testing
        self.scan_read_measurement_hdf5()

    def scan_end(self):
        pass

    def _strip_block(self, raw):
        if raw.startswith("#"):
            n = int(raw[1]); raw = raw[2+n:]
        return re.split(r"[,\s]+", raw.strip())

    def scan_read_measurement(self, scan_index=None, scan_location=None):
        results = {}
        for idx, name in enumerate(self.get_channel_names(), start=1):
            raw = self.vna.query(f":CALC1:PAR{idx}:DATA:SDAT?")
            tokens = self._strip_block(raw)
            vals = list(map(float, tokens))
            results[name] = np.array([complex(vals[i], vals[i+1])
                            for i in range(0, len(vals), 2)])
        return results
    
    