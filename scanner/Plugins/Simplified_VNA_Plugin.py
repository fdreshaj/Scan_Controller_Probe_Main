from scanner.probe_controller import ProbePlugin
from scanner.plugin_setting import PluginSettingString, PluginSettingInteger, PluginSettingFloat
from scanner.MS461xxVISA_Implementation import InstrumentConnection
import pyvisa
import tkinter as tk
from tkinter import ttk
#from tkinterPopUp import s_parameter_selection_VNA_n_channels
import scanner.Plugins.VNA_List_Sparams as VNA_List_Sparams
### This plugin is for the MS46524B 4 port VNA, 
#import VNA_List_Sparams

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

        # self.s_param_interest = PluginSettingString(
        #     "Choose desired S parameter", "S11",
        #     select_options=["S11","S12","S13","S14","S21","S22","S23","S24","S31","S32","S33","S34","S41","S42","S43","S44"], restrict_selections=True
        # )

        self.freq_start = PluginSettingFloat("Start Freq (Hz)", 1e9)
        
        self.freq_stop = PluginSettingFloat("Stop Freq (Hz)", 4e9)

        self.if_bandwidth = PluginSettingFloat("IF Bandwidth (Hz)", 10000)        

        # self.num_sparam_int = PluginSettingInteger("Desired num of s-params", 1)

        # Add the Pre connect settings

        self.add_setting_pre_connect(self.address)
        
        self.add_setting_pre_connect(self.timeout)
        
        self.add_setting_pre_connect(self.freq_mode)
        
        self.add_setting_pre_connect(self.freq_start)
        
        self.add_setting_pre_connect(self.freq_stop)

        self.add_setting_pre_connect(self.if_bandwidth)

        # self.add_setting_pre_connect(self.s_param_interest)

        # self.add_setting_pre_connect(self.num_sparam_int)

    def connect(self):
        self.vna=InstrumentConnection(self.address.value, self.timeout.value).connect()
        
        # Apply frequency settings Query or Write and implement start/stop/intermediate frequencies

        if self.freq_mode.value == "Query":

            start_Frequency = self.vna.query(":SENS1:FREQ:STAR?")
            stop_Frequency = self.vna.query(":SENS1:FREQ:STOP?")
            intermediate_Frequency = self.vna.query(":SENS1:BAND?")

            print(f"VNA start frequency is: {start_Frequency} Hz")
            print(f"VNA stop frequency is: {stop_Frequency} Hz")
            print(f"VNA IF bandwidth frequency is: {intermediate_Frequency} Hz")

            # Update Queried values
            
            PluginSettingFloat.set_value_from_string(self.freq_start, f"{start_Frequency}")
            
            PluginSettingFloat.set_value_from_string(self.freq_stop, f"{stop_Frequency}")

            PluginSettingFloat.set_value_from_string(self.if_bandwidth, f"{intermediate_Frequency}")


        elif self.freq_mode.value == "Write":
            
            self.vna.write(f":SENS1:FREQ:STAR {self.freq_start.value}")
            self.vna.write(f":SENS1:FREQ:STOP {self.freq_stop.value}")
            self.vna.write(f":SENS1:BAND {self.if_bandwidth.value}")

        else:
            print("__Incorrect Input on frequency mode setting__")


        # Set number of traces, num params -> num traces

        #self.vna.write(":CALC1:PAR:COUN 1")

        #number of s params will be a function of n^2
        #input to the s_param_selection_VNA_n_channels is how many channels your vna has, i wrote it that way so that someone can use it for other VNA plugins aswell if they want to have a quick choosing system on tkinter

        selected_params = VNA_List_Sparams.s_parameter_selection_VNA_n_channels(4)
        print(selected_params)
        self.vna.write(f":CALC1:PAR:COUN {len(selected_params)}")

        for i in range(1,len(selected_params)+1):
            self.vna.write(f"CALC1:PAR{i}:DEF {selected_params[i-1]}")
            print(f"CALC1:PAR{i}:DEF {selected_params[i-1]}")
            self.vna.write(f":CALC1:PAR{i}:FORM: REIM")
            print(f":CALC1:PAR{i}:FORM: REIM")  

        # Set what format you are interested in, check page 235 of programming manual for more info on what types are available if needed 
        # Maybe add button for user selection ? 
        # self.vna.write(":CALC1:PAR1:FORM: REIM")

        # Set 501 points
        self.vna.write(":SENS1:SWE:POIN 501")
        
        # Set instrument on Hold
        self.vna.write(":SENS1:HOLD:FUNC HOLD")
        
        # Check if instrument is correctly connected 
        opc_done = self.vna.query("*OPC?")

        if not (opc_done == "1"):
            print(f"Error, Opc returned unexpected value while waiting for a single sweep to finish (expected '1', received {opc_done}); ending code execution.")
            self.vna.close()


        print("Frequency list")
        frequency_data_query = self.vna.query(":SENS1:FREQ:DATA?")
        print(frequency_data_query)

        # Reading S parameter data
        # Important to note, if you want more than one s parameter data, you need to set traces to more than one and define them with their respective parameters
        # for example: 3. Define 4 traces - S11, S21, S12 & S22
        #             shockline_instrument.write(":CALC1:PAR:COUN 4") , defines the traces 
        #             shockline_instrument.write(":CALC1:PAR1:DEF S11") , defines which param# corresponds to a specific s# param
        #             shockline_instrument.write(":CALC1:PAR2:DEF S21")
        #             shockline_instrument.write(":CALC1:PAR3:DEF S12")
        #             shockline_instrument.write(":CALC1:PAR4:DEF S22")
        #
        
        #2d array
        s_param_interest_data_query=[]

        for j in range(1,len(selected_params)+1):

            query_list = self.vna.query(f":CALC1:PAR{j}:DATA:SDAT?")

            s_param_interest_data_query.append(query_list)
            
            print(f"\n Printing {selected_params[j-1]} data")
            print(s_param_interest_data_query[j-1])

        


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
        
