
from scanner.motion_controller import MotionController
from scanner.probe_controller import ProbeController
from scanner.plugin_switcher import PluginSwitcher
from scanner.plugin_switcher_motion import PluginSwitcherMotion
import importlib
import numpy as np
from  gui.plotter import plotter_system
class Scanner():
    _motion_controller: MotionController

    _probe_controller: ProbeController
    
   
    
    def __init__(self, motion_controller: MotionController | None = None, probe_controller: ProbeController | None = None) -> None:
       # self.plotter = plotter_system()
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
            
    
    def run_scan(self,matrix,length,step_size,negative_step_size) -> None:
        x_axis_pos = 0
        y_axis_pos = 0
      
        negative_thresh = -0.01
        positive_thresh = 0.01
        step_size = step_size/2 ## For some reason the step size to mm ratio is double, need to check what is going on there but this is a quick fix for now
        negative_step_size = negative_step_size/2
        

        for i in range (0,len(matrix[0])):
            self.vna_sim()
            
            if i == 0:
                print("First scan in place, no movement")
    
                #self.plotter._get_and_process_data("Log Mag")
                # SCAN
            elif i == len(matrix[0])-1:
                # SCAN END
                #self.plotter._get_and_process_data("Log Mag")
                print("Scan END: ")
            else:
                
                difference = matrix[:,i] - matrix[:,i-1]
                #x axis
                #self.plotter._get_and_process_data("Log Mag")
                
                if difference[0] > positive_thresh:
                    
              
                    self._motion_controller.move_absolute({0:step_size})
                    
                    
                    
                    busy_bit = self._motion_controller.is_moving()
                    
                    while busy_bit[0] != 224:
                        busy_bit = self._motion_controller.is_moving()
                   
                    
                elif difference[0] < negative_thresh:
                
                    
                    self._motion_controller.move_absolute({0:negative_step_size})
                   

                    
                    
                    
                    busy_bit = self._motion_controller.is_moving()
                    while busy_bit[0] != 224:
                        busy_bit = self._motion_controller.is_moving()
        
                #y axis
                if difference[1] > positive_thresh:
                   
                   
                   self._motion_controller.move_absolute({1:step_size})
                   
                   
                   
                   busy_bit = self._motion_controller.is_moving()
                   while busy_bit[1] != 225:
                      busy_bit = self._motion_controller.is_moving()
                   
                elif difference[1] < negative_thresh:
                    
                    self._motion_controller.move_absolute({1:negative_step_size})
                   
                    
                    
                   
                    busy_bit = self._motion_controller.is_moving()
                    while busy_bit[1] != 225:
                        busy_bit = self._motion_controller.is_moving()
                        
    def vna_sim(self):

        self.output_filepath = "vna_data2.txt"
        
        #freqs = np.array(self._probe_controller.get_xaxis_coords())
        all_s_params_data = self._probe_controller.scan_read_measurement(0, ())
        #s_param_names = self._probe_controller.get_channel_names()

        
        
        with open(self.output_filepath, 'a') as f:
            
            f.write(f"{all_s_params_data}\n")
            
        print(f"Data written to {self.output_filepath}")
        
    
    
        

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

    

    






