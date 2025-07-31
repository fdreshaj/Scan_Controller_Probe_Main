
## IMPORTS 
#region Imports
from scanner.plugin_setting import PluginSettingString, PluginSettingInteger, PluginSettingFloat
from PySide6.QtCore import QTimer, Slot
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget
import tkinter as tk
from tkinter import simpledialog
from tkinter import filedialog as fd
from tkinter import messagebox
import threading
from gui.scanner_qt import ScannerQt
from gui.ui_scanner_plotter_version import Ui_MainWindow
from gui.qt_util import QPluginSetting
import gui.select_plot_style as select_plot_style
import gui.select_plot_hide as select_plot_hide
import raster_pattern_generator as scan_pattern_gen
import numpy as np
import matplotlib
matplotlib.use('QtAgg') 
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas 
from matplotlib.figure import Figure
from  gui.plotter import plotter_system
from scanner.scan_pattern_1 import ScanPattern
from scanner.scan_pattern_controller import ScanPatternControllerPlugin
from scanner.scan_file_1 import ScanFile
import time     
#endregion

class MainWindow(QMainWindow):
    scanner: ScannerQt
    ui: Ui_MainWindow
    pluginChosen_probe = False
    pluginChosen_motion = False
    
    ## SETUP FUNCTIONS
    #region Setup
    def __init__(self) -> None:
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.scanner = ScannerQt()
        self.plotter = plotter_system()
        self.back_btn_check = False
        self.scan_controller = ScanPattern()
        self.file_controller = ScanFile()
        self.motion_config_counter = 0
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
    #endregion
    
    
    
    ## CONFIG M/P/SP/SF 
    #region config functions
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
            
        else:
            for i in reversed(range(self.ui.config_layout.rowCount())):
                self.ui.config_layout.removeRow(i)
    
    @Slot(bool)
    def configure_probe(self, was_selected: bool) -> None:
        if was_selected:
            controller = self.scanner.scanner.probe_controller
            self.set_configuration_settings_probe(controller._probe, controller.is_connected(), self.connect_probe, self.disconnect_probe)
        else:
            for i in reversed(range(self.ui.config_layout.rowCount())):
                self.ui.config_layout.removeRow(i)


        self.back_btn_check = False
    
    @Slot(bool)
    def configure_pattern(self, was_selected: bool) -> None:
        if was_selected:               
            
            connected = self.scan_controller.is_connected()
            self.set_configuration_setting_pattern(connected)
        else:
            for i in reversed(range(self.ui.config_layout.rowCount())):
                self.ui.config_layout.removeRow(i)

        
        

    @Slot(bool)
    def configure_file(self, was_selected: bool) -> None:
        if was_selected:
            connected = self.file_controller.is_connected()
            self.set_configuration_setting_file(connected)
                
        else:
            for i in reversed(range(self.ui.config_layout.rowCount())):
                self.ui.config_layout.removeRow(i)
    
    #endregion
    
    
    
    #####
    #
    #     
    #####
    ## CONFIG SETTINGS M/P/SP/SF
    #region config settings
    def set_configuration_setting_file(self,connected):
        
        self.file_display_label_text =[]
        if connected == True:
            for i in reversed(range(self.ui.config_layout.rowCount())):
                    self.ui.config_layout.removeRow(i)
            for setting in self.file_controller.settings_pre_connect:
                    plug = QPluginSetting(setting)
                    plug.setDisabled(True)
                    self.ui.config_layout.addRow(setting.display_label, plug)
                    self.file_display_label_text.append(f"{setting.display_label}")
                    
            for setting in self.file_controller.settings_post_connect:
                    
                    PluginSettingString.set_value_from_string(self.file_controller.file_directory,f"{self.file_directory}")
                    plug = QPluginSetting(setting)
                    
                    self.ui.config_layout.addRow(setting.display_label, plug)
                
            go_back_file = QPushButton("Back")
            go_back_file.clicked.connect(self.go_back_file)
            self.ui.config_layout.addRow(go_back_file)  
        
        else:   
            for i in reversed(range(self.ui.config_layout.rowCount())):
                    self.ui.config_layout.removeRow(i)
            for setting in self.file_controller.settings_pre_connect:
                        self.ui.config_layout.addRow(setting.display_label, QPluginSetting(setting))
            get_file_dir = QPushButton("Choose File Directory")
            get_file_dir.clicked.connect(self.get_file_dir)
            self.ui.config_layout.addRow(get_file_dir)            
                        
            finish_config = QPushButton("Finish Config")
            finish_config.clicked.connect(self.finish_config)
            self.ui.config_layout.addRow(finish_config)
                    
    def set_configuration_settings_motion(self, controller, connected, connect_function, disconnect_function):
        
        self.motion_connected = connected 
        for i in reversed(range(self.ui.config_layout.rowCount())):
            self.ui.config_layout.removeRow(i)
      
        
        if self.motion_connected:
           
            if self.pluginChosen_motion == False:
               
                for i in reversed(range(self.ui.config_layout.rowCount())):
                    self.ui.config_layout.removeRow(i)
            
                old_probe = self.scanner.scanner.probe_controller
               
                from scanner.scanner import Scanner
                self.scanner.scanner = Scanner(probe_controller=old_probe)
                self.configure_motion(True)
                self.motion_connected = False
                self.pluginChosen_motion = True
                
    

            elif self.pluginChosen_motion == True:
                self.settings_motion_list = []
                for setting in controller.settings_pre_connect:
                    plug = QPluginSetting(setting)
                    plug.setDisabled(True)
                    self.ui.config_layout.addRow(setting.display_label, plug)
                   
                disconnect_button = QPushButton("Disconnect")
                disconnect_button.clicked.connect(disconnect_function)
                self.ui.config_layout.addRow(disconnect_button)
                
                for setting in controller.settings_post_connect:
                    
                    self.ui.config_layout.addRow(setting.display_label, QPluginSetting(setting))
                i = 0
                for setting in controller.settings_pre_connect:
                    self.settings_motion_list.append( PluginSettingFloat.get_value_as_string(controller.settings_pre_connect[i]))
                    i = i+1
                    
               
                # self.pos_mult = PluginSettingFloat.get_value_as_string(controller.settings_pre_connect[2])
                # self.accel = PluginSettingFloat.get_value_as_string(controller.settings_pre_connect[5])
                
                self.scan_testing()
                

        else:
                
                for setting in controller.settings_pre_connect:
                    
                    self.ui.config_layout.addRow(setting.display_label, QPluginSetting(setting))
                   
                
                connect_button = QPushButton("Connect")
                connect_button.clicked.connect(connect_function)
                self.ui.config_layout.addRow(connect_button)
                i = 0
                for setting in controller.settings_post_connect:
                    
                    plug = QPluginSetting(setting)
                    plug.setDisabled(True)
                    self.ui.config_layout.addRow(setting.display_label, plug)
                    
                       
                
                    
        
    def set_configuration_settings_probe(self, controller, connected, connect_function, disconnect_function):
        
        for i in reversed(range(self.ui.config_layout.rowCount())):
            self.ui.config_layout.removeRow(i)
        
    
        if connected:
            
            if self.pluginChosen_probe == False:
            
                for i in reversed(range(self.ui.config_layout.rowCount())):
                    self.ui.config_layout.removeRow(i)
                    
                
                old_motion = self.scanner.scanner.motion_controller
                
                self.motion_connected = True
                
                
                from scanner.scanner import Scanner
                
                self.scanner.scanner = Scanner(motion_controller=old_motion)
                
                self.configure_probe(True)
                connected = False
                self.pluginChosen_probe = True
                
                if self.pluginChosen_motion == True:
                    
                    self.scanner.scanner.motion_controller.disconnect()
                
        
            elif self.pluginChosen_probe == True:
                for setting in controller.settings_pre_connect:
                    plug = QPluginSetting(setting)
                    plug.setDisabled(True)
                    self.ui.config_layout.addRow(setting.display_label, plug)
                disconnect_button = QPushButton("Disconnect")
                disconnect_button.clicked.connect(disconnect_function)
                self.ui.config_layout.addRow(disconnect_button)
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
                    
                if self.pluginChosen_motion == True:
                    
                    self.scanner.scanner.motion_controller.connect() 
                    print(f"{self.settings_motion_list[4]},{self.settings_motion_list[5]},{self.settings_motion_list[6]},{self.settings_motion_list[7]},{self.settings_motion_list[8]}")
                    self.scanner.scanner.motion_controller.set_acceleration(self.settings_motion_list[4])
                    self.scanner.scanner.motion_controller.set_acceleration(self.settings_motion_list[5])
                    self.scanner.scanner.motion_controller.set_config(self.settings_motion_list[8],self.settings_motion_list[7],self.settings_motion_list[6])
                    #In this case 8 7 6 correspont to amps idle percent and idle timeout respectively, need to refactor this to be more general for all possible plugins FIXME: 
                       
                
        else:
                
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
                    
                    
    def set_configuration_setting_pattern(self,connected) -> None:
        
        
        if connected == True:
            for i in reversed(range(self.ui.config_layout.rowCount())):
                    self.ui.config_layout.removeRow(i)
            for setting in self.scan_controller.settings_pre_connect:
                    plug = QPluginSetting(setting)
                    plug.setDisabled(True)
                    self.ui.config_layout.addRow(setting.display_label, plug)
                
            for setting in self.scan_controller.settings_post_connect:
                    self.ui.config_layout.addRow(setting.display_label, QPluginSetting(setting))
            disconnect_button = QPushButton("Back")
            disconnect_button.clicked.connect(self.disconnect_pat)
            self.ui.config_layout.addRow(disconnect_button)
            
            ### TESTING
            self.step_size = self.scan_controller.float_step_size
            self.length = self.scan_controller.y_axis_len
            matrix = self.scan_controller.matrix 
            self.scan_testing()      
            ### TESTING
        else:   
            for i in reversed(range(self.ui.config_layout.rowCount())):
                    self.ui.config_layout.removeRow(i)
            for setting in self.scan_controller.settings_pre_connect:
                        self.ui.config_layout.addRow(setting.display_label, QPluginSetting(setting))
            connect_button = QPushButton("Generate")
            connect_button.clicked.connect(self.connect_pat)
            self.ui.config_layout.addRow(connect_button)
                     
    #endregion
    
    
    
    
    
    
    ## CONNECT DISCONNECT M/P/SP/SF
    #region c/dc functions
    @Slot()
    def connect_motion(self):
        self.scanner.scanner.motion_controller.connect()
        self.configure_motion(True)

    @Slot()
    def disconnect_motion(self):
        self.scanner.scanner.motion_controller.disconnect()
        self.configure_motion(True)
            
    @Slot()
    def connect_probe(self):
        self.scanner.scanner.probe_controller.connect()
        self.configure_probe(True)


    @Slot()
    def disconnect_probe(self):
        self.scanner.scanner.probe_controller.disconnect()
        self.configure_probe(True)
        #self.connect = False
        
    @Slot()
    def finish_config(self):
        #connect button for scan file config
        self.file_controller.connect()
        self.configure_file(True)
        
    @Slot()
    def go_back_file(self):

        self.file_controller.disconnect()
        self.configure_file(True)
        
    @Slot()
    def connect_pat(self):
        
        self.scan_controller.connect()
        self.configure_pattern(True)
    @Slot()
    def disconnect_pat(self):
        self.scan_controller.disconnect()
        self.configure_pattern(True)    
        
    #endregion
    
    
    
    
                    
    ## Helper Functions and Buttons
    #region  helper functions   
    def get_file_dir(self):

        self.file_directory = fd.askdirectory()
        
        
    
    ## Fix after 
    def plot_btn(self):
        for i in reversed(range(self.ui.plot_config_wid.rowCount())):
            self.ui.plot_config_wid.removeRow(i)
            
        self.freqs, self.s_param_names,self.all_s_params_data = self.plotter._get_and_process_data("Log Mag")
        self.plot_style = "Log Mag"
        self.processed_data = self.plotter.plot_initial_data(self.plot_style,self.freqs, self.s_param_names,self.all_s_params_data)
        self.plot_settings()

    def scan_testing(self):
        test_scan = QPushButton("Test Scan")
        test_scan.clicked.connect(self.test_scan_bt)
        self.ui.config_layout.addRow(test_scan)
        
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
        
    #region scan button func    
    def test_scan_bt(self):
        self.step_size = self.scan_controller.float_step_size
        self.length = self.scan_controller.y_axis_len
        matrix = self.scan_controller.matrix 
        self.metaData=[]
        inc = 0
        for setting in self.file_controller.settings_pre_connect:
            plug = QPluginSetting(setting)
            self.metaData.append(PluginSettingString.get_value_as_string(self.file_controller.settings_pre_connect[inc]))
            inc = inc +1
        
        self.metaData_labels = self.file_display_label_text
        
            
        self.negative_step_size = np.negative(self.step_size)
        self.scan_thread = threading.Thread(target=self.scanner.scanner.run_scan,args=(matrix,self.length,self.step_size,self.negative_step_size,self.metaData,self.metaData_labels))
        self.scan_thread.start()
        
            
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
        
    
    def plot_plugins(self):
        self.scanner.scanner._probe_controller.scan_trigger_and_wait()
    
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
            #self.connected = False
            self.pluginChosen_probe = False
        else: 
            pass 
                


    # TODO:
    def back_function_motion(self):

        pass
        
       
    
    
    def setup_plotting_canvas(self) -> None:
        main_layout = self.ui.main_layout 
       
        main_layout.addWidget(self.plotter, 1, 5)
        
    def closeEvent(self, event: QCloseEvent) -> None:
        self.scanner.close()
        return super().closeEvent(event)
    #endregion 

if __name__ == "__main__":
    app = QApplication([])
    window = MainWindow()
    app.exec()