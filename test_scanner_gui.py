import globals
from typing import Iterable

from PySide6.QtCore import QTimer, Slot
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton
import tkinter as tk
from tkinter import simpledialog
from tkinter import filedialog as fd
from gui.scanner_qt import ScannerQt
from gui.ui_scanner import Ui_MainWindow
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


for finder, module_name, ispkg in pkgutil.iter_modules(plugin_pkg.__path__):
    importlib.import_module(f"scanner.Plugins.{module_name}")

class MainWindow(QMainWindow):
    scanner: ScannerQt
    ui: Ui_MainWindow
    pluginChosen = False

    def __init__(self) -> None:
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.scanner = ScannerQt()
        
        try:
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
        self.display_timer.timeout.connect(self.scanner.update_motion)
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
            self.set_configuration_settings(controller._driver, controller.is_connected(), self.connect_motion, self.disconnect_motion)
        else:
            for i in reversed(range(self.ui.config_layout.rowCount())):
                self.ui.config_layout.removeRow(i)
                
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
            self.set_configuration_settings(controller._probe, controller.is_connected(), self.connect_probe, self.disconnect_probe)
        else:
            for i in reversed(range(self.ui.config_layout.rowCount())):
                self.ui.config_layout.removeRow(i)
            
    @Slot()
    def connect_probe(self):
        self.scanner.scanner.probe_controller.connect()
        self.configure_probe(True)

    @Slot()
    def disconnect_probe(self):
        self.scanner.scanner.probe_controller.disconnect()
        self.configure_probe(True)

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
    
    

    def set_configuration_settings(self, controller, connected, connect_function, disconnect_function):

       

        for i in reversed(range(self.ui.config_layout.rowCount())):
            self.ui.config_layout.removeRow(i)
        #globals.value_flag = controller.settings_pre_connect[0].value

        if connected:
            #print debugging
            if self.pluginChosen == False:
                print(PluginSwitcher.plugin_name)
                
                print(PluginSwitcher.plugin_name)
                
                print(PluginSwitcher.plugin_name)
                print(controller.settings_pre_connect[0].value)


                for i in reversed(range(self.ui.config_layout.rowCount())):
                    self.ui.config_layout.removeRow(i)
            
                old_motion = self.scanner.scanner.motion_controller
                #newProbeInst = PluginSwitcher.plugin_name
            
                # re‐instantiate Scanner
                from scanner.scanner import Scanner
                self.scanner.scanner = Scanner(motion_controller=old_motion)

                self.configure_probe(True)
                connected = False
                self.pluginChosen = True

            elif self.pluginChosen == True:
                for setting in controller.settings_pre_connect:
                    plug = QPluginSetting(setting)
                    plug.setDisabled(True)
                    self.ui.config_layout.addRow(setting.display_label, plug)
                connect_button = QPushButton("Disconnect")
                connect_button.clicked.connect(disconnect_function)
                self.ui.config_layout.addRow(connect_button)
                for setting in controller.settings_post_connect:
                    self.ui.config_layout.addRow(setting.display_label, QPluginSetting(setting))
                plot_btn = QPushButton("Plot")
                plot_btn.clicked.connect(controller.plot)   
            
                self.ui.config_layout.addRow(plot_btn)
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


    def closeEvent(self, event: QCloseEvent) -> None:
        self.scanner.close()
        return super().closeEvent(event)

if __name__ == "__main__":
    app = QApplication([])
    window = MainWindow()
    app.exec()