#This plugin is for the GM215 motor 

from scanner.motion_controller import MotionControllerPlugin
from scanner.plugin_setting import PluginSettingString, PluginSettingInteger, PluginSettingFloat
import serial
from serial.tools import list_ports
from scanner.Plugins import geckoInstructions


class motion_controller_plugin(MotionControllerPlugin):
    
    def __init__(self):
        
        
        # TODO: # error in error out settings  and Serial Port IN Serial Port OUT connection settings 
        
        
        super().__init__()
        
        ports = [port.device for port in list_ports.comports()]
        
        
        
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
        
        self.add_setting_pre_connect(self.position_multiplier) #2
        
        self.add_setting_pre_connect(self.microstep_multiplier)
        
        self.add_setting_pre_connect(self.travel_velocity)
        
        self.add_setting_pre_connect(self.acceleration)
        
        self.add_setting_pre_connect(self.idle_timeout)
        
        self.add_setting_pre_connect(self.idle_Percent)
        
        self.add_setting_pre_connect(self.amps) #8
        
        
        
        
        
    def connect(self):
        
        port_name = self.motion_address.value
       
        self.serial_port = serial.Serial(
            port=port_name,
            baudrate=115200,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=1 #seconds
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

        high_first_pair_x = (binary_x >> 24) & 0xFF
        high_last_pair_x = (binary_x >> 16) & 0xFF
        low_first_pair_x = (binary_x >> 8) & 0xFF
        low_last_pair_x = binary_x & 0xFF
        
        high_first_pair_y = (binary_y >> 24) & 0xFF
        high_last_pair_y = (binary_y >> 16) & 0xFF
        low_first_pair_y = (binary_y >> 8) & 0xFF
        low_last_pair_y = binary_y & 0xFF
        

        self.serial_port.write(bytes([0x04, 0x00, high_last_pair_x, high_first_pair_x, low_last_pair_x, low_first_pair_x]))
        
        
        self.serial_port.write(bytes([0x04, 0x00, high_last_pair_y, high_first_pair_y, low_last_pair_y, low_first_pair_y]))
        
    def disconnect(self):
        self.serial_port.close
    
    def get_axis_display_names(self):
        pass
    
    def get_axis_units(self):
        pass
    
    def set_config(self, amps,idle_p, idle_time):
        
        amp_float = float(amps)
       
        idle_p_int = int(idle_p)
        
        idle_t_float = float(idle_time)
        
        PluginSettingFloat.set_value_from_string(self.amps, f"{amp_float}")
        PluginSettingFloat.set_value_from_string(self.idle_Percent, f"{idle_p_int}")
        PluginSettingFloat.set_value_from_string(self.idle_timeout, f"{idle_t_float}")
        
        
        config_insn_x = geckoInstructions.ConfigureInsn(line=0,axis=0,i=amp_float,p=idle_p_int,s=idle_t_float)
        
        config_insn_y = geckoInstructions.ConfigureInsn(line=0,axis=1,i=amp_float,p=idle_p_int,s=idle_t_float)
        
        binary_x = config_insn_x.get_binary()
        binary_y = config_insn_y.get_binary()

        high_first_pair_x = (binary_x >> 24) & 0xFF
        high_last_pair_x = (binary_x >> 16) & 0xFF
        low_first_pair_x = (binary_x >> 8) & 0xFF
        low_last_pair_x = binary_x & 0xFF
        
        high_first_pair_y = (binary_y >> 24) & 0xFF
        high_last_pair_y = (binary_y >> 16) & 0xFF
        low_first_pair_y = (binary_y >> 8) & 0xFF
        low_last_pair_y = binary_y & 0xFF
        

        self.serial_port.write(bytes([0x04, 0x00, high_last_pair_x, high_first_pair_x, low_last_pair_x, low_first_pair_x]))
        
        
        self.serial_port.write(bytes([0x04, 0x00, high_last_pair_y, high_first_pair_y, low_last_pair_y, low_first_pair_y]))
        
        
        
    def set_velocity(self, velocities=None):
        
       
        vel=float(PluginSettingInteger.get_value_as_string(self.travel_velocity))
        pos_mult = float(PluginSettingFloat.get_value_as_string(self.position_multiplier))
        micro_mult = float(PluginSettingFloat.get_value_as_string(self.microstep_multiplier))
        
        vel_final = pos_mult*micro_mult*0.261*vel
        
        vel_int=int(vel_final)
        
        
        velocity_command_x = geckoInstructions.VelocityInsn(line=0, axis=0, n=vel_int)
        
        velocity_command_y = geckoInstructions.VelocityInsn(line=0, axis=1, n=vel_int)
        
        binary_x = velocity_command_x.get_binary()
        binary_y = velocity_command_y.get_binary()
        

        high_first_pair_x = (binary_x >> 24) & 0xFF
        high_last_pair_x = (binary_x >> 16) & 0xFF
        low_first_pair_x = (binary_x >> 8) & 0xFF
        low_last_pair_x = binary_x & 0xFF
        
        high_first_pair_y = (binary_y >> 24) & 0xFF
        high_last_pair_y = (binary_y >> 16) & 0xFF
        low_first_pair_y = (binary_y >> 8) & 0xFF
        low_last_pair_y = binary_y & 0xFF
        
        
        self.serial_port.write(bytes([0x04, 0x00, high_last_pair_x, high_first_pair_x, low_last_pair_x, low_first_pair_x]))
        
        
        self.serial_port.write(bytes([0x04, 0x00, high_last_pair_y, high_first_pair_y, low_last_pair_y, low_first_pair_y]))
       
        
    
    def set_acceleration(self, accels=None):
        
        
        
        if accels == None:
            acc=float(PluginSettingInteger.get_value_as_string(self.acceleration))
        else:
            acc = float(accels)
            PluginSettingFloat.set_value_from_string(self.acceleration, f"{accels}")
            
        pos_mult = float(PluginSettingFloat.get_value_as_string(self.position_multiplier))
        micro_mult = float(PluginSettingFloat.get_value_as_string(self.microstep_multiplier))
        
        acc_final = pos_mult*micro_mult*0.261*acc*(1/1000)

        acc_int=int(acc_final)
        
        
        acc_command_x = geckoInstructions.AccelerationInsn(line=0, axis=0, n=acc_int)
        
        acc_command_y = geckoInstructions.AccelerationInsn(line=0, axis=1, n=acc_int)
        
        binary_x = acc_command_x.get_binary()
        binary_y = acc_command_y.get_binary()
        
        high_first_pair_x = (binary_x >> 24) & 0xFF
        high_last_pair_x = (binary_x >> 16) & 0xFF
        low_first_pair_x = (binary_x >> 8) & 0xFF
        low_last_pair_x = binary_x & 0xFF
        
        high_first_pair_y = (binary_y >> 24) & 0xFF
        high_last_pair_y = (binary_y >> 16) & 0xFF
        low_first_pair_y = (binary_y >> 8) & 0xFF
        low_last_pair_y = binary_y & 0xFF

        # swapping first and last h/l pairs due to little endian formatting
        
        self.serial_port.write(bytes([0x04, 0x00, high_last_pair_x, high_first_pair_x, low_last_pair_x, low_first_pair_x]))
        
        
        self.serial_port.write(bytes([0x04, 0x00, high_last_pair_y, high_first_pair_y, low_last_pair_y, low_first_pair_y]))
        
    
    def move_relative(self, move_dist):
        pass  
    
    def move_absolute(self, move_pos):
       
       
       
        pos_mult = float(PluginSettingFloat.get_value_as_string(self.position_multiplier))
        micro_mult = float(PluginSettingFloat.get_value_as_string(self.microstep_multiplier))
        
        is_negative = 0
        
        raw_value = 0
        axis_num = 0
        
        if not isinstance(move_pos, dict) or not move_pos:
            print("Error: Input must be a non-empty dictionary.")
            
        
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

        
        if raw_value < 0:
            is_negative = -1
            raw_value = int(abs(raw_value))
        else:
            is_negative = 1
            raw_value = int(abs(raw_value))
        
        
        
        raw_value = int(raw_value*pos_mult*micro_mult)
        
        motion_insn = geckoInstructions.MoveInsn(line=0,axis=axis_num,relative=is_negative,n=raw_value,chain=False)
        binary_x = motion_insn.get_binary()
    
        high_first_pair = (binary_x >> 24) & 0xFF
        high_last_pair = (binary_x >> 16) & 0xFF
        low_first_pair = (binary_x >> 8) & 0xFF
        low_last_pair = binary_x & 0xFF
        
        self.serial_port.write(bytes([0x04, 0x00, high_last_pair, high_first_pair, low_last_pair, low_first_pair]))
        
        
        
    def home(self, axes=None):
        pass
        
    def get_current_positions(self):
      
        query_long_command = bytes([0x08, 0x00])
        
        self.serial_port.write(query_long_command)
        
        response = self.serial_port.read(22)
        print(f"Response: \n \n { response } \n \n")
        
        self.tokens = list(response)
        print(self.tokens)
        
        print(f"Position {self.tokens[8],self.tokens[9],self.tokens[10]}")
        
                
            
    def is_moving(self):
        
        query_long_command = bytes([0x08, 0x00])         
        
        
        self.serial_port.write(query_long_command)
        
        read_qlong = self.serial_port.read(22)
        
        self.res_qlong = list(read_qlong)
        
        busy_bits= [self.res_qlong[2],self.res_qlong[12]]
        
        print(busy_bits)
        
        return busy_bits
        
         
    def get_endstop_minimums(self):
        pass

    
    def get_endstop_maximums(self):
        pass
    
   
        
        