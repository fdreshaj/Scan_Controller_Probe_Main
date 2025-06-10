# gui/plotter.py
import numpy as np
import csv
from datetime import datetime
from PySide6.QtWidgets import QWidget, QVBoxLayout, QApplication
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from scanner.Plugins.Simplified_VNA_Plugin import VNA_Plugin # Ensure this import is correct
import skrf as rf
class plotter_system(QWidget):

    def __init__(self, connected_vna_plugin: VNA_Plugin = None):
        super().__init__()
        self.x_axis=[]
        self.y_axis =[]
        self.figure = Figure(figsize=(4, 4), dpi=100)
        self.static_ax = self.figure.add_subplot(111)
        self.canvas = FigureCanvas(self.figure)
        self.setup_layout()
        self.traces = {} # Dictionary to store plot line objects, keyed by S-parameter name

        if connected_vna_plugin is not None:
            self.plugin = connected_vna_plugin
        else:
            self.plugin = None
            print("WARNING (plotter_system init): No VNA_Plugin instance provided. Plotting/saving functionality may be limited.")

    def setup_layout(self):
        layout = QVBoxLayout(self)
        layout.addWidget(self.canvas)
        self.setLayout(layout)

    def _get_and_process_data(self,plot_style):
        
        if self.plugin is None or self.plugin.vna is None:
            print("Cannot get data: VNA plugin not connected or not provided.")
            return None, None, None

        try:
            freqs = np.array(self.plugin.get_xaxis_coords())
            all_s_params_data = self.plugin.scan_read_measurement(0, ())
            s_param_names = self.plugin.get_channel_names()

            if not s_param_names:
                print("No S-parameters selected for data processing.")
                return None, None, None
            
            condition = plot_style
            
            if condition == "Log Mag":
                processed_data = {}
                for name in s_param_names:
                    s_data = np.array(all_s_params_data[name])
                    processed_data[name] = 20 * np.log10(np.abs(s_data)) 
            elif condition == "Phase":
                processed_data = {}
                for name in s_param_names:
                    s_data = np.array(all_s_params_data[name])
                    processed_data[name] = np.angle(s_data,deg=True)
            elif condition == "Real":
                processed_data = {}
                for name in s_param_names:
                    s_data = np.array(all_s_params_data[name])
                    processed_data[name] = s_data.real
            elif condition == "Imag":
                processed_data = {}
                for name in s_param_names:
                    s_data = np.array(all_s_params_data[name])
                    processed_data[name] = s_data.imag
            elif condition == "VSWR":
                processed_data = {}
                for name in s_param_names:

                    s_data = np.array(all_s_params_data[name])
                    m = np.abs(s_data)
                    processed_data[name] = (1+m)/(1-m)
            elif condition == "Smith":
                processed_data = {}
                for name in s_param_names:
                    s_data = np.array(all_s_params_data[name])
                    processed_data[name] = np.angle(s_data,deg=True)
                    s_mat = s_data.reshape(-1, 1, 1)
                    # build the one-port network
                    nt = rf.Network(f=freqs, s=s_mat, z0=50)
                    # plot the Smith chart
                    nt.plot_s_smith()            
            
            
            
            return freqs, processed_data, s_param_names

        except Exception as e:
            print(f"Error getting and processing data: {e}")
            return None, None, None

    def plot_initial_data(self):
       
        freqs, processed_data, s_param_names = self._get_and_process_data(plot_style="Phase")

        if freqs is None: # Error occurred in data processing
            return

        self.static_ax.clear()
        self.traces.clear() # Clear existing trace references for embedded plot

        for name in s_param_names:
            y = processed_data[name]
            # Store the Line2D object returned by plot/semilogx
            line, = self.static_ax.semilogx(freqs, y, label=name) # Note the comma for unpacking
            self.traces[name] = line # Store the line object for visibility control

        self.static_ax.set_xlabel("Frequency (Hz)")
        self.static_ax.set_ylabel("LogMag (dB)")
        self.static_ax.set_title("S-Parameters Scan (Embedded)") # Differentiate title
        self.static_ax.grid(True, which="both")
        self.static_ax.legend()
        self.static_ax.autoscale() # Ensure axes are scaled correctly

        self.canvas.draw()
        print(f"DEBUG: Plotted S-parameters (Embedded): {', '.join(s_param_names)}")
        self.plot_in_popup()

    def plot_in_popup(self):
        
        freqs, processed_data, s_param_names = self._get_and_process_data(plot_style="Phase")

        if freqs is None: 
            return

        
        popup_figure = plt.figure(figsize=(8, 6), dpi=100) 
        popup_ax = popup_figure.add_subplot(111)

        for name in s_param_names:
            y = processed_data[name]
            popup_ax.semilogx(freqs, y, label=name)

        popup_ax.set_xlabel("Frequency (Hz)")
        popup_ax.set_ylabel("LogMag (dB)")
        popup_ax.set_title("S-Parameters Scan (Pop-up)") 
        popup_ax.grid(True, which="both")
        popup_ax.legend()

        plt.show() 
        print(f"DEBUG: Pop-up plot displayed for S-parameters: {', '.join(s_param_names)}")


    def set_trace_visibility(self, s_param_name: str, visible: bool):
        if s_param_name in self.traces:
            self.traces[s_param_name].set_visible(visible)
            self.canvas.draw() 
        else:
            print(f"WARNING: Trace '{s_param_name}' not found for visibility toggle.") 
                
    def save(self, filename=None):
        if self.plugin is None or self.plugin.vna is None:
            print("Cannot save: VNA plugin not connected or not provided.")
            return

        if filename is None:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"s_parameters_data_{ts}.csv"

        try:
            self.freqs = np.array(self.plugin.get_xaxis_coords())
            all_s_params_data = self.plugin.scan_read_measurement(0, ())

            s_param_names = self.plugin.get_channel_names()
            if not s_param_names:
                print("No S-parameters selected to save.")
                return

            header = ["Frequency (Hz)"]
            cols_to_write = [self.freqs]

            for name in s_param_names:
                s_data = np.array(all_s_params_data[name])
                header.extend([f"{name}_Real", f"{name}_Imag"])
                cols_to_write.extend([s_data.real, s_data.imag])

            with open(filename, "w", newline="") as f:
                w = csv.writer(f)
                w.writerow([])
                w.writerow(header)
                for row in zip(*cols_to_write):
                    w.writerow(row)

            print(f"Saved {len(self.freqs)} rows with {len(s_param_names)} S-parameters to {filename}")

        except Exception as e:
            print(f"Error during save operation: {e}")