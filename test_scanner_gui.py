import globals
from typing import Iterable

from PySide6.QtCore import QTimer, Slot
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget
import tkinter as tk
from tkinter import simpledialog
from tkinter import filedialog as fd
from tkinter import messagebox
from gui.scanner_qt import ScannerQt
from gui.ui_scanner_plotter_version import Ui_MainWindow
from gui.qt_util import QPluginSetting
from scanner import scanner
from scanner.plugin_setting import PluginSetting
#from scanner.VNA_Plugin import VNAProbePlugin
from scanner.probe_controller import ProbePlugin
from scanner.plugin_switcher import PluginSwitcher
import pkgutil
import importlib
import scanner.Plugins as plugin_pkg
from scanner.probe_controller import ProbeController
import gui.select_plot_style as select_plot_style
import gui.select_plot_hide as select_plot_hide
# import matplotlib
# matplotlib.use('QtAgg')
# from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
# from matplotlib.figure import Figure
# from  gui.plotter import plotter_system
import matplotlib
matplotlib.use('QtAgg') # <--- Ensure this line is exactly 'QtAgg' and is at the top
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas # <--- CHANGE THIS LINE
from matplotlib.figure import Figure
from  gui.plotter import plotter_system
# for finder, module_name, ispkg in pkgutil.iter_modules(plugin_pkg.__path__):
#     importlib.import_module(f"scanner.Plugins.{module_name}")

########      FIX NOTES 
# Noticed in testing that position multiplier might need to be lowered a small amount it was overshooting a bit 
# Velocity on Query Long
#
######## 

class MainWindow(QMainWindow):
    scanner: ScannerQt
    ui: Ui_MainWindow
    pluginChosen_probe = False
    
    pluginChosen_motion = False
    
    
    
    def __init__(self) -> None:
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.scanner = ScannerQt()
        self.plotter = plotter_system()
        self.back_btn_check = False
        try:
            self.setup_plotting_canvas()
            self.setup_connections()
            self.show()
        except:
            self.scanner.close()
            raise
    
    def setup_connections(self) -> None:
        self.ui.xy_move_amount.valueChanged.connect(self.scanner.set_xy_move)
        self.ui.z_move_amount.valueChanged.connect(self.scanner.set_z_move)
        self.scanner.set_xy_move(self.ui.xy_move_amount.value())
        self.scanner.set_z_move(self.ui.z_move_amount.value())

        self.ui.x_plus_button.clicked.connect(self.scanner.clicked_move_x_plus)
        self.ui.x_minus_button.clicked.connect(self.scanner.clicked_move_x_minus)
        self.ui.y_plus_button.clicked.connect(self.scanner.clicked_move_y_plus)
        self.ui.y_minus_button.clicked.connect(self.scanner.clicked_move_y_minus)
        self.ui.z_plus_button.clicked.connect(self.scanner.clicked_move_z_plus)
        self.ui.z_minus_button.clicked.connect(self.scanner.clicked_move_z_minus)
        
        self.ui.configure_motion_button.clicked.connect(self.configure_pressed)
        self.ui.configure_probe_button.clicked.connect(self.configure_pressed)
        self.ui.configure_pattern_button.clicked.connect(self.configure_pressed)
        self.ui.configure_file_button.clicked.connect(self.configure_pressed)

        self.ui.configure_motion_button.clicked.connect(self.configure_motion)
        self.ui.configure_probe_button.clicked.connect(self.configure_probe)
        self.ui.configure_pattern_button.clicked.connect(self.configure_pattern)
        self.ui.configure_file_button.clicked.connect(self.configure_file)

        self.scanner.current_position_x.connect(self.ui.x_axis_slider.setSliderPosition)
        self.scanner.current_position_y.connect(self.ui.y_axis_slider.setSliderPosition)
        self.scanner.current_position_z.connect(self.ui.z_axis_slider.setSliderPosition)

        self.display_timer = QTimer()
        self.display_timer.setInterval(1000 // 60)
       # self.display_timer.timeout.connect(self.scanner.update_motion) TODO:
        self.display_timer.start()
    
    @Slot(bool)
    def configure_pressed(self, was_selected: bool) -> None:
        self.sender().blockSignals(True)
        self.ui.configure_motion_button.setChecked(False)
        self.ui.configure_probe_button.setChecked(False)
        self.ui.configure_pattern_button.setChecked(False)
        self.ui.configure_file_button.setChecked(False)
        self.sender().setChecked(was_selected)
        self.sender().blockSignals(False)
        
    @Slot(bool)
    def configure_motion(self, was_selected: bool) -> None:
        
        if was_selected:
            controller = self.scanner.scanner.motion_controller
            self.set_configuration_settings_motion(controller._driver, controller.is_connected(), self.connect_motion, self.disconnect_motion)
            self.back_btn_check == False
        else:
            for i in reversed(range(self.ui.config_layout.rowCount())):
                self.ui.config_layout.removeRow(i)
            self.back_btn_check == False
    @Slot()
    def connect_motion(self):
        self.scanner.scanner.motion_controller.connect()
        self.configure_motion(True)

    @Slot()
    def disconnect_motion(self):
        self.scanner.scanner.motion_controller.disconnect()
        self.configure_motion(True)

    @Slot(bool)
    def configure_probe(self, was_selected: bool) -> None:
        if was_selected:
            controller = self.scanner.scanner.probe_controller
            self.set_configuration_settings_probe(controller._probe, controller.is_connected(), self.connect_probe, self.disconnect_probe)
        else:
            for i in reversed(range(self.ui.config_layout.rowCount())):
                self.ui.config_layout.removeRow(i)


        self.back_btn_check = False
        # back_btn = QPushButton("Back")
        # back_btn.clicked.connect(self.back_function)
        # self.ui.config_layout.addRow(back_btn)    
            
    @Slot()
    def connect_probe(self):
        self.scanner.scanner.probe_controller.connect()
        self.configure_probe(True)

    @Slot()
    def disconnect_probe(self):
        self.scanner.scanner.probe_controller.disconnect()
        self.configure_probe(True)
        self.connect = False

    @Slot(bool)
    def configure_pattern(self, was_selected: bool) -> None:
        if was_selected:
            for i in reversed(range(self.ui.config_layout.rowCount())):
                self.ui.config_layout.removeRow(i)
        else:
            for i in reversed(range(self.ui.config_layout.rowCount())):
                self.ui.config_layout.removeRow(i)

    @Slot(bool)
    def configure_file(self, was_selected: bool) -> None:
        if was_selected:
            for i in reversed(range(self.ui.config_layout.rowCount())):
                self.ui.config_layout.removeRow(i)
        else:
            for i in reversed(range(self.ui.config_layout.rowCount())):
                self.ui.config_layout.removeRow(i)

    def plot_btn(self):
        for i in reversed(range(self.ui.plot_config_wid.rowCount())):
            self.ui.plot_config_wid.removeRow(i)
            
        self.freqs, self.s_param_names,self.all_s_params_data = self.plotter._get_and_process_data("Log Mag")
        self.plot_style = "Log Mag"
        self.processed_data = self.plotter.plot_initial_data(self.plot_style,self.freqs, self.s_param_names,self.all_s_params_data)
        self.plot_settings()


    def plot_settings(self):
        
        display_Pop_up = QPushButton("Display Pop Up")
        display_Pop_up.clicked.connect(self.display_Pop_up)
        self.ui.plot_config_wid.addRow(display_Pop_up)  
        
        plot_style = QPushButton("Select Plot Style (Mag dB default)")
        plot_style.clicked.connect(self.plot_style_btn)
        self.ui.plot_config_wid.addRow(plot_style)       
        
        sel_hide_channel = QPushButton("Select/Hide S-Parameters")
        sel_hide_channel.clicked.connect(self.sel_hide_channel)
        self.ui.plot_config_wid.addRow(sel_hide_channel)
        
        dsp_settings = QPushButton("DSP Settings")
        dsp_settings.clicked.connect(self.dsp_settings)
        self.ui.plot_config_wid.addRow(dsp_settings)      
        
        plot_plugins = QPushButton("Import Plot Plugins")
        plot_plugins.clicked.connect(self.plot_plugins)
        self.ui.plot_config_wid.addRow(plot_plugins)  
        
        
        
                  
    def display_Pop_up(self):
    
        self.plotter.plot_in_popup(self.plot_style,self.freqs, self.s_param_names,self.processed_data)
        
        
    def plot_style_btn(self):
        #Pop up Tkinter asking what style of plot you want
        self.plot_style = select_plot_style.select_plot_style()
        self.processed_data=self.plotter.plot_initial_data(self.plot_style,self.freqs, self.s_param_names,self.all_s_params_data)
    
    def sel_hide_channel(self):
        
        selected_hidden = select_plot_hide.select_plot_hide(4)
        self.plotter.set_trace_visibility(selected_hidden)
    
    def dsp_settings(self):
        self.invfft = self.plotter.invFFT_plot(self.s_param_names,self.processed_data,)
        #self.fft = self.plotter.FFT_plot(self.s_param_names,self.invfft) 
    
    def plot_plugins(self):
        pass
    
    def save_btn(self):
        self.plotter.save()
        
    

    def back_function(self):

        response = messagebox.askyesno(
            "Reset Instrument Connection",
            "Are you sure you want to reset the instrument connection?"
        )

        if response:  
            from scanner.scanner import Scanner
            self.scanner.scanner = Scanner(probe_controller="Back")

            self.configure_probe(True)
            self.connected = False
            self.pluginChosen_probe = False
        else: 
            pass 



    # TODO:
    def back_function_motion(self):

        pass
        
        
    def set_configuration_settings_motion(self, controller, connected, connect_function, disconnect_function):
        
        for i in reversed(range(self.ui.config_layout.rowCount())):
            self.ui.config_layout.removeRow(i)
        #globals.value_flag = controller.settings_pre_connect[0].value
        
        if connected:
            #print debugging
            if self.pluginChosen_motion == False:
                print(PluginSwitcher.plugin_name)
                
                print(PluginSwitcher.plugin_name)
                
                print(PluginSwitcher.plugin_name)
                print(controller.settings_pre_connect[0].value)


                for i in reversed(range(self.ui.config_layout.rowCount())):
                    self.ui.config_layout.removeRow(i)
            
                old_probe = self.scanner.scanner.probe_controller
                #newProbeInst = PluginSwitcher.plugin_name
            
                # re‐instantiate Scanner
                from scanner.scanner import Scanner
                self.scanner.scanner = Scanner(probe_controller=old_probe)

                self.configure_motion(True)
                connected = False
                self.pluginChosen_motion = True
                # back_btn = QPushButton("Back")
                # back_btn.clicked.connect(self.back_function)
                # self.ui.config_layout.addRow(back_btn)

            elif self.pluginChosen_motion == True:
                for setting in controller.settings_pre_connect:
                    plug = QPluginSetting(setting)
                    plug.setDisabled(True)
                    self.ui.config_layout.addRow(setting.display_label, plug)
                connect_button = QPushButton("Disconnect")
                connect_button.clicked.connect(disconnect_function)
                self.ui.config_layout.addRow(connect_button)
                for setting in controller.settings_post_connect:
                    self.ui.config_layout.addRow(setting.display_label, QPluginSetting(setting))

                # self.plotter = plotter_system(connected_vna_plugin=self.scanner.scanner.probe_controller._probe)
                # self.setup_plotting_canvas()
                # plot_btn = QPushButton("Plot")
                # plot_btn.clicked.connect(self.plot_btn)   
                # self.ui.config_layout.addRow(plot_btn)

                # save_btn = QPushButton("Save Data")
                # save_btn.clicked.connect(self.save_btn)   
                # self.ui.config_layout.addRow(save_btn)

                # back_btn = QPushButton("Back")
                # back_btn.clicked.connect(self.back_function)
                # self.ui.config_layout.addRow(back_btn)

        else:
                print(controller)
                print(controller)
                for setting in controller.settings_pre_connect:
                    self.ui.config_layout.addRow(setting.display_label, QPluginSetting(setting))
                connect_button = QPushButton("Connect")
                connect_button.clicked.connect(connect_function)
                self.ui.config_layout.addRow(connect_button)
                # back_btn = QPushButton("Back")
                # back_btn.clicked.connect(self.back_function)
                # self.ui.config_layout.addRow(back_btn)
                for setting in controller.settings_post_connect:
                    plug = QPluginSetting(setting)
                    plug.setDisabled(True)
                    self.ui.config_layout.addRow(setting.display_label, plug)    
        
    def set_configuration_settings_probe(self, controller, connected, connect_function, disconnect_function):
        
        for i in reversed(range(self.ui.config_layout.rowCount())):
            self.ui.config_layout.removeRow(i)
        
    
        if connected:
            #print debugging
            if self.pluginChosen_probe == False:
                print(PluginSwitcher.plugin_name)
                
                print(PluginSwitcher.plugin_name)
                
                print(PluginSwitcher.plugin_name)
                print(controller.settings_pre_connect[0].value)


                for i in reversed(range(self.ui.config_layout.rowCount())):
                    self.ui.config_layout.removeRow(i)
                    
                #self.back_btn_check = False
                old_motion = self.scanner.scanner.motion_controller
                #newProbeInst = PluginSwitcher.plugin_name
            
                # re‐instantiate Scanner
                from scanner.scanner import Scanner
                self.scanner.scanner = Scanner(motion_controller=old_motion)

                self.configure_probe(True)
                connected = False
                self.pluginChosen_probe = True
                
        
            elif self.pluginChosen_probe == True:
                for setting in controller.settings_pre_connect:
                    plug = QPluginSetting(setting)
                    plug.setDisabled(True)
                    self.ui.config_layout.addRow(setting.display_label, plug)
                connect_button = QPushButton("Disconnect")
                connect_button.clicked.connect(disconnect_function)
                self.ui.config_layout.addRow(connect_button)
                for setting in controller.settings_post_connect:
                    self.ui.config_layout.addRow(setting.display_label, QPluginSetting(setting))

                self.plotter = plotter_system(connected_vna_plugin=self.scanner.scanner.probe_controller._probe)
                self.setup_plotting_canvas()
                plot_btn = QPushButton("Plot")
                plot_btn.clicked.connect(self.plot_btn)   
                self.ui.config_layout.addRow(plot_btn)

                save_btn = QPushButton("Save Data")
                save_btn.clicked.connect(self.save_btn)   
                self.ui.config_layout.addRow(save_btn)

                if self.back_btn_check == False:
                    self.back_btn_check = True
                    back_btn = QPushButton("Back")
                    back_btn.clicked.connect(self.back_function)
                    self.ui.config_layout.addRow(back_btn)

        else:
                print(controller)
                print(controller)
                for setting in controller.settings_pre_connect:
                    self.ui.config_layout.addRow(setting.display_label, QPluginSetting(setting))
                connect_button = QPushButton("Connect")
                connect_button.clicked.connect(connect_function)
                self.ui.config_layout.addRow(connect_button)
                
               
                for setting in controller.settings_post_connect:
                    plug = QPluginSetting(setting)
                    plug.setDisabled(True)
                    self.ui.config_layout.addRow(setting.display_label, plug)

                if self.back_btn_check == False:
                    self.back_btn_check = True
                    back_btn = QPushButton("Back")
                    back_btn.clicked.connect(self.back_function)
                    self.ui.config_layout.addRow(back_btn)
    def setup_plotting_canvas(self) -> None:
        main_layout = self.ui.main_layout 
        # Add the plotter_system widget to the main layout
        main_layout.addWidget(self.plotter, 1, 5)
        
    def closeEvent(self, event: QCloseEvent) -> None:
        self.scanner.close()
        return super().closeEvent(event)

if __name__ == "__main__":
    app = QApplication([])
    window = MainWindow()
    app.exec()