import tkinter as tk
from tkinter import ttk
from scanner.scan_pattern_controller import ScanPatternControllerPlugin
from tkinter import messagebox
import numpy as np
import csv
import os
import datetime
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

        self.random_scan = PluginSettingFloat("Random Removal by percent amount: ", 0.5)
        
        self.add_setting_pre_connect(self.pattern)
        
        self.add_setting_pre_connect(self.y_length)
        
        self.add_setting_pre_connect(self.x_length)
        
        self.add_setting_pre_connect(self.step_size)
        
        self.add_setting_post_connect(self.rotation_deg)

        self.add_setting_pre_connect(self.random_scan)
        
    def connect(self):
        self.pattern_style = PluginSettingString.get_value_as_string(self.pattern)
        self._is_connected = True
        self.y_axis_len = PluginSettingFloat.get_value_as_string(self.y_length)
        self.x_axis_len = PluginSettingFloat.get_value_as_string(self.x_length)
        self.float_step_size = PluginSettingFloat.get_value_as_string(self.step_size)
        
        self.float_step_size = float(self.float_step_size)
        self.y_axis_len = float(self.y_axis_len)
        self.x_axis_len = float(self.x_axis_len)
        
        self.y_axis_len_int = int(self.y_axis_len)
        self.x_axis_len_int = int(self.x_axis_len)
        
        # self.points = self.y_axis_len / self.float_step_size 
        self.x_points = self.x_axis_len / self.float_step_size +1  
        
        self.y_points = self.y_axis_len / self.float_step_size +1
        #check divisibility 
        self.points = self.x_points * self.y_points
        self.random_scan_patt = PluginSettingFloat.get_value_as_string(self.random_scan)
        self.random_scan_patt = float(self.random_scan_patt)

        if self.points.is_integer():  
            self.x_points = int(self.x_points)
            self.y_points = int(self.y_points)
            # self.matrix = self.create_pattern_matrix(self.points)
            self.matrix = self.create_pattern_matrix_generalized(self.x_points,self.y_points)
            if self.random_scan_patt > 0:

                self.matrix = self.random_removal(self.matrix,self.random_scan_patt)
            else:
                pass
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
    
    def random_removal(self, matrix, random_percent, export_csv=True, csv_path=None,
                       save_plot=True, plot_path=None):
        original = matrix                         # keep the full set for the plot
        n = matrix.shape[1]                       # number of points (columns)

        # interpret the input as a percentage; accept either 0.5 or 50
        frac = random_percent / 100.0 if random_percent > 1 else random_percent
        frac = min(max(frac, 0.0), 1.0)           # clamp to [0, 1]

        num_remove = int(round(n * frac))         # integer count to drop

        # --- diagnostics ---
        print("\n--- Random Removal ---")
        print(f"Input value: {random_percent}  ->  fraction: {frac:.4f}  ({frac*100:.2f}%)")
        print(f"Points before removal: {n}")
        print(f"Points to remove: {num_remove}")

        if num_remove <= 0:
            print("Nothing to remove (num_remove <= 0). Returning matrix unchanged.")
            print(f"Points after removal: {n}")
            if export_csv:
                self.export_matrix_csv(matrix, csv_path, tag="no_removal")
            if save_plot:
                self.plot_removal_points(matrix, None, plot_path, tag="no_removal")
            return matrix
        if num_remove >= n:
            num_remove = n - 1                    # never remove the whole scan
            print(f"Clamped removal count to {num_remove} (never empties the scan).")

        rng = np.random.default_rng()             # seed here for reproducibility
        remove_idx = rng.choice(n, size=num_remove, replace=False)

        keep_mask = np.ones(n, dtype=bool)
        keep_mask[remove_idx] = False

        new_matrix = matrix[:, keep_mask]         # column order preserved

        # --- diagnostics ---
        print(f"Points after removal: {new_matrix.shape[1]}")
        print(f"Removed column indices (sorted): {np.sort(remove_idx)}")
        print(f"Kept matrix shape: {new_matrix.shape}")

        if export_csv:
            self.export_matrix_csv(new_matrix, csv_path, tag="removed")
        if save_plot:
            self.plot_removal_points(new_matrix, original[:, remove_idx], plot_path, tag="removed")

        return new_matrix

    def export_matrix_csv(self, matrix, csv_path=None, tag="pattern"):
        """Write the (3, N) scan matrix to CSV as N rows of axis0,axis1,axis2 for inspection."""
        if csv_path is None:
            stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            csv_path = os.path.join(os.getcwd(), f"scan_pattern_{tag}_{stamp}.csv")

        # matrix is (3, N): rows are axes, columns are points.
        # Transpose so each CSV row is one scan point.
        points = np.asarray(matrix).T

        try:
            with open(csv_path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["index", "axis0", "axis1", "axis2"])
                for i, row in enumerate(points):
                    writer.writerow([i] + list(row))
            print(f"Scan pattern exported to: {csv_path}")
        except Exception as e:
            print(f"Failed to export scan pattern CSV: {e}")

        return csv_path

    def plot_removal_points(self, kept, removed=None, plot_path=None, tag="removed"):
        """Save a 2-D scatter of the surviving scan points (row0 vs row1).

        kept:    (3, N) matrix of points that remain in the scan.
        removed: optional (3, M) matrix of dropped points, drawn faintly for context.
        The path is walked column-order, so a line is drawn through the kept points
        to show the travel order the mover will follow.
        """
        if plot_path is None:
            stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            plot_path = os.path.join(os.getcwd(), f"scan_pattern_{tag}_{stamp}.png")

        kept = np.asarray(kept)
        a0, a1 = kept[0], kept[1]                 # axis0 vs axis1 (pre-swap)

        try:
            fig, ax = plt.subplots(figsize=(7, 7))

            # dropped points, faint, for context
            if removed is not None and np.asarray(removed).shape[1] > 0:
                removed = np.asarray(removed)
                ax.scatter(removed[0], removed[1], s=25, facecolors='none',
                           edgecolors='lightgray', label=f"removed ({removed.shape[1]})")

            # travel path through the kept points, in column order
            ax.plot(a0, a1, color='tab:blue', alpha=0.4, linewidth=0.8, zorder=1)
            ax.scatter(a0, a1, s=30, color='tab:blue', zorder=2,
                       label=f"kept ({kept.shape[1]})")

            # mark start and end so the ordering is unambiguous
            ax.scatter(a0[0], a1[0], s=90, color='green', marker='o', zorder=3, label="start")
            ax.scatter(a0[-1], a1[-1], s=90, color='red', marker='X', zorder=3, label="end")

            ax.set_xlabel("axis0 (grid index)")
            ax.set_ylabel("axis1 (grid index)")
            ax.set_title(f"Scan pattern — {tag} ({kept.shape[1]} points)")
            ax.set_aspect('equal', adjustable='box')
            ax.legend(loc='upper right', fontsize=8)
            ax.grid(True, alpha=0.3)

            fig.tight_layout()
            fig.savefig(plot_path, dpi=150)
            plt.close(fig)
            print(f"Scan pattern image saved to: {plot_path}")
        except Exception as e:
            print(f"Failed to save scan pattern image: {e}")

        return plot_path

    def apply_planar_slope_ui(self, matrix_xy, step_size, s_deg=10, s_dir=90.0, z_off=50.0):
        
        root = tk.Tk()
        root.withdraw()

        popup = tk.Toplevel(root)
        popup.title("Planar Slope Parameters")
        popup.attributes('-topmost', True)
        
        self._result_matrix = None
        z_step_size = step_size * np.tan(np.deg2rad(s_deg))
        def on_generate():
            
           
            order = order_var.get()

            if order == "YX":
                y_idx, x_idx, z_old = matrix_xy
            else:
                x_idx, y_idx, z_old = matrix_xy

            
            x = x_idx * step_size
            y = y_idx * step_size

            
            slope = np.tan(np.deg2rad(s_deg))
            phi = np.deg2rad(s_dir)

            
            z = z_off + slope * (x * np.cos(phi) + y * np.sin(phi))

            self._result_matrix = np.vstack((x, y, z))
            
            
            
            
            print("\n--- Generated Scan Matrix (XYZ) ---")
            print(self._result_matrix)
            print(f"Shape: {self._result_matrix.shape}\n")

            # 4. Plot and Clean up
            self.plot_scan_3d(self._result_matrix)
            popup.destroy()
            root.quit()
                
            
    
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
        
       
        try: root.destroy()
        except: pass
        
        return self._result_matrix, z_step_size

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