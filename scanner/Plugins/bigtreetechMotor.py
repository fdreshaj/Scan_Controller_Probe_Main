from scanner.motion_controller import MotionControllerPlugin
from scanner.plugin_setting import PluginSettingString, PluginSettingInteger, PluginSettingFloat
import serial
from serial.tools import list_ports
import pyvisa
import threading
class motion_controller_plugin(MotionControllerPlugin):
    def __init__(self):
        
        
    
        
        super().__init__()
        
        
        self.rm = None         
        self.driver = None     
        self.resource_name = None 
        self.timeout = 10000
        self.rm = pyvisa.ResourceManager()
        print("PyVISA ResourceManager initialized.")
        self.devices = self.rm.list_resources()
        
    def connect(self):
        # self.rm = None         
        # self.driver = None     
        # self.resource_name = None 
        # self.timeout = 10000
        # self.rm = pyvisa.ResourceManager()
        # print("PyVISA ResourceManager initialized.")
        # devices = self.rm.list_resources()

        # if devices:
        #     print("Found the following VISA devices:")
        #     for device in devices:
        #         print(f"- {device}")
        #     self.resource_name = devices[0] 
        #     print(f"Selected device: {self.resource_name}")
        # else:
        #     print("No VISA devices found.")
        #     self.resource_name = None
        i=0
        for device in self.devices:
            if device == "ASRL6::INSTR":
                self.resource_name = self.devices[i]
                self.driver = self.rm.open_resource(self.resource_name)
                print(f"\nSuccessfully connected to: {self.resource_name}")
            i = i+1
        # Set the timeout for read and write operations
        self.driver.timeout = self.timeout
        print(f"Communication timeout set to {self.timeout} ms.")
        response = self.send_gcode_command("G28")
        response = self.send_gcode_command("G91")
        
        
        
    def disconnect(self):
        self.driver.close()
        print(f"Connection to {self.resource_name} closed.")
        self.driver = None
    
    
    def get_axis_display_names(self) -> tuple[str, ...]:
        pass
    
    def get_axis_units(self) -> tuple[str, ...]:
        pass

    
    def set_velocity(self, velocities: dict[int, float] = None) -> None:
        pass
 
    def set_acceleration(self, accels: dict[int, float] = None) -> None:
        pass


    def move_relative(self, move_dist: dict[int, float]) -> dict[int, float] | None:
        pass

    def move_absolute(self, move_pos: dict[int, float]) -> dict[int, float] | None:
        for key, val in move_pos.items():
            raw_value = val
            if key == 0:
                
                axis_num = 0
            elif key == 1:
                
                axis_num=1
            else:
                print(f"Warning: Unexpected dictionary key '{key}'. Expected 0 for 'x' or 1 for 'y'.")
                
                axis_num = 1
            break 

        busy_command = "M114"
        if raw_value < 0:
            is_negative = -1
            raw_value = int(raw_value)
        else:
            is_negative = 1
            raw_value = int(raw_value)
        
        if axis_num == 0:
            move_string = f"X{raw_value}"
            move_command = f"G0 {move_string}"
            
        else:
            move_string = f"Y{raw_value}"
            move_command = f"G0 {move_string}" 

        self.response = self.send_gcode_command(move_command)
        # busy_bit = self.send_gcode_command(busy_command)
        # while busy_bit != 'ok':
        #     busy_bit = self.send_gcode_command(busy_command)
        
        return self.response
    def home(self, axes: list[int]) -> dict[int, float]:
        pass


    def get_current_positions(self) -> tuple[float, ...]:
        pass
 
    def is_moving(self,axis=None) -> bool:

        movement=[False,False]
        res_x = self.move_absolute({0:0})
        
        res_y = self.move_absolute({1:0})
        
        if res_x != 'ok':
            movement[0] = True
        if res_y != 'ok':
            movement[1] = True
        

        return movement
        
    def get_endstop_minimums(self) -> tuple[float, ...]:
        pass
    
    def get_endstop_maximums(self) -> tuple[float, ...]:
        pass
    
    def set_config(self, amps,idle_p, idle_time):
        pass
    
    
    def send_gcode_command(self, command):
    
        if not self.driver:
            print("Not connected to a device. Please call connect() first.")
            return None

        
        # if not command.endswith('\n'):
        #     command += '\n'

        q_response = None
        try:
            print(f"Sending G-code command: '{command.strip()}'")
          
            q_response = self.driver.query(command)
            print(f"Received response: '{q_response.strip()}'")
            return q_response.strip()

        except pyvisa.errors.VisaIOError as e:
            print(f"VISA I/O Error during command '{command.strip()}': {e}")
        except Exception as e:
            print(f"An unexpected error occurred while sending command: {e}")
        return None
    def home(self):
        response = self.send_gcode_command("G28")