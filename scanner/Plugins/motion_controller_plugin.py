#This plugin is for the GM215 motor 

from scanner.motion_controller import MotionControllerPlugin
from scanner.plugin_setting import PluginSettingString, PluginSettingInteger, PluginSettingFloat
import serial
from serial.tools import list_ports
import math
import time
from scanner.Plugins import geckoInstructions


class motion_controller_plugin(MotionControllerPlugin):
    
    def __init__(self):
        
        
        # TODO: # error in error out settings  and Serial Port IN Serial Port OUT connection settings 
        
        
        super().__init__()
        
        ports = [port.device for port in list_ports.comports()]
        
        
        # self.motionInsn = geckoInstructions.MoveInsn()
        
        # self.velocityInsn = geckoInstructions.VelocityInsn()
        
        # self.accelerationInsn = geckoInstructions.AccelerationInsn()
        
        # self.configInsn = geckoInstructions.ConfigureInsn()
        
        # self.homeInsn = geckoInstructions.HomeInsn()
        
        for port in list_ports.comports():
            print(f"Found: {port.device}")
        if not ports:
            ports = ["NO_PORTS_FOUND"]
        # PluginSettingString with options
        self.motion_address = PluginSettingString(
            "Select Address", 
            ports[0],
            select_options=ports,
            restrict_selections=True
        )
        
        self.axis_settings = PluginSettingString("Choose Axis","X",select_options=["X","Y","Z","W"],restrict_selections=True)
        
        self.position_multiplier = PluginSettingFloat("Position Multiplier",39.4)
        
        self.microstep_multiplier = PluginSettingFloat("Microstep Multiplier", 10)
        
        self.travel_velocity = PluginSettingInteger("Travel Velocity",50)
        
        self.acceleration = PluginSettingFloat("Acceleration",100)
        
        self.idle_timeout = PluginSettingFloat("0-25.5s",2.5)
        
        self.idle_Percent = PluginSettingFloat("0-99",25)
        
        self.amps = PluginSettingFloat("Amps 0-7",3)
        
        
        
        self.add_setting_pre_connect(self.motion_address)
        
        self.add_setting_pre_connect(self.axis_settings)
        
        self.add_setting_pre_connect(self.position_multiplier)
        
        self.add_setting_pre_connect(self.microstep_multiplier)
        
        self.add_setting_pre_connect(self.travel_velocity)
        
        self.add_setting_pre_connect(self.acceleration)
        
        self.add_setting_pre_connect(self.idle_timeout)
        
        self.add_setting_pre_connect(self.idle_Percent)
        
        self.add_setting_pre_connect(self.amps)
        
        
        
        
        
    def connect(self):
        
        port_name = self.motion_address.value
        # Configure the serial port as per the manual: 115200 baud, 8 data bits, no parity, 1 stop bit
        self.serial_port = serial.Serial(
            port=port_name,
            baudrate=115200,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=1 # Read timeout in seconds
        )
       
       
        #self.serial_port.write(bytes([0x04, 0x00, 0x00, 0x41, 0x00, 0x0A])) # -20 Y axis
        
        
        #self.serial_port.write(bytes([0x04, 0x00, 0x00, 0x01, 0x00, 0x0A])) #-20 x
        
        
        #self.serial_port.write(bytes([0x04, 0x00, 0x80, 0x01, 0x00, 0x0A])) # +20 x
        
        
        #self.serial_port.write(bytes([0x04, 0x00, 0x80, 0x41, 0x00, 0x0A])) # +20Y
        

        
    def disconnect(self):
        pass
    
    def get_axis_display_names(self):
        pass
    
    def get_axis_units(self):
        pass
    
    def set_velocity(self, velocities=None):
        
      
        
        vel=PluginSettingInteger.get_value_as_string(self.travel_velocity)
        vel_int=int(vel)
        
        
        velocity_command_x = geckoInstructions.VelocityInsn(line=0, axis=0, n=vel_int)
        
        velocity_command_y = geckoInstructions.VelocityInsn(line=0, axis=1, n=vel_int)
        print(f"\n--- Setting Velocity ---")
        print(f"Travel Velocity (self.travel_velocity): {vel_int}")
        binary_x = velocity_command_x.get_binary()
        binary_y = velocity_command_y.get_binary()
        print(f"Binary Command for X (raw int): {binary_x} ({binary_x:#010x})")
        print(f"Binary Command for Y (raw int): {binary_y} ({binary_y:#010x})")
        # Extract individual bytes (most significant byte first for typical serial comms)
        # Assuming 32-bit unsigned integer, sent as 4 bytes: MSB to LSB
        high_first_pair_x = (binary_x >> 24) & 0xFF
        high_last_pair_x = (binary_x >> 16) & 0xFF
        low_first_pair_x = (binary_x >> 8) & 0xFF
        low_last_pair_x = binary_x & 0xFF
        
        high_first_pair_y = (binary_y >> 24) & 0xFF
        high_last_pair_y = (binary_y >> 16) & 0xFF
        low_first_pair_y = (binary_y >> 8) & 0xFF
        low_last_pair_y = binary_y & 0xFF
        
        
        print(f"\nExtracted Bytes for X:")
        print(f"  MSB: {high_first_pair_x:#04x}")
        print(f"  Next: {high_last_pair_x:#04x}")
        print(f"  Next: {low_first_pair_x:#04x}")
        print(f"  LSB: {low_last_pair_x:#04x}")

        print(f"\nExtracted Bytes for Y:")
        print(f"  MSB: {high_first_pair_y:#04x}")
        print(f"  Next: {high_last_pair_y:#04x}")
        print(f"  Next: {low_first_pair_y:#04x}")
        print(f"  LSB: {low_last_pair_y:#04x}")

        self.serial_port.write(bytes([0x04, 0x00, high_last_pair_x, high_first_pair_x, low_last_pair_x, low_first_pair_x]))
        
        
        self.serial_port.write(bytes([0x04, 0x00, high_last_pair_y, high_first_pair_y, low_last_pair_y, low_first_pair_y]))
        
    
    def set_acceleration(self, accels):
        
        first_pair,last_pair,axis_name,isnegative = self.low_word_generator({0:self.acceleration})
        print(f"{first_pair,last_pair,axis_name,isnegative}")
        last_pair_int = int(last_pair, 16)
        first_pair_int = int(first_pair, 16)
        #x axis
        self.serial_port.write(bytes([0x04, 0x00, 0x00, 0x0C, last_pair_int, first_pair_int]))
        
        #y axis 
        self.serial_port.write(bytes([0x04, 0x00, 0x00, 0x4C, last_pair_int, first_pair_int]))
        
    
    def move_relative(self, move_dist):
        pass  
    
    def move_absolute(self, move_pos):
        first_pair,last_pair,axis_name,isnegative = self.low_word_generator(move_pos)
        
        print(f"{first_pair,last_pair,axis_name,isnegative}")
        last_pair_int = int(last_pair, 16)
        first_pair_int = int(first_pair, 16)
        
        if axis_name == "x":
            if isnegative == False: 
                self.serial_port.write(bytes([0x04, 0x00, 0x80, 0x01, last_pair_int, first_pair_int]))
            else:
                self.serial_port.write(bytes([0x04, 0x00, 0x00, 0x01, last_pair_int, first_pair_int]))
        if axis_name == "y":
            if isnegative == False: 
                self.serial_port.write(bytes([0x04, 0x00, 0x80, 0x41, last_pair_int, first_pair_int]))
            else:
                self.serial_port.write(bytes([0x04, 0x00, 0x00, 0x41, last_pair_int, first_pair_int]))
                
    def home(self, axes=None):
        #self.serial_port.write(bytes([0x04, 0x00, 0x00, 0x07, 0x05, 0x00]))
        
        self.serial_port.write(bytes([0x04, 0x00, 0x00, 0x22, 0x00, 0x00, 0x00, 0x42, 0x00, 0x00]))
        
        
        #self.serial_port.write(bytes([0x04, 0x00, 0x00, 0x42, 0x00, 0x00]))
        
        # if axes =='y':
        #     self.serial_port.write(bytes([0x04, 0x00, 0x00, 0x42, 0x00, 0x00]))
        # elif axes == 'x':
        #      self.serial_port.write(bytes([0x04, 0x00, 0x00, 0x02, 0x00, 0x00]))
        
        
    def get_current_positions(self):
        pass
    
    def is_moving(self):
        pass
    
    def get_endstop_minimums(self):
        pass

    
    def get_endstop_maximums(self):
        pass
    
    
    # def low_word_generator(self, input_dict):
        
    #     is_negative = False
    #     axis_name = ""
    #     raw_value = None

    #     if not isinstance(input_dict, dict) or not input_dict:
    #         print("Error: Input must be a non-empty dictionary.")
    #         return None, None, None, None

    #     # Extract the key-value pair and determine axis_name
    #     for key, val in input_dict.items():
    #         raw_value = val
    #         if key == 0:
    #             axis_name = "x"
    #         elif key == 1:
    #             axis_name = "y"
    #         else:
    #             print(f"Warning: Unexpected dictionary key '{key}'. Expected 0 for 'x' or 1 for 'y'.")
    #             axis_name = "unknown_axis"
    #         break # Process only the first item

    #     # Convert to positive if negative, and set the is_negative flag
    #     if raw_value is not None and raw_value < 0:
    #         is_negative = True
    #         raw_value = abs(raw_value)

    #     try:
    #         # Attempt to convert the raw value to an integer.
    #         # Floats will be truncated (e.g., 10.5 becomes 10).
    #         value = int(raw_value)
    #     except (ValueError, TypeError):
    #         print(f"Error: Could not convert '{raw_value}' to an integer. Please provide a numeric value.")
    #         return None, None, axis_name, is_negative

    #     # Max 255 value due to highest 8-bit representation (after integer conversion)
    #     if not (0 <= value <= 255):
    #         print(f"Error: Extracted value ({value}) must be between 0 and 255 after conversion to integer.")
    #         return None, None, axis_name, is_negative

    #     # Convert value to 8-bit binary, padded to 8 digits (as per your original code)
    #     binary_8_bit = bin(value)[2:].zfill(8)

    #     # Append 8 zeroes on the right to the 8-bit value (as per your original code)
    #     binary_16_bit = binary_8_bit + '00000000'

    #     # Translate the full binary value into hexadecimal
    #     hex_value = hex(int(binary_16_bit, 2))[2:]

    #     # Append zeroes to hex if not 4 digits
    #     hex_4_digits = hex_value.zfill(4)

    #     # Split the hex into first and last pair
    #     first_pair = hex_4_digits[:2]
    #     last_pair = hex_4_digits[2:]

    #     return first_pair, last_pair, axis_name, is_negative
    



