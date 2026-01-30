


import tkinter as tk
from tkinter import ttk
from scanner.scan_pattern_controller import ScanPatternControllerPlugin
from tkinter import messagebox
import numpy as np
#from scan_pattern_controller import ScanPatternControllerPlugin
from scanner.plugin_setting import PluginSettingString, PluginSettingInteger, PluginSettingFloat
import matplotlib.pyplot as plt

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


        z = np.zeros(len(final_x))
                
        
        return np.array([final_y, final_x,z])
    
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
    
    
    def apply_planar_slope_ui(self, matrix_xy, step_size, s_deg=45, s_dir=0.0, z_off=50.0):
        # Initialize hidden root for the popup
        root = tk.Tk()
        root.withdraw()

        popup = tk.Toplevel(root)
        popup.title("Planar Slope Parameters")
        popup.attributes('-topmost', True)
        
        self._result_matrix = None

        def on_generate():
            
            # # 1. Capture user inputs
            # s_size = float(entry_step.get())
            # s_deg = float(entry_slope.get())
            # s_dir = float(entry_dir.get())
            # z_off = float(entry_z0.get())
            # print(f"Z Offset: {z_off}, Slope: {s_deg}, Slope Dir: {s_dir}, Step Size: {s_size}")
            order = order_var.get()

            if order == "YX":
                y_idx, x_idx, z_old = matrix_xy
            else:
                x_idx, y_idx, z_old = matrix_xy

            # Convert indices to physical units (mm)
            x = x_idx * step_size
            y = y_idx * step_size

            # Apply the planar slope formula
            slope = np.tan(np.deg2rad(s_deg))
            phi = np.deg2rad(s_dir)

            # Planar Equation: z = z0 + slope * (x*cos(phi) + y*sin(phi))
            z = z_off + slope * (x * np.cos(phi) + y * np.sin(phi))

            # Overwrite the result matrix with the new calculated XYZ coordinates
            self._result_matrix = np.vstack((x, y, z))
            
            
            
            # 3. Print the matrix to console (as requested)
            print("\n--- Generated Scan Matrix (XYZ) ---")
            print(self._result_matrix)
            print(f"Shape: {self._result_matrix.shape}\n")

            # 4. Plot and Clean up
            self.plot_scan_3d(self._result_matrix)
            popup.destroy()
            root.quit()
                
            
        # --- UI Setup ---
        fields = [("Step Size", str(step_size)), ("Slope (deg)", "5.0"), 
                  ("Slope Dir (deg)", "0"), ("Z Offset (z0)", "50.0")]
        
        entries = []
        for i, (label_text, default_val) in enumerate(fields):
            tk.Label(popup, text=label_text).grid(row=i, column=0, padx=15, pady=5, sticky="e")
            e = tk.Entry(popup)
            e.insert(0, default_val)
            e.grid(row=i, column=1, padx=15, pady=5)
            entries.append(e)

        entry_step, entry_slope, entry_dir, entry_z0 = entries

        tk.Label(popup, text="Order:").grid(row=4, column=0, sticky="e")
        order_var = tk.StringVar(value="YX")
        ttk.OptionMenu(popup, order_var, "YX", "YX", "XY").grid(row=4, column=1, sticky="w", padx=15)

        tk.Button(popup, text="GENERATE & PRINT", command=on_generate, 
                  bg="#27ae60", fg="white", font=('Arial', 10, 'bold'), height=2).grid(row=5, columnspan=2, pady=20)

        # Run the UI loop
        popup.mainloop() 
        
        # Cleanup and return to the main script
        try: root.destroy()
        except: pass
        
        return self._result_matrix

    def plot_scan_3d(self, xyz, stride=1):
        X, Y, Z = xyz[0, ::stride], xyz[1, ::stride], xyz[2, ::stride]
        fig = plt.figure()
        ax = fig.add_subplot(111, projection="3d")
        ax.plot(X, Y, Z, color='blue', alpha=0.7)
        ax.set_xlabel("X (mm)")
        ax.set_ylabel("Y (mm)")
        ax.set_zlabel("Z (mm)")
        
        # Keep aspect ratio equal to avoid visual distortion
        ax.set_box_aspect([np.ptp(X), np.ptp(Y), np.ptp(Z)])
        plt.show()