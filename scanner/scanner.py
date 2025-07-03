
from scanner.motion_controller import MotionController
from scanner.probe_controller import ProbeController
from scanner.plugin_switcher import PluginSwitcher
from scanner.plugin_switcher_motion import PluginSwitcherMotion
import importlib


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
            
    
    def run_scan(self,matrix,length,step_size,negative_step_size) -> None:
        x_axis_pos = 0
        y_axis_pos = 0
      
        negative_thresh = -0.01
        positive_thresh = 0.01

        for i in range (0,len(matrix[0])):
            if i == 0:
                print("First scan in place, no movement")
                # SCAN
            else:
                
                difference = matrix[:,i] - matrix[:,i-1]
                #x axis
                if difference[0] > positive_thresh:
                    
                    
                    if x_axis_pos-step_size > -225:
                        self._motion_controller.move_absolute({0:step_size})
                    else: 
                        print("Motion Stopped due to user set boundary")
                    x_axis_pos = x_axis_pos - step_size
                    
                    busy_bit = self._motion_controller.is_moving()
                    
                    while busy_bit[0] != 224:
                        busy_bit = self._motion_controller.is_moving()
                   
                    
                elif difference[0] < negative_thresh:
                
                    
                    if x_axis_pos + step_size < 0:
                        self._motion_controller.move_absolute({0:negative_step_size})
                    else:
                        print("Motion Stopped due to user set boundary")

                    x_axis_pos = x_axis_pos + step_size
                    
                    
                    busy_bit = self._motion_controller.is_moving()
                    while busy_bit[0] != 224:
                        busy_bit = self._motion_controller.is_moving()
        
                #y axis
                if difference[1] > positive_thresh:
                   
                   
                   if y_axis_pos - step_size > -225:
                        self._motion_controller.move_absolute({1:step_size})
                   else:
                       print("Motion Stopped due to user set boundary")
                   y_axis_pos = y_axis_pos - step_size
                   
                   busy_bit = self._motion_controller.is_moving()
                   while busy_bit[1] != 225:
                      busy_bit = self._motion_controller.is_moving()
                   
                elif difference[1] < negative_thresh:
                    
                    if y_axis_pos + step_size < 0:
                        self._motion_controller.move_absolute({1:negative_step_size})
                    else:
                        print("Motion Stopped due to user set boundary")
                    y_axis_pos = y_axis_pos + step_size
                    
                   
                    busy_bit = self._motion_controller.is_moving()
                    while busy_bit[1] != 225:
                        busy_bit = self._motion_controller.is_moving()
                        
    
    
        

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


    






