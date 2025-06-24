
from itertools import product
import time

from scanner.plugin_setting import PluginSetting
import os 
import sys 
import importlib.util
from scanner.motion_controller import MotionController
from scanner.probe_controller import ProbeController
import tkinter as tk
from tkinter import simpledialog
from tkinter import filedialog as fd
from scanner.gcode_simulator import GcodeSimulator
from scanner.probe_simulator import ProbeSimulator
from scanner.Plugins.motion_controller_plugin import motion_controller_plugin
#from scanner.VNA_Plugin import VNAProbePlugin
from scanner.plugin_switcher import PluginSwitcher
from scanner.plugin_switcher_motion import PluginSwitcherMotion
import importlib
import scanner.Plugins as plugin_pkg

#optimization TODO: 
import threading
import multiprocessing






# for finder, module_name, ispkg in pkgutil.iter_modules(plugin_pkg.__path__):
#     importlib.import_module(f"scanner.Plugins.{module_name}")

class Scanner():
    _motion_controller: MotionController

    _probe_controller: ProbeController
    
    def __init__(self, motion_controller: MotionController | None = None, probe_controller: ProbeController | None = None) -> None:

        if PluginSwitcher.plugin_name == "":
            
            self.plugin_Probe = PluginSwitcher()
            
        else:
           
            plugin_module_name = f"scanner.Plugins.{PluginSwitcher.basename.replace('.py', '')}"
            
            try:
                plugin_module = importlib.import_module(plugin_module_name)
                
                plugin_class = getattr(plugin_module, PluginSwitcher.plugin_name)
                
                self.plugin_Probe = plugin_class()
                
                
    
                
            except (ImportError, AttributeError) as e:
                print(f"Error loading plugin {PluginSwitcher.plugin_name} from {plugin_module_name}: {e}")
               
                self.plugin_Probe = PluginSwitcher()
                
                
        if probe_controller is None:
            self._probe_controller = ProbeController(self.plugin_Probe)
        elif probe_controller == "Back":
            self._probe_controller = ProbeController(PluginSwitcher()) 
        else:
            self._probe_controller = ProbeController(self.plugin_Probe)    
            
            
            
                 
                
        if PluginSwitcherMotion.plugin_name == "":
            
            
            self.plugin_Motion = PluginSwitcherMotion()
        else:
           
            
            motion_module_name = f"scanner.Plugins.{PluginSwitcherMotion.basename.replace('.py', '')}"
            try:
                
                
                motion_module = importlib.import_module(motion_module_name)
                
                motion_class = getattr(motion_module, PluginSwitcherMotion.plugin_name)
                
                self.plugin_Motion = motion_class()
                
            except (ImportError, AttributeError) as e:
        
                self.plugin_Motion = PluginSwitcherMotion()        
                
        if motion_controller is None:
            self._motion_controller = MotionController(self.plugin_Motion)
        elif motion_controller== "Back":
            self._motion_controller = MotionController(PluginSwitcherMotion())
        else:
            self._motion_controller = MotionController(self.plugin_Motion)
            
            
        
        
        
        
        
        
        
        
        
        
        
        
        
        

    def run_scan(self) -> None:
        scan_xy = [(float(x) - 20, float(40 - y if x%20==10 else y) - 20) for x,y in product(range(0, 50, 10), repeat=2)]

        start = time.time()
        for (i, (x, y)) in enumerate(scan_xy):
            self._motion_controller.move_absolute({0:x, 1:y})
            if i == 0:
                self._probe_controller.scan_begin()
            else:
                # Add thread here TODO:
                self._probe_controller.scan_read_measurement(i - 1, (x, y))

            while self._motion_controller.is_moving():
                time.sleep(0.001)

            self._probe_controller.scan_trigger_and_wait(i, (x, y))
        
        self._motion_controller.move_absolute({0:0, 1:0})
        self._probe_controller.scan_read_measurement(len(scan_xy), (x, y))
        self._probe_controller.scan_end()
        
        print(f"Total time elapsed: {time.time() - start} seconds.")

    def close(self) -> None:
        self._motion_controller.disconnect()
        self._probe_controller.disconnect()


    def close_Probe(self) -> None:
        self._probe_controller.disconnect()

    def close_Motion(self) -> None:
        self._motion_controller.disconnect()
    @property
    def motion_controller(self) -> MotionController:
        return self._motion_controller
    
    @property
    def probe_controller(self) -> ProbeController:
        return self._probe_controller


    






