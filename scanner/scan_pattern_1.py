


import tkinter as tk
from scanner.scan_pattern_controller import ScanPatternControllerPlugin
from tkinter import messagebox
import numpy as np
#from scan_pattern_controller import ScanPatternControllerPlugin
from scanner.plugin_setting import PluginSettingString, PluginSettingInteger, PluginSettingFloat


class ScanPattern(ScanPatternControllerPlugin):
    _is_connected:bool
    
    def __init__(self):
        super().__init__()
        
        self._is_connected = False
        self.pattern = PluginSettingString("Pattern Type Raster: ", "YX", select_options=["YX","XY"], restrict_selections=True)
        
        
        self.y_length = PluginSettingFloat("Y axis length(mm): ", 200)
        
        self.x_length = PluginSettingFloat("X axis length(mm): ", 200)
        
        self.step_size = PluginSettingFloat("Step Size(mm): ", 2)
        
        self.rotation_deg = PluginSettingFloat("Rotation Angle CC deg: ",0)
        
        self.add_setting_pre_connect(self.pattern)
        
        self.add_setting_pre_connect(self.y_length)
        
        self.add_setting_pre_connect(self.x_length)
        
        self.add_setting_pre_connect(self.step_size)
        
        self.add_setting_post_connect(self.rotation_deg)
        
    def connect(self):
        self.pattern_style = PluginSettingString.get_value_as_string(self.pattern)
        self._is_connected = True
        self.y_axis_len = PluginSettingFloat.get_value_as_string(self.y_length)
        self.x_axis_len = PluginSettingFloat.get_value_as_string(self.x_length)
        self.float_step_size = PluginSettingFloat.get_value_as_string(self.step_size)
        
        self.float_step_size = float(self.float_step_size)
        self.y_axis_len = float(self.y_axis_len)
        self.x_axis_len = float(self.x_axis_len)
        
        # self.points = self.y_axis_len / self.float_step_size 
        self.x_points = self.x_axis_len / self.float_step_size +1  
        
        self.y_points = self.y_axis_len / self.float_step_size +1
        #check divisibility 
        self.points = self.x_points * self.y_points
        if self.points.is_integer():  
            self.x_points = int(self.x_points)
            self.y_points = int(self.y_points)
            # self.matrix = self.create_pattern_matrix(self.points)
            self.matrix = self.create_pattern_matrix_generalized(self.x_points,self.y_points)
            print(self.matrix)
            
            if self.pattern_style == "XY" :
                temp_row = self.matrix[0].copy()
                self.matrix[0] = self.matrix[1]
                self.matrix[1] = temp_row
                print(f"Swapped Matrix: {self.matrix}")
                
            
            self.time_est = self.time_estimate(self.points,self.float_step_size)
            print(f"Time EST: {self.time_est} Hours")
            root = tk.Tk()
            root.withdraw() 
            messagebox.showinfo("Time EST", f"Time EST: {self.time_est} Hours")
            root.destroy
           
        else: # disconnect
            root = tk.Tk()
            root.withdraw() 
            messagebox.showinfo("Error", " Length needs to be divisible by step size")
            root.destroy
            self.disconnect()
        print(f"Connected Status Backend: {self._is_connected}")
            
    def is_connected(self) -> bool:
        print(f"Connected Status Backend _is_connected: {self._is_connected}")
        return self._is_connected
        
        
    def disconnect(self):
        self._is_connected = False
    
    def create_pattern_matrix(self,n):
        #generates (n+1)^2 (x,y) column
        row1 = np.repeat(np.arange(n+1), n+1)
        row2 = []
        for i in range(n+1):
            if i % 2 == 0:
                row2.extend(range(n+1))        
            else:
                row2.extend(range(n, -1, -1))   
        return np.array([row1, row2])
    
    def create_pattern_matrix_generalized(self,rows, cols):
    
        x_coords = np.tile(np.arange(cols), rows)

        y_coords = []
        
        for r in range(rows):
            if r % 2 == 0:
                
                y_coords.extend(np.arange(cols))
            else:
                
                y_coords.extend(np.arange(cols - 1, -1, -1))

      
        final_x = []
        final_y = []

        for r in range(rows):
            if r % 2 == 0:
                
                final_x.extend(np.arange(cols))
            else:
                
                final_x.extend(np.arange(cols - 1, -1, -1))
           
            final_y.extend([r] * cols)

        return np.array([final_y, final_x])
    
    def rotate_points(self,matrix, theta_rad):
    
        R = np.array([
            [np.cos(theta_rad), -np.sin(theta_rad)],
            [np.sin(theta_rad),  np.cos(theta_rad)]
        ])
        
        R = R @ matrix
        R[np.abs(R) < 1e-10] = 0
        
        
        return R
    
    def time_estimate(self,points,step_size):
        acceleration = 10
        time_to_point = 2*np.sqrt(step_size/acceleration)
        total_time = points*(time_to_point)
        total_time = total_time / (60*60)
        return np.round(total_time,3)