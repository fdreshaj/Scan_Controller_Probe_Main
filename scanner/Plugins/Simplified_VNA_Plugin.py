from scanner.probe_controller import ProbePlugin
from scanner.plugin_setting import PluginSettingString, PluginSettingInteger, PluginSettingFloat
from scanner.MS461xxVISA_Implementation import InstrumentConnection
import pyvisa
import tkinter as tk


### This plugin is for the MS46524B 4 port VNA

class VNA_Plugin(ProbePlugin):


    def __init__(self):
        super().__init__()
        self.vna = None

        # Connection settings
        self.address = PluginSettingString("Resource Address", "TCPIP0::169.254.250.89::inst0::INSTR")
        self.timeout = PluginSettingInteger("Timeout (ms)", 20000)

        # Frequency settings

        self.freq_mode = PluginSettingString(
            "Frequency Mode Query or Write", "Query",
            select_options=["Query", "Write"], restrict_selections=True
        )

        self.s_param_interest = PluginSettingString(
            "Choose desired S parameter", "S11",
            select_options=["S11","S12","S13","S14","S21","S22","S23","S24","S31","S32","S33","S34","S41","S42","S43","S44"], restrict_selections=True
        )


        self.freq_start = PluginSettingFloat("Start Freq (Hz)", 1e9)
        
        self.freq_stop = PluginSettingFloat("Stop Freq (Hz)", 4e9)

        self.if_bandwidth = PluginSettingFloat("IF Bandwidth (Hz)", 10000)        

        # Add the Pre connect settings

        self.add_setting_pre_connect(self.address)
        
        self.add_setting_pre_connect(self.timeout)
        
        self.add_setting_pre_connect(self.freq_mode)
        
        self.add_setting_pre_connect(self.freq_start)
        
        self.add_setting_pre_connect(self.freq_stop)

        self.add_setting_pre_connect(self.if_bandwidth)

        self.add_setting_pre_connect(self.s_param_interest)


    def connect(self):
        self.vna=InstrumentConnection(self.address.value, self.timeout.value).connect()
        
        # Apply frequency settings Query or Write and implement start/stop/intermediate frequencies

        if self.freq_mode.value == "Query":

            ##### Add a button update for the queried value and grey it out

            start_Frequency = self.vna.query(":SENS1:FREQ:STAR?")
            stop_Frequency = self.vna.query(":SENS1:FREQ:STOP?")
            intermediate_Frequency = self.vna.query(":SENS1:BAND?")

            print(f"VNA start frequency is: {start_Frequency} Hz")
            print(f"VNA stop frequency is: {stop_Frequency} Hz")
            print(f"VNA IF bandwidth frequency is: {intermediate_Frequency} Hz")
            
            

        elif self.freq_mode.value == "Write":
            
            self.vna.write(f":SENS1:FREQ:STAR {self.freq_start.value}")
            self.vna.write(f":SENS1:FREQ:STOP {self.freq_stop.value}")
            self.vna.write(f":SENS1:BAND {self.if_bandwidth.value}")

        else:
            print("__Incorrect Input on frequency mode setting__")


        # Set number of traces, default traces are 4, it is set to 1 for now
        
        self.vna.write(":CALC1:PAR:COUN 1")

        # Set which S parameter you are interested in
        self.vna.write(f"CALC1:PAR1:DEF {self.s_param_interest}")
        
                
    def disconnect(self):
        if self.vna:
            self.vna.close()

    def get_xaxis_coords(self):
        pass 

    def get_xaxis_units(self):
        pass

    def get_yaxis_units(self):
        pass

    def get_channel_names(self):
        pass

    def scan_begin(self):
        self.vna.write(":TRIG:SING")
        self.vna.query("*OPC?")


    def scan_trigger_and_wait(self, scan_index, scan_location):
        pass

    def scan_end(self):
        pass

    def scan_read_measurement(self, scan_index, scan_location):
        pass

# class self.vna:

#     def __init__(self, resource_name, timeout):
#         self.resource_name = resource_name
#         self.timeout = timeout
#         self.q_response = None
#         self.shockline_visa = None
#         self.rm = pyvisa.ResourceManager()
#         self.connect()
#         self.shockline_visa.timeout = timeout

#     def connect(self):
#         try:
#             self.shockline_visa = self.rm.open_resource(self.resource_name)
#         except Exception as e:
#             print("Failed to initialize VISA connection, message error is :\n")
#             print(e)

#     def write(self, w_command):
#         try:
#             self.shockline_visa.write(w_command)
#         except Exception as e:
#             print(f'Failed to write command "{w_command}", message error is :\n')
#             print(e)

#     def query(self, q_command):
#         self.q_response = self.shockline_visa.query(q_command)
#         return self.q_response.rstrip()

#     def close(self):
#         try:
#             self.shockline_visa.close()
#             self.rm.close()
#         except Exception as e:
#             print("Failed to disconnect VISA connection, message error is :\n")
#             print(e)

