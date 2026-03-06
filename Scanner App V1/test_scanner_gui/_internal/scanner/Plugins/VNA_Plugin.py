from scanner.probe_controller import ProbePlugin
from scanner.plugin_setting import PluginSettingString, PluginSettingInteger, PluginSettingFloat
from scanner.MS461xxVISA_Implementation import InstrumentConnection
import numpy as np
import skrf as rf
import csv 
import os 
import matplotlib.pyplot as plt
import re
from datetime import datetime
class VNAProbePlugin(ProbePlugin):
    def __init__(self):
        super().__init__()
        self.vna = None

        # Connection settings
        self.address = PluginSettingString("Resource Address", "TCPIP0::169.254.250.89::inst0::INSTR")
        self.timeout = PluginSettingInteger("Timeout (ms)", 20000)

        # Frequency mode and settings
        self.freq_mode = PluginSettingString(
            "Frequency Mode", "Center/Span",
            select_options=["Start/Stop", "Center/Span"], restrict_selections=True
        )
        self.plotType = PluginSettingString(
        "Plot Type", "Log Mag",
        select_options=[
        "Log Mag","Lin Mag","Phase","Real","Imag",
        "VSWR","Impedance","Smith","Polar","Log Polar"
        ],
        restrict_selections=True
        )
        #self.add_setting_post_connect(self.plotButton)
        self.add_setting_post_connect(self.plotType)

        self.freq_start = PluginSettingFloat("Start Freq (Hz)", 1e9)
        self.freq_stop = PluginSettingFloat("Stop Freq (Hz)", 4e9)
        self.freq_center = PluginSettingFloat("Center Freq (Hz)", 2.5e9)
        self.freq_span = PluginSettingFloat("Span (Hz)", 3e9)
        self.if_bandwidth = PluginSettingFloat("IF Bandwidth (Hz)", 1e5)
        #self.plotButton = PluginSettingButton("Plot",callback=self.plot)
        # Register settings
        self.add_setting_pre_connect(self.address)
        self.add_setting_pre_connect(self.timeout)
        self.add_setting_pre_connect(self.freq_mode)
        self.add_setting_pre_connect(self.freq_start)
        self.add_setting_pre_connect(self.freq_stop)
        self.add_setting_pre_connect(self.freq_center)
        self.add_setting_pre_connect(self.freq_span)
        self.add_setting_pre_connect(self.if_bandwidth)
       # self.add_setting_post_connect(self.plotButton)
    def connect(self):
        self.vna = InstrumentConnection(self.address.value, self.timeout.value).connect()

        # Apply frequency mode
        if self.freq_mode.value == "Start/Stop":
            self.vna.write(f":SENS1:FREQ:STAR {self.freq_start.value}")
            self.vna.write(f":SENS1:FREQ:STOP {self.freq_stop.value}")
        else:
            self.vna.write(f":SENS1:FREQ:CENT {self.freq_center.value}")
            self.vna.write(f":SENS1:FREQ:SPAN {self.freq_span.value}")

        # Apply IF Bandwidth
        self.vna.write(f":SENS1:BAND {self.if_bandwidth.value}")

        # Default to single trigger hold
        self.vna.write(":SENS1:HOLD:FUNC HOLD")

        # Define parameters and format
        self.vna.write(":CALC1:PAR:COUN 1")
        self.vna.write(":CALC1:PAR1:DEF S11")
        self.vna.write(":CALC1:PAR1:FORM MLOG")

    def disconnect(self):
        if self.vna:
            self.vna.close()

    def get_xaxis_coords(self):
        # 1) ask for the ASCII frequency list (block format)
        raw = self.vna.query(":SENS1:FREQ:DATA?")

        # 2) strip SCPI “#<n><len>” prefix if present
        if raw.startswith("#"):
            hdr_digits = int(raw[1])           # e.g. '9'
            raw = raw[2 + hdr_digits:]         # skip "#", the '9', plus 9 header chars

        # 3) split on whitespace or commas, convert to float
        parts = re.split(r"[,\s]+", raw.strip())
        return tuple(map(float, parts))
    

    def get_xaxis_units(self):
        return "Hz"

    def get_yaxis_units(self):
        return ("dB",)

    def get_channel_names(self):
        return ("S11",)

    def scan_begin(self):
        self.vna.write(":TRIG:SING")
        self.vna.query("*OPC?")
     
    def scan_trigger_and_wait(self, scan_index, scan_location):
        self.vna.write(":TRIG:SING")
        self.vna.query("*OPC?")
        

    def _strip_block(self, raw):
        if raw.startswith("#"):
            n = int(raw[1]); raw = raw[2+n:]
        return re.split(r"[,\s]+", raw.strip())

    def scan_read_measurement(self, scan_index, scan_location):
        results = {}
        for idx, name in enumerate(self.get_channel_names(), start=1):
            raw = self.vna.query(f":CALC1:PAR{idx}:DATA:SDAT?")
            tokens = self._strip_block(raw)
            vals = list(map(float, tokens))
            results[name] = [complex(vals[i], vals[i+1])
                            for i in range(0, len(vals), 2)]
        return results

    def scan_end(self):
        pass

            
    def plot(self):
        freqs = np.array(self.get_xaxis_coords())
        s11   = np.array(self.scan_read_measurement(0,())["S11"])
        pt    = self.plotType.value
        fig, ax = plt.subplots(subplot_kw={
            "projection": "polar"} if pt in ("Polar","Log Polar") else {})

        # compute x/y
        if pt=="Log Mag":
            x,y = freqs, 20*np.log10(np.abs(s11)); ax.semilogx(x,y)
        elif pt=="Lin Mag":
            ax.semilogx(freqs, np.abs(s11))
        elif pt=="Phase":
            ax.semilogx(freqs, np.angle(s11,deg=True))
        elif pt=="Real":
            ax.semilogx(freqs, s11.real)
        elif pt=="Imag":
            ax.semilogx(freqs, s11.imag)
        elif pt=="VSWR":
            m = np.abs(s11); vswr=(1+m)/(1-m); ax.semilogx(freqs,vswr)
        elif pt=="Impedance":                                       
            z0=50; z=z0*(1+s11)/(1-s11); ax.semilogx(freqs,z.real)  
        elif pt == "Smith":
            # s11 is an (N,) array; reshape to (N,1,1)
            s_mat = s11.reshape(-1, 1, 1)
            # build the one-port network
            nt = rf.Network(f=freqs, s=s_mat, z0=50)
            # plot the Smith chart
            nt.plot_s_smith()
            plt.show()
            return
        elif pt in ("Polar","Log Polar"):
            θ = np.angle(s11)
            r = np.abs(s11)
            ax.plot(θ,r)
            if pt=="Log Polar": ax.set_rscale("log")

        else:
            raise RuntimeError("Unknown plot type")

        ax.set_xlabel("Frequency (Hz)")
        ax.set_ylabel(pt)
        ax.grid(True,which="both")
        plt.tight_layout()
        plt.show()
        self.save_data_csv()
   
    def save_data_csv(self, filename=None):
        settings = {
            "Resource Address":     self.address.value,
            "Timeout (ms)":         self.timeout.value,
            "Frequency Mode":       self.freq_mode.value,
            "Start Freq (Hz)":      self.freq_start.value,
            "Stop Freq (Hz)":       self.freq_stop.value,
            "Center Freq (Hz)":     self.freq_center.value,
            "Span (Hz)":            self.freq_span.value,
            "IF Bandwidth (Hz)":    self.if_bandwidth.value,
            "Plot Type":            self.plotType.value,
        }

        if filename is None:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"s11_data_{ts}.csv"
        freqs = np.array(self.get_xaxis_coords())
        s11   = np.array(self.scan_read_measurement(0,())["S11"])
        pt    = self.plotType.value
        z0    = 50

        # prepare columns based on plot type
        if pt == "Log Mag":
            y = 20*np.log10(np.abs(s11))
            header, cols = ["Frequency (Hz)","LogMag (dB)"], [freqs,y]

        elif pt == "Lin Mag":
            y = np.abs(s11)
            header, cols = ["Frequency (Hz)","LinMag"], [freqs,y]

        elif pt == "Phase":
            y = np.angle(s11,deg=True)
            header, cols = ["Frequency (Hz)","Phase (deg)"], [freqs,y]

        elif pt == "Real":
            y = s11.real
            header, cols = ["Frequency (Hz)","Real"], [freqs,y]

        elif pt == "Imag":
            y = s11.imag
            header, cols = ["Frequency (Hz)","Imag"], [freqs,y]

        elif pt == "VSWR":
            m = np.abs(s11)
            y = (1+m)/(1-m)
            header, cols = ["Frequency (Hz)","VSWR"], [freqs,y]

        elif pt == "Impedance":
            z = z0*(1+s11)/(1-s11)
            header, cols = ["Frequency (Hz)","Z_real","Z_imag"], [freqs,z.real,z.imag]

        elif pt in ("Polar","Log Polar"):
            r = np.abs(s11)
            θ = np.angle(s11,deg=True)
            header, cols = ["Angle (deg)","Radius"], [θ,r]

        elif pt == "Smith":
            
            header, cols = ["Frequency (Hz)","S11_real","S11_imag"], [freqs,s11.real,s11.imag]



        else:
            raise RuntimeError(f"Unknown plot type: {pt}")

        # write CSV
        with open(filename, "w", newline="") as f:
            w = csv.writer(f)
            # metadata block
            w.writerow(["Setting","Value"])
            for k, v in settings.items():
                w.writerow([k, v])
            w.writerow([]) 
            w.writerow(header)
            for row in zip(*cols):
                w.writerow(row)

        print(f"Saved {len(freqs)} rows to {filename}")