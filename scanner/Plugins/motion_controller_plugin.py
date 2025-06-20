#This plugin is for the GM215 motor 

from scanner.motion_controller import MotionControllerPlugin
from scanner.plugin_setting import PluginSettingString, PluginSettingInteger, PluginSettingFloat
import serial
from serial.tools import list_ports
import math
import time
from scanner.Plugins import geckoInstructions
import keyboard 
import threading
#stop_listener_flag = threading.Event()

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
       
        amp_val = PluginSettingFloat.get_value_as_string(self.amps)
        amp_float = float(amp_val)
        idle_percent = PluginSettingFloat.get_value_as_string(self.idle_Percent)
        idle_p_int = int(idle_percent)
        idle_time = PluginSettingFloat.get_value_as_string(self.idle_timeout)
        idle_t_float = float(idle_time)
        
        config_insn_x = geckoInstructions.ConfigureInsn(line=0,axis=0,i=amp_float,p=idle_p_int,s=idle_t_float)
        
        config_insn_y = geckoInstructions.ConfigureInsn(line=0,axis=1,i=amp_float,p=idle_p_int,s=idle_t_float)
        
        binary_x = config_insn_x.get_binary()
        binary_y = config_insn_y.get_binary()
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
        
        # Attempting to add some threadding functionality with keyboard position adjust/maybe controller later on if that seems to be useful?
        
        # listener_thread = threading.Thread(target=self.keyboard_listener_thread_function
        # listener_thread.daemon = True 
        # listener_thread.start()
    def disconnect(self):
        pass
    
    def get_axis_display_names(self):
        pass
    
    def get_axis_units(self):
        pass
    
    def set_velocity(self, velocities=None):
        
            
        
        vel=float(PluginSettingInteger.get_value_as_string(self.travel_velocity))
        pos_mult = float(PluginSettingFloat.get_value_as_string(self.position_multiplier))
        micro_mult = float(PluginSettingFloat.get_value_as_string(self.microstep_multiplier))
        
        vel_final = pos_mult*micro_mult*0.261*vel
      
        print(f"Final Velocity value: {vel_final}") 
        
        vel_int=int(vel_final)
        print(f"vel int val: \n{vel_int} \n")
        
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
        time.sleep(0.1)
        self.get_current_positions()
        time.sleep(0.1)
        
    def set_acceleration(self, accels=None):
        
        # first_pair,last_pair,axis_name,isnegative = self.low_word_generator({0:self.acceleration})
        # print(f"{first_pair,last_pair,axis_name,isnegative}")
        # last_pair_int = int(last_pair, 16)
        # first_pair_int = int(first_pair, 16)
        # #x axis
        # self.serial_port.write(bytes([0x04, 0x00, 0x00, 0x0C, last_pair_int, first_pair_int]))
        
        # #y axis 
        # self.serial_port.write(bytes([0x04, 0x00, 0x00, 0x4C, last_pair_int, first_pair_int]))
        
        acc=float(PluginSettingInteger.get_value_as_string(self.acceleration))
        pos_mult = float(PluginSettingFloat.get_value_as_string(self.position_multiplier))
        micro_mult = float(PluginSettingFloat.get_value_as_string(self.microstep_multiplier))
        
        acc_final = pos_mult*micro_mult*0.261*acc*(1/1000)
        
        print(f"Final acceleration value: {acc_final}")
        
        acc_int=int(acc_final)
        
        
        acc_command_x = geckoInstructions.AccelerationInsn(line=0, axis=0, n=acc_int)
        
        acc_command_y = geckoInstructions.AccelerationInsn(line=0, axis=1, n=acc_int)
        print(f"\n--- Setting Acceleration ---")
        print(f"Travel Velocity (self.acceleration): {acc_int}")
        binary_x = acc_command_x.get_binary()
        binary_y = acc_command_y.get_binary()
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
        
    
    def move_relative(self, move_dist):
        pass  
    
    def move_absolute(self, move_pos):
        is_negative = 0
        axis_name = ""
        raw_value = 0
        axis_num = 0
        
        if not isinstance(move_pos, dict) or not move_pos:
            print("Error: Input must be a non-empty dictionary.")
            
        
        for key, val in move_pos.items():
            raw_value = val
            if key == 0:
                axis_name = "x"
                axis_num = 0
            elif key == 1:
                axis_name = "y"
                axis_num=1
            else:
                print(f"Warning: Unexpected dictionary key '{key}'. Expected 0 for 'x' or 1 for 'y'.")
                axis_name = "unknown_axis"
                axis_num = 1
            break 

        
        if raw_value < 0:
            is_negative = -1
            raw_value = int(abs(raw_value))
        else:
            is_negative = 1
            raw_value = int(abs(raw_value))
        

        
        motion_insn = geckoInstructions.MoveInsn(line=0,axis=axis_num,relative=is_negative,n=raw_value,chain=False)
        binary_x = motion_insn.get_binary()
       
        print(f"Binary Command for X (raw int): {binary_x} ({binary_x:#010x})")
       
        # Extract individual bytes (most significant byte first for typical serial comms)
        # Assuming 32-bit unsigned integer, sent as 4 bytes: MSB to LSB
        high_first_pair = (binary_x >> 24) & 0xFF
        high_last_pair = (binary_x >> 16) & 0xFF
        low_first_pair = (binary_x >> 8) & 0xFF
        low_last_pair = binary_x & 0xFF
        
       
        
        
        print(f"\nExtracted Bytes for X:")
        print(f"  MSB: {high_first_pair:#04x}")
        print(f"  Next: {high_last_pair:#04x}")
        print(f"  Next: {low_first_pair:#04x}")
        print(f"  LSB: {low_last_pair:#04x}")

        
        
        self.serial_port.write(bytes([0x04, 0x00, high_last_pair, high_first_pair, low_last_pair, low_first_pair]))
            
        
        self.get_current_positions()
        
        
        
        # first_pair,last_pair,axis_name,isnegative = self.low_word_generator(move_pos)
        
        # print(f"{first_pair,last_pair,axis_name,isnegative}")
        # last_pair_int = int(last_pair, 16)
        # first_pair_int = int(first_pair, 16)
        
        # if axis_name == "x":
        #     if isnegative == False: 
        #         self.serial_port.write(bytes([0x04, 0x00, 0x80, 0x01, first_pair_int, last_pair_int]))
        #     else:
        #         self.serial_port.write(bytes([0x04, 0x00, 0x00, 0x01, first_pair_int, last_pair_int]))
        # if axis_name == "y":
        #     if isnegative == False: 
        #         self.serial_port.write(bytes([0x04, 0x00, 0x80, 0x41, first_pair_int, last_pair_int]))
        #     else:
        #         self.serial_port.write(bytes([0x04, 0x00, 0x00, 0x41, first_pair_int, last_pair_int]))
        
    def home(self, axes=None):
        #self.serial_port.write(bytes([0x04, 0x00, 0x00, 0x07, 0x05, 0x00]))
        
        #self.serial_port.write(bytes([0x04, 0x00, 0x00, 0x22, 0x00, 0x00, 0x00, 0x42, 0x00, 0x00]))
        
        
        #self.serial_port.write(bytes([0x04, 0x00, 0x00, 0x42, 0x00, 0x00]))
        
        # if axes =='y':
        #     self.serial_port.write(bytes([0x04, 0x00, 0x00, 0x42, 0x00, 0x00]))
        # elif axes == 'x':
        #      self.serial_port.write(bytes([0x04, 0x00, 0x00, 0x02, 0x00, 0x00]))
        pass
        
    def get_current_positions(self):
        # currently using for velocity/accel testing

        query_long_command = bytes([0x08, 0x00])
        
        self.serial_port.write(query_long_command)
        
        response = self.serial_port.read(50)
        print(f"Response: \n \n {response} \n \n")
        
    def is_moving(self):
        pass
    
    def get_endstop_minimums(self):
        pass

    
    def get_endstop_maximums(self):
        pass
    def pos_adjust(self,event):
        
        #position_adjust_insn = geckoInstructions.PositionAdjustInsn(line=0, axis=, n=1000)
        if event.event_type == keyboard.KEY_DOWN:
            if event.name == 'up':
                
                print(f"Up Arrow Pressed (Y+)")
                axis_sel = 1
                
                # In your actual motor control, you would call a function like:
                # your_motor_controller.move_y(1)
            elif event.name == 'down':
                
                print(f"Down Arrow Pressed (Y-)")
                axis_sel = 1
                # your_motor_controller.move_y(-1)
            elif event.name == 'left':
                axis_sel = 0
                print(f"Left Arrow Pressed (X-)")
                # your_motor_controller.move_x(-1)
            elif event.name == 'right':
                axis_sel = 0
                print(f"Right Arrow Pressed (X+)")
                # your_motor_controller.move_x(1)
                
            position_adjust_insn = geckoInstructions.PositionAdjustInsn(line=0, axis=axis_sel, n=1000)
            binary_x=position_adjust_insn.get_binary() 
            print(f"Binary Command for X (raw int): {binary_x} ({binary_x:#010x})")
       
            # Extract individual bytes (most significant byte first for typical serial comms)
            # Assuming 32-bit unsigned integer, sent as 4 bytes: MSB to LSB
            high_first_pair = (binary_x >> 24) & 0xFF
            high_last_pair = (binary_x >> 16) & 0xFF
            low_first_pair = (binary_x >> 8) & 0xFF
            low_last_pair = binary_x & 0xFF
            
        
            
            
            print(f"\nExtracted Bytes for X:")
            print(f"  MSB: {high_first_pair:#04x}")
            print(f"  Next: {high_last_pair:#04x}")
            print(f"  Next: {low_first_pair:#04x}")
            print(f"  LSB: {low_last_pair:#04x}")

            
            
            self.serial_port.write(bytes([0x04, 0x00, high_last_pair, high_first_pair, low_last_pair, low_first_pair]))    
            
    def keyboard_listener_thread_function(self):
        print("[Listener Thread] Starting keyboard listener...")
        # This will hook the keys and process events
        # The `suppress=True` means the key event won't be passed to other applications
        # but be careful with this, it might prevent you from typing 'esc' in the console!
        # For now, let's keep it simple without suppress for the 'esc' to work.
        keyboard.hook(self.pos_adjust)

        # We use a blocking call within the thread to keep it alive
        # We'll use a specific hotkey to set the stop flag
        keyboard.add_hotkey('esc', stop_listener_flag.set)

        # Loop until the stop_listener_flag is set
        while not stop_listener_flag.is_set():
            time.sleep(0.1) # Sleep briefly to prevent busy-waiting

        print("[Listener Thread] Keyboard listener stopping.")
        # Remove all hooks to clean up
        keyboard.unhook_all()
    # def low_word_generator(self, input_dict):
        
        
    #     # is_negative = False
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
    



