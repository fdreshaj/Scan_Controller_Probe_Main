
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
import struct
#from npy_append_array import NpyAppendArray
import h5py
import tkinter as tk
from tkinter import ttk
from alive_progress import alive_bar



class Scanner():
    _motion_controller: MotionController

    _probe_controller: ProbeController



    def __init__(self, motion_controller: MotionController | None = None, probe_controller: ProbeController | None = None, signal_scope=None) -> None:
       
        self.output_filepath = "vna_data5.bin"
        self.time_linearity_test = []
        self.signal_scope = signal_scope

       
        self._plugin_settings_cache = {}
        
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
        
    
    
    
    def run_scan(self, matrix, length, step_size, negative_step_size, meta_data, meta_data_labels, camera_app=None, scan_settings=None, scan_point_callback=None) -> None:
        self.data_inc = 0
        self.matrix_copy = matrix
        negative_thresh = -0.01
        positive_thresh = 0.01
        step_size = step_size 
        negative_step_size = negative_step_size
        self._open_output_file()
        self.frequencies = self._probe_controller.get_xaxis_coords()

        self.start_data = time.time()

        self.HDF5FILE = h5py.File(f"{meta_data[1]}.hdf5", mode="a")  # meta 1 is filename

        # Write metadata
        for i in range(0, len(meta_data)):
            self.HDF5FILE.attrs[f'{meta_data_labels[i]}'] = f'{meta_data[i]}'
        self.HDF5FILE.attrs['Units'] = 'Hz'
        self.HDF5FILE.attrs['wasUniform'] = 1  
        self.HDF5FILE.attrs['isComplex'] = 1  
        self.HDF5FILE.attrs['isComplex'] = True
        self.HDF5FILE.attrs['numPoints'] = len(matrix[0])
        self.HDF5FILE.attrs['numFrequencies'] = len(self.frequencies)

        
        if scan_settings:
            self.HDF5FILE.create_group("/ScanSettings")
            for key, value in scan_settings.items():
                self.HDF5FILE["/ScanSettings"].attrs[key] = str(value)

        # Save camera image to HDF5
        if camera_app:
            try:
                frame = camera_app.get_current_frame()
                if frame is not None:
                    import cv2
                    # Encode image as PNG
                    is_success, buffer = cv2.imencode(".png", frame)
                    if is_success:
                        # Store as binary dataset
                        self.HDF5FILE.create_dataset("/CameraImage", data=np.frombuffer(buffer, dtype=np.uint8))
                        self.HDF5FILE["/CameraImage"].attrs['format'] = 'PNG'
                        self.HDF5FILE["/CameraImage"].attrs['timestamp'] = datetime.datetime.now().isoformat()
                        print("Camera image saved to HDF5 file")
            except Exception as e:
                print(f"Failed to save camera image: {e}")

        freqs_ghz = np.asarray(self.frequencies, dtype=float) / 1e9
        # Create datasets for frequencies and coordinates
        self.HDF5FILE.create_dataset("/Frequencies/Range", data=freqs_ghz)  # Store frequencies in GHz
        self.HDF5FILE.create_dataset("/Coords/x_data", data=self.matrix_copy[0, :]*step_size)
        self.HDF5FILE.create_dataset("/Coords/y_data", data=self.matrix_copy[1, :]*step_size)
        self.HDF5FILE.create_dataset("/Coords/z_data", data=np.zeros(len(matrix[0])))

        # Get S-parameter names from probe controller
        self.s_param_names = self._probe_controller.get_channel_names()

        # Pre-allocate arrays for bulk data storage
        num_points = len(matrix[0])
        num_freqs = len(self.frequencies)

        # Create datasets for each S-parameter dynamically
        self.HDF5FILE.create_group("/Data")
        for s_param_name in self.s_param_names:
            self.HDF5FILE.create_dataset(f"/Data/{s_param_name}_real", (num_points, num_freqs), dtype='float64')
            self.HDF5FILE.create_dataset(f"/Data/{s_param_name}_imag", (num_points, num_freqs), dtype='float64')
            print(f"Created datasets for {s_param_name}")

        # VNA error tracking - only trigger error if it fails twice in a row
        vna_consecutive_failures = 0

        with alive_bar(len(matrix[0])) as bar:
            for i in range(len(matrix[0])):
                start = time.time()

                # Move to position FIRST (except for point 0 where we're already there)
                if i > 0:
                    diff_Var = matrix[:, i] - matrix[:, i-1]

                    try:
                        if self.signal_scope:
                            self.signal_scope.set_lane_active("Motor")

                        if diff_Var[0] > positive_thresh:
                            self._motion_controller.move_absolute({0: step_size})
                            busy_bit = self._motion_controller.is_moving()
                            while busy_bit[0] == True:
                                busy_bit = self._motion_controller.is_moving()
                        elif diff_Var[0] < negative_thresh:
                            self._motion_controller.move_absolute({0: negative_step_size})
                            busy_bit = self._motion_controller.is_moving()
                            while busy_bit[0] == True:
                                busy_bit = self._motion_controller.is_moving()

                        if diff_Var[1] > positive_thresh:
                            self._motion_controller.move_absolute({1: step_size})
                            busy_bit = self._motion_controller.is_moving()
                            while busy_bit[1] == True:
                                busy_bit = self._motion_controller.is_moving()
                        elif diff_Var[1] < negative_thresh:
                            self._motion_controller.move_absolute({1: negative_step_size})
                            busy_bit = self._motion_controller.is_moving()
                            while busy_bit[1] == True:
                                busy_bit = self._motion_controller.is_moving()
                            time.sleep(0.1)
                        if diff_Var[2] > positive_thresh:
                            self._motion_controller.move_absolute({2: step_size})
                            busy_bit = self._motion_controller.is_moving()
                            while busy_bit[2] == True:
                                busy_bit = self._motion_controller.is_moving()
                        elif diff_Var[2] < negative_thresh:
                            self._motion_controller.move_absolute({2: negative_step_size})
                            busy_bit = self._motion_controller.is_moving()
                            while busy_bit[2] == True:
                                busy_bit = self._motion_controller.is_moving()

                        if self.signal_scope:
                            self.signal_scope.set_lane_idle("Motor")
                    except Exception as e:
                        if self.signal_scope:
                            self.signal_scope.set_lane_idle("Motor")

                        is_endstop = "ENDSTOP VIOLATION" in str(e)
                        error_category = "Endstop Violation" if is_endstop else "Motor Failure"
                        error_msg = f"{error_category}: {str(e)}"
                        
                        print(error_msg)

                        if self.signal_scope:
                            self.signal_scope.freeze_on_error(
                                error_msg,
                                "Motor",
                                {
                                    "point_index": i,
                                    "current_position": matrix[:, i-1].tolist(),
                                    "target_position": matrix[:, i].tolist(),
                                    "exception_type": type(e).__name__,
                                    "is_boundary_violation": is_endstop
                                }
                            )
                        break

                # VNA measurement with error handling and retry logic
                all_s_params_data = None
                try:
                    if self.signal_scope:
                        self.signal_scope.set_lane_active("VNA")

                    all_s_params_data = self.vna_sim()

                    if self.signal_scope:
                        self.signal_scope.set_lane_idle("VNA")

                    # VNA measurement successful - reset consecutive failure counter
                    vna_consecutive_failures = 0

                except Exception as e:
                    if self.signal_scope:
                        self.signal_scope.set_lane_idle("VNA")

                    vna_consecutive_failures += 1
                    error_msg = f"VNA measurement failed (attempt {vna_consecutive_failures}): {str(e)}"
                    print(error_msg)

                    # Only treat as fatal error if it fails twice in a row
                    if vna_consecutive_failures >= 2:
                        if self.signal_scope:
                            self.signal_scope.freeze_on_error(
                                f"VNA measurement failed twice consecutively: {str(e)}",
                                "VNA",
                                {
                                    "point_index": i,
                                    "position": matrix[:, i].tolist(),
                                    "exception_type": type(e).__name__,
                                    "consecutive_failures": vna_consecutive_failures
                                }
                            )
                        break
                    else:
                        # Single failure - zero pad this data point and continue
                        print(f"Single VNA failure at point {i}. Zero-padding data and continuing...")
                        all_s_params_data = {}
                        for s_param_name in self.s_param_names:
                            # Create zero-padded data with correct shape
                            all_s_params_data[s_param_name] = np.zeros(num_freqs, dtype=complex)

                current_position = self._motion_controller.get_current_positions()

                # File I/O with error handling
                print("Writing to index", self.data_inc)
                try:
                    if self.signal_scope:
                        self.signal_scope.set_lane_active("File I/O")

                    self.vna_thread = threading.Thread(target=self.vna_write_data_bulk, args=(all_s_params_data,))
                    self.vna_thread.start()
                    self.vna_thread.join()

                    if self.signal_scope:
                        self.signal_scope.set_lane_idle("File I/O")
                except Exception as e:
                    if self.signal_scope:
                        self.signal_scope.set_lane_idle("File I/O")

                    error_msg = f"File write failed: {str(e)}"
                    print(error_msg)
                    if self.signal_scope:
                        self.signal_scope.freeze_on_error(
                            error_msg,
                            "File I/O",
                            {
                                "point_index": i,
                                "data_inc": self.data_inc,
                                "exception_type": type(e).__name__
                            }
                        )
                    break
                
                self.data_inc += 1

                # Call callback for real-time plotting updates
                if scan_point_callback is not None:
                    try:
                        scan_point_callback(i, all_s_params_data)
                    except Exception as e:
                        print(f"Warning: Scan point callback failed: {e}")

                end = time.time()
                bar()
            
            self.HDF5FILE.close()
            self._close_output_file()
            end_2 = time.time()
            print("Scan complete. Total time:", end_2 - self.start_data)
            #dset6 = self.HDF5FILE.create_dataset("/Coords/write_time_testing",data=self.time_linearity_test)
                
                        
    def vna_sim(self):
        
        start = time.time_ns()
        #freqs = np.array(self._probe_controller.get_xaxis_coords())
        self._probe_controller.scan_begin()
        all_s_params_data = self._probe_controller.scan_read_measurement(0, ())
        #s_param_names = self._probe_controller.get_channel_names()
        end = time.time_ns()
        
       
        return all_s_params_data
        
    def vna_write_data(self,all_s_params_data):
        
        start_data = time.time()
        self.HDF5FILE.create_group(f"/Point_Data/{self.matrix_copy[:,self.data_inc]}")
        for s_param_name, s_param_values in all_s_params_data.items():
            
            
            
            
            
            self.HDF5FILE.create_group(f"/Point_Data/{self.matrix_copy[:,self.data_inc]}/{s_param_name}")
            
            dset = self.HDF5FILE.create_dataset(f"/Point_Data/{self.matrix_copy[:,self.data_inc]}/{s_param_name}/data",data=s_param_values)
            print(f"s_param_name: {s_param_name}, shape: {s_param_values.shape}, type: {s_param_values.dtype}, values: {s_param_values}")
            
    
            
        end = time.time()
        
        self.motion_tracker_thread = threading.Thread(target=self.motion_tracker, args=(self.matrix_copy[:,self.data_inc],))
        self.motion_tracker_thread.start()
        self.time_linearity_test.append(end - start_data)
    
    def vna_write_data_bulk(self, all_s_params_data):
        
        start_data = time.time()
        
        for s_param_name, s_param_values in all_s_params_data.items():
            # Write to bulk arrays (much faster than creating individual groups)
            self.HDF5FILE[f"/Data/{s_param_name}_real"][self.data_inc, :] = np.real(s_param_values)
            self.HDF5FILE[f"/Data/{s_param_name}_imag"][self.data_inc, :] = np.imag(s_param_values)
            print(f"s_param_name: {s_param_name}, shape: {s_param_values.shape}, type: {s_param_values.dtype}")
        
        end = time.time()
        
        self.motion_tracker_thread = threading.Thread(target=self.motion_tracker, args=(self.matrix_copy[:, self.data_inc],))
        self.motion_tracker_thread.start()
        self.time_linearity_test.append(end - start_data)
    
    
    def motion_tracker(self,vector):   
        self.percentage = self.data_inc/len(self.matrix_copy[0]) *100
        
        
        
    
    def _open_output_file(self):
        
        try:
            
            # self.output_file_handle = open(self.output_filepath, 'ab')
            # print("FILE OPENED SUCCESSFULY")
            # if self.output_file_handle == None:
            #     print("Something went wrong:")
                
            pass
          
        except Exception as e:
                      
            header = f""
            header_encoding = header.encode("utf-8")
            self.output_file_handle.write(header_encoding)
            

            self.output_file_handle = None 
        
            
    def _close_output_file(self):
        
       pass
        # if self.output_file_handle:
        #     try:
        #         self.output_file_handle.close()
        #         print("OUTPUT FILE CLOOOOOSED!!!!")
        #     except Exception as e:
        #         print(f"Error closing output file {self.output_filepath}: {e}")
        #     finally:
        #         self.output_file_handle = None
        
    def file_combination_HDF5(self,matrix,freq,s_param_magnitudes,s_param_names):
       
        # s_param_names=self._probe_controller.get_channel_names()
        # s_param_magnitudes = [] #numpy array 
        # freq = []
        
        for i in range(0,len(matrix[0])):
            
            
            for j in range(0,len(s_param_names)):
                self.HDF5FILE[f"/Coordinate_{matrix[:,i]}/{s_param_names[j]}/Frequencies"] = freq
                self.HDF5FILE[f"/Coordinate_{matrix[:,i]}/{s_param_names[j]}/Frequencies"].attrs["Magnitudes"] = s_param_magnitudes
            
        
        
       
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

    def _save_plugin_settings(self, plugin) -> None:
        """Save all settings (pre-connect and post-connect) for a plugin instance."""
        plugin_class_name = plugin.__class__.__name__

        settings_data = {
            'pre_connect': [],
            'post_connect': []
        }

        # Save pre-connect settings
        for setting in plugin.settings_pre_connect:
            settings_data['pre_connect'].append({
                'display_label': setting.display_label,
                'value': setting.get_value_as_string()
            })

        # Save post-connect settings
        for setting in plugin.settings_post_connect:
            settings_data['post_connect'].append({
                'display_label': setting.display_label,
                'value': setting.get_value_as_string()
            })

        self._plugin_settings_cache[plugin_class_name] = settings_data
        print(f"Saved settings for plugin: {plugin_class_name}")

    def _restore_plugin_settings(self, plugin) -> None:
        """Restore saved settings to a plugin instance if available."""
        plugin_class_name = plugin.__class__.__name__

        if plugin_class_name not in self._plugin_settings_cache:
            print(f"No cached settings found for plugin: {plugin_class_name}")
            return

        settings_data = self._plugin_settings_cache[plugin_class_name]

        # Restore pre-connect settings
        for i, setting in enumerate(plugin.settings_pre_connect):
            if i < len(settings_data['pre_connect']):
                cached = settings_data['pre_connect'][i]
                if setting.display_label == cached['display_label']:
                    try:
                        setting.set_value_from_string(cached['value'])
                        print(f"Restored pre-connect setting: {cached['display_label']} = {cached['value']}")
                    except Exception as e:
                        print(f"Error restoring setting {cached['display_label']}: {e}")

        # Restore post-connect settings
        for i, setting in enumerate(plugin.settings_post_connect):
            if i < len(settings_data['post_connect']):
                cached = settings_data['post_connect'][i]
                if setting.display_label == cached['display_label']:
                    try:
                        setting.set_value_from_string(cached['value'])
                        print(f"Restored post-connect setting: {cached['display_label']} = {cached['value']}")
                    except Exception as e:
                        print(f"Error restoring setting {cached['display_label']}: {e}")

        print(f"Restored settings for plugin: {plugin_class_name}")

    def swap_probe_plugin(self):
        """Swap probe plugin by reading from PluginSwitcher - preserves Scanner state and settings."""
        # Save current plugin settings before swapping
        if hasattr(self, '_probe_controller') and self._probe_controller._probe:
            self._save_plugin_settings(self._probe_controller._probe)

        # Disconnect old probe if connected
        if self._probe_controller.is_connected():
            self._probe_controller.disconnect()

        # Load the new plugin based on PluginSwitcher selection
        if PluginSwitcher.plugin_name == "":
            new_plugin = PluginSwitcher()
        else:
            plugin_module_name = f"scanner.Plugins.{PluginSwitcher.basename.replace('.py', '')}"
            try:
                plugin_module = importlib.import_module(plugin_module_name)
                plugin_class = getattr(plugin_module, PluginSwitcher.plugin_name)
                new_plugin = plugin_class()

                # Restore saved settings if available
                self._restore_plugin_settings(new_plugin)
            except (ImportError, AttributeError) as e:
                print(f"Error loading probe plugin: {e}")
                new_plugin = PluginSwitcher()

        # Create new probe controller with selected plugin
        self._probe_controller = ProbeController(new_plugin)
        print(f"Swapped to probe plugin: {new_plugin.__class__.__name__}")

    def swap_motion_plugin(self):
        """Swap motion plugin by reading from PluginSwitcherMotion - preserves Scanner state and settings."""
        # Save current plugin settings before swapping
        if hasattr(self, '_motion_controller') and self._motion_controller._driver:
            self._save_plugin_settings(self._motion_controller._driver)

        # Disconnect old motion controller if connected
        if self._motion_controller.is_connected():
            self._motion_controller.disconnect()

        # Load the new plugin based on PluginSwitcherMotion selection
        if PluginSwitcherMotion.plugin_name == "":
            new_plugin = PluginSwitcherMotion()
        else:
            motion_module_name = f"scanner.Plugins.{PluginSwitcherMotion.basename.replace('.py', '')}"
            try:
                motion_module = importlib.import_module(motion_module_name)
                motion_class = getattr(motion_module, PluginSwitcherMotion.plugin_name)
                new_plugin = motion_class()

                # Restore saved settings if available
                self._restore_plugin_settings(new_plugin)
            except (ImportError, AttributeError) as e:
                print(f"Error loading motion plugin: {e}")
                new_plugin = PluginSwitcherMotion()

        # Create new motion controller with selected plugin
        self._motion_controller = MotionController(new_plugin)
        print(f"Swapped to motion plugin: {new_plugin.__class__.__name__}")



    






