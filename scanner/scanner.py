
from scanner.motion_controller import MotionController
from scanner.probe_controller import ProbeController
from scanner.plugin_switcher import PluginSwitcher
from scanner.plugin_switcher_motion import PluginSwitcherMotion
import importlib
import numpy as np
import threading
import datetime
import time 
import os
class Scanner():
    _motion_controller: MotionController

    _probe_controller: ProbeController
    
    
    
    def __init__(self, motion_controller: MotionController | None = None, probe_controller: ProbeController | None = None) -> None:
       # self.plotter = plotter_system()
        self.output_filepath = "vna_data3.txt"
        if PluginSwitcher.plugin_name == "":
            
            self.plugin_Probe = PluginSwitcher()
            
        else:
           
            plugin_module_name = f"scanner.Plugins.{PluginSwitcher.basename.replace('.py', '')}"
            
            try:
                plugin_module = importlib.import_module(plugin_module_name)
                
                plugin_class = getattr(plugin_module, PluginSwitcher.plugin_name)
                
                self.plugin_Probe = plugin_class()
                
                
    
                
            except (ImportError, AttributeError) as e:
                #print(f"Error loading plugin {PluginSwitcher.plugin_name} from {plugin_module_name}: {e}")
               
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
        

        negative_thresh = -0.01
        positive_thresh = 0.01
        step_size = step_size ## For some reason the step size to mm ratio is double, need to check what is going on there but this is a quick fix for now FIXME:
        negative_step_size = negative_step_size
        self._open_output_file()
        

        for i in range (0,len(matrix[0])):
            
            start=time.time()
            all_s_params_data = self.vna_sim()
            #print(all_s_params_data)
            end_1 = time.time()
            
            print(f"Time to excecute vna sim func: {end_1-start} \n")
            
            if i == 0:
                
                self.vna_thread = threading.Thread(target=self.vna_write_data,args=(all_s_params_data,))
                self.vna_thread.start()
               
                self.vna_thread.join()
                
            elif i == len(matrix[0])-1:
                # SCAN END
                
                self.vna_thread = threading.Thread(target=self.vna_write_data,args=(all_s_params_data,))
                self.vna_thread.start()
               
                self.vna_thread.join()
                end_2 = time.time()
                print(f"Scan Ended: {end_2-start} seconds")
                
            else:
                
                difference = matrix[:,i] - matrix[:,i-1]
                #x axis
               
                
                if difference[0] > positive_thresh:
                    
              
                    self._motion_controller.move_absolute({0:step_size})
                    
                    
                    
                    busy_bit = self._motion_controller.is_moving()
                    
                
                    self.vna_thread = threading.Thread(target=self.vna_write_data,args=(all_s_params_data,))
                    self.vna_thread.start()
                    
                    while busy_bit[0] == True:
                        busy_bit = self._motion_controller.is_moving()
                        
                    self.vna_thread.join()
                    
                elif difference[0] < negative_thresh:
                
                    
                    self._motion_controller.move_absolute({0:negative_step_size})
                   

                    
                    
                    
                    busy_bit = self._motion_controller.is_moving()
                    
                    self.vna_thread = threading.Thread(target=self.vna_write_data,args=(all_s_params_data,))
                    self.vna_thread.start()
                    
                    while busy_bit[0] == True:
                        busy_bit = self._motion_controller.is_moving()
                        
                    self.vna_thread.join()
                    
                    
                    
                    
                #y axis
                if difference[1] > positive_thresh:
                   
                   
                   self._motion_controller.move_absolute({1:step_size})
                   
                   
                   
                   busy_bit = self._motion_controller.is_moving()
                   self.vna_thread = threading.Thread(target=self.vna_write_data,args=(all_s_params_data,))
                   self.vna_thread.start()
                       
                   while busy_bit[1] == True:
                       busy_bit = self._motion_controller.is_moving()
                       
                   self.vna_thread.join()
                   
                   
                elif difference[1] < negative_thresh:
                    
                    self._motion_controller.move_absolute({1:negative_step_size})
                   
                    
                    
                   
                    busy_bit = self._motion_controller.is_moving()
                    
                    
                        
                    self.vna_thread = threading.Thread(target=self.vna_write_data,args=(all_s_params_data,))
                    self.vna_thread.start()
    
                    while busy_bit[1] == True:
                        busy_bit = self._motion_controller.is_moving()
                    self.vna_thread.join()
                    
                end = time.time()
                print(f"Time it took for one scan movement: {end-start} \n")
   
                        
    def vna_sim(self):
        
        start = time.time_ns()
        #freqs = np.array(self._probe_controller.get_xaxis_coords())
        self._probe_controller.scan_begin()
        all_s_params_data = self._probe_controller.scan_read_measurement(0, ())
        #s_param_names = self._probe_controller.get_channel_names()
        end = time.time_ns()
        
        print(f"Time it took for vna data transfer: {end-start}")
        
        return all_s_params_data
        
    def vna_write_data(self,all_s_params_data):
        
        start = time.time()
        
                
        for s_param_name, s_param_values in all_s_params_data.items():
            
            values_string = ", ".join([str(val) for val in s_param_values])
            
            
            self.output_file_handle.write(f"{s_param_name}: [{values_string}]\n")

        self.output_file_handle.write("\n") 

        self.output_file_handle.flush() 
        os.fsync(self.output_file_handle.fileno())
        
        end = time.time()
        
        print(f"\n Time it took to write data: {end-start} \n")
    
    def _open_output_file(self):
        
        try:
            
            self.output_file_handle = open(self.output_filepath, 'w')
            
            self.output_file_handle.write(f"# VNA Scan Data - Started: {datetime.datetime.now()}\n")
            
        
          
        except Exception as e:
            
            self.output_file_handle = None 
            
    def _close_output_file(self):
       
        if self.output_file_handle:
            try:
                self.output_file_handle.close()
         
            except Exception as e:
                print(f"Error closing output file {self.output_filepath}: {e}")
            finally:
                self.output_file_handle = None
        

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

    

    






