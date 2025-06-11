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
import scipy.fft as fft
class plotter_system(QWidget):

    def __init__(self, connected_vna_plugin: VNA_Plugin = None):
        super().__init__()
        self.x_axis=[]
        self.y_axis =[]
        self.figure = Figure(figsize=(4, 4), dpi=100)
        self.static_ax = self.figure.add_subplot(111)
        self.canvas = FigureCanvas(self.figure)
        self.setup_layout()
        self.traces = {}
        self.tracePopup ={}
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
            if plot_style != None:
                
                condition = plot_style
            else:
                condition = "Log Mag"
                
            #self.plot_initial_data(condition,freqs, s_param_names,all_s_params_data)
            # if condition == "Log Mag":
            #     processed_data = {}
            #     for name in s_param_names:
            #         s_data = np.array(all_s_params_data[name])
            #         processed_data[name] = 20 * np.log10(np.abs(s_data)) 
            # elif condition == "Phase":
            #     processed_data = {}
            #     for name in s_param_names:
            #         s_data = np.array(all_s_params_data[name])
            #         processed_data[name] = np.angle(s_data,deg=True)
            # elif condition == "Real":
            #     processed_data = {}
            #     for name in s_param_names:
            #         s_data = np.array(all_s_params_data[name])
            #         processed_data[name] = s_data.real
            # elif condition == "Imag":
            #     processed_data = {}
            #     for name in s_param_names:
            #         s_data = np.array(all_s_params_data[name])
            #         processed_data[name] = s_data.imag
            # elif condition == "VSWR":
            #     processed_data = {}
            #     for name in s_param_names:

            #         s_data = np.array(all_s_params_data[name])
            #         m = np.abs(s_data)
            #         processed_data[name] = (1+m)/(1-m)
            # elif condition == "Smith":
            #     processed_data = {}
            #     for name in s_param_names:
            #         s_data = np.array(all_s_params_data[name])
            #         processed_data[name] = np.angle(s_data,deg=True)
            #         s_mat = s_data.reshape(-1, 1, 1)
            #         # build the one-port network
            #         nt = rf.Network(f=freqs, s=s_mat, z0=50)
            #         # plot the Smith chart
            #         nt.plot_s_smith()            
            
            
            
            return freqs, s_param_names,all_s_params_data

        except Exception as e:
            print(f"Error getting and processing data: {e}")
            return None, None, None

    def plot_initial_data(self, plot_style, freqs, s_param_names, all_s_params_data ):
       
        # freqs, processed_data, s_param_names,all_s_params_data = self._get_and_process_data()

        condition = plot_style
        
        
        
        if condition == "Log Mag":
            processed_data = {}
            for name in s_param_names:
                s_data = np.array(all_s_params_data[name])
                processed_data[name] = 20 * np.log10(np.abs(s_data)) 
                units = "dB"
        elif condition == "Phase":
            processed_data = {}
            for name in s_param_names:
                s_data = np.array(all_s_params_data[name])
                processed_data[name] = np.angle(s_data,deg=True)
                units = "Deg"
        elif condition == "Real":
            processed_data = {}
            for name in s_param_names:
                s_data = np.array(all_s_params_data[name])
                processed_data[name] = s_data.real
                units = ""
        elif condition == "Imag":
            processed_data = {}
            for name in s_param_names:
                s_data = np.array(all_s_params_data[name])
                processed_data[name] = s_data.imag
                units = ""
        elif condition == "VSWR":
            processed_data = {}
            for name in s_param_names:

                s_data = np.array(all_s_params_data[name])
                m = np.abs(s_data)
                processed_data[name] = (1+m)/(1-m)
                units = ""
        elif condition == "Smith":
            #Work in progress
            processed_data = {}
            for name in s_param_names:
                s_data = np.array(all_s_params_data[name])
                processed_data[name] = np.angle(s_data,deg=True)
                s_mat = s_data.reshape(-1, 1, 1)
                # build the one-port network
                nt = rf.Network(f=freqs, s=s_mat, z0=50)
                # plot the Smith chart
                nt.plot_s_smith()
                units = ""
        else:
            print("Error Plot Style Invalid")            
        
        if len(all_s_params_data) != 0:
            pass
        
        if freqs is None: # Error occurred in data processing
            return

        self.static_ax.clear()
        self.traces.clear() # Clear existing trace references for embedded plot

        for name in s_param_names:
            y = processed_data[name]
            # Store the Line2D object returned by plot/semilogx
            
            line, = self.static_ax.semilogx(freqs, y, label=name) 
            self.traces[name] = line # Store the line object for visibility control

        self.static_ax.set_xlabel("Frequency (Hz)")
        self.static_ax.set_ylabel(f"{plot_style} {units}")
        self.static_ax.set_title("S-Parameters Scan (Embedded)") 
        self.static_ax.grid(True, which="both")
        self.static_ax.legend()
        self.static_ax.autoscale() # Ensure axes are scaled correctly

        self.canvas.draw()
        print(f"DEBUG: Plotted S-parameters (Embedded): {', '.join(s_param_names)}")
        #self.plot_in_popup(plot_style,freqs, s_param_names, processed_data)
        return processed_data

    def plot_in_popup(self,plot_style, freqs, s_param_names, processed_data):
        
        
        if freqs is None: 
            return
        
        self.popup_figure = plt.figure(figsize=(8, 6), dpi=100) 
        self.popup_ax = self.popup_figure.add_subplot(111)
        
        #self.tracePopup = {}
        for name in s_param_names:
            y = processed_data[name]
            lineTrace,= self.popup_ax.semilogx(freqs, y, label=name)
            self.tracePopup[name] = lineTrace
                
                
        self.popup_ax.set_xlabel("Frequency (Hz)")
        self.popup_ax.set_ylabel(f"{plot_style}")
        self.popup_ax.set_title("S-Parameters Scan (Pop-up)") 
        self.popup_ax.grid(True, which="both")
        self.popup_ax.legend()

        plt.show() 
        print(f"DEBUG: Pop-up plot displayed for S-parameters: {', '.join(s_param_names)}")

    def invFFT_plot(self, s_param_names, processed_data):
        t = np.arange(501)
        for name in s_param_names:
            
            s = fft.ifft(processed_data[name])
            plt.plot(t, s.real, 'b-', t, s.imag, 'r--')
            plt.legend(('real', 'imaginary'))
            plt.show()
        return s
    
    def FFT_plot(self, s_param_names, time_domain_data):
        t = np.arange(501)
        
        for name in s_param_names:    
            s = fft.ifft(time_domain_data[name])
            plt.plot(t, s.real, 'b-', t, s.imag, 'r--')
            plt.legend(('real', 'imaginary'))
            plt.show()   
        return s 
    
    def set_trace_visibility(self, s_param_name: str):
       
        for name in s_param_name:
            
            if name in self.traces:
                current_visibility = self.traces[name].get_visible()
                self.traces[name].set_visible(not current_visibility)
                self.canvas.draw()
            else:
                print(f"WARNING: Trace '{name}' not found for embedded plot visibility toggle.")

            
            if name in self.tracePopup and self.popup_figure is not None:
                current_visibility_popup = self.tracePopup[name].get_visible()
                self.tracePopup[name].set_visible(not current_visibility_popup)
                
                self.popup_figure.canvas.draw_idle() 
            else:
                if self.popup_figure is not None:
                    print(f"WARNING: Trace '{name}' not found for pop-up plot visibility toggle.")
                
                    
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