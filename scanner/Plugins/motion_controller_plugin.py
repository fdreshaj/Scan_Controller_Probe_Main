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

        # Position tracking and safety state
        self.current_position = [0.0, 0.0]  # [X, Y] position tracking
        self.is_homed = False

        # Boundary limits (set based on scanner type during connect)
        self.x_min = 0.0
        self.x_max = 0.0
        self.y_min = 0.0
        self.y_max = 0.0

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

        # Scanner type selection for boundary checking
        self.scanner_type = PluginSettingString(
            "Scanner Type",
            "N-d Scanner",
            select_options=["Big Scanner", "N-d Scanner"],
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

        self.add_setting_pre_connect(self.scanner_type)

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

        # Set boundary limits based on scanner type
        scanner_type_str = self.scanner_type.value
        if scanner_type_str == "Big Scanner":
            # Big Scanner: 600x600 mm (X, Y only)
            self.x_min = 0.0
            self.x_max = 600.0
            self.y_min = 0.0
            self.y_max = 600.0
            print("Scanner boundaries set: Big Scanner (600x600 mm)")
        else:  # "N-d Scanner"
            # N-d Scanner: 300x300 mm
            self.x_min = 0.0
            self.x_max = 300.0
            self.y_min = 0.0
            self.y_max = 300.0
            print("Scanner boundaries set: N-d Scanner (300x300 mm)")
       
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
        """
        Move to an absolute position with safety checks.

        Requires homing before movement to establish coordinate system.
        Checks boundary limits before executing movement.

        Args:
            move_pos: Dictionary with axis index as key and position as value
                      e.g., {0: 100.0} for X axis, {1: 50.0} for Y axis
        """
        # Safety check: Require homing before movement
        if not self.is_homed:
            raise RuntimeError("Motors must be homed before movement. Call home() first.")

        if not isinstance(move_pos, dict) or not move_pos:
            raise ValueError("Error: Input must be a non-empty dictionary.")

        pos_mult = float(PluginSettingFloat.get_value_as_string(self.position_multiplier))
        micro_mult = float(PluginSettingFloat.get_value_as_string(self.microstep_multiplier))

        # Process each axis movement
        for axis_num, target_pos in move_pos.items():
            if axis_num not in [0, 1]:
                print(f"Warning: Unexpected axis index '{axis_num}'. Expected 0 for X or 1 for Y.")
                continue

            # Safety check: Boundary validation
            if axis_num == 0:  # X axis
                if target_pos < self.x_min or target_pos > self.x_max:
                    raise ValueError(
                        f"LIMIT VIOLATION: X-axis movement to {target_pos:.2f} mm "
                        f"exceeds boundaries [{self.x_min:.2f}, {self.x_max:.2f}] mm. "
                        f"Command stopped."
                    )
            elif axis_num == 1:  # Y axis
                if target_pos < self.y_min or target_pos > self.y_max:
                    raise ValueError(
                        f"LIMIT VIOLATION: Y-axis movement to {target_pos:.2f} mm "
                        f"exceeds boundaries [{self.y_min:.2f}, {self.y_max:.2f}] mm. "
                        f"Command stopped."
                    )

            # Calculate relative movement from current position
            delta = target_pos - self.current_position[axis_num]

            # Determine sign for relative movement
            if delta < 0:
                is_negative = -1
                raw_value = int(abs(delta))
            else:
                is_negative = 1
                raw_value = int(abs(delta))

            # Apply position and microstep multipliers
            raw_value = int(raw_value * pos_mult * micro_mult)

            # Create and send move instruction
            motion_insn = geckoInstructions.MoveInsn(line=0, axis=axis_num, relative=is_negative, n=raw_value, chain=False)
            binary = motion_insn.get_binary()

            high_first_pair = (binary >> 24) & 0xFF
            high_last_pair = (binary >> 16) & 0xFF
            low_first_pair = (binary >> 8) & 0xFF
            low_last_pair = binary & 0xFF

            self.serial_port.write(bytes([0x04, 0x00, high_last_pair, high_first_pair, low_last_pair, low_first_pair]))

            # Update tracked position after sending command
            self.current_position[axis_num] = target_pos

        print(f"Position updated: X={self.current_position[0]:.2f}, Y={self.current_position[1]:.2f}")
        
        
        
    def home(self, axes=None):
        """
        Home the XY axes simultaneously using the chain feature.

        The chain bit allows multiple axes to start homing at the same time.
        X axis is sent with chain=True, Y axis with chain=False (last in sequence).

        After homing, position is initialized to (0, 0).
        """
        print("Homing XY axes simultaneously...")

        # Create HOME instruction for X axis with chain=True (to chain with Y)
        home_insn_x = geckoInstructions.HomeInsn(line=0, axis=0, chain=True)
        # Create HOME instruction for Y axis with chain=False (last in sequence)
        home_insn_y = geckoInstructions.HomeInsn(line=0, axis=1, chain=False)

        binary_x = home_insn_x.get_binary()
        binary_y = home_insn_y.get_binary()

        # Extract bytes for X axis (little endian formatting)
        high_first_pair_x = (binary_x >> 24) & 0xFF
        high_last_pair_x = (binary_x >> 16) & 0xFF
        low_first_pair_x = (binary_x >> 8) & 0xFF
        low_last_pair_x = binary_x & 0xFF

        # Extract bytes for Y axis (little endian formatting)
        high_first_pair_y = (binary_y >> 24) & 0xFF
        high_last_pair_y = (binary_y >> 16) & 0xFF
        low_first_pair_y = (binary_y >> 8) & 0xFF
        low_last_pair_y = binary_y & 0xFF

        # Send both HOME commands (X chained, then Y to complete the chain)
        self.serial_port.write(bytes([0x04, 0x00, high_last_pair_x, high_first_pair_x, low_last_pair_x, low_first_pair_x]))
        self.serial_port.write(bytes([0x04, 0x00, high_last_pair_y, high_first_pair_y, low_last_pair_y, low_first_pair_y]))

        print(f"HOME X (chained): {binary_x:#010x}")
        print(f"HOME Y: {binary_y:#010x}")

        # Wait for homing to complete
        movement = self.is_moving()
        while movement[0] or movement[1]:
            movement = self.is_moving()

        # Initialize position to origin after homing
        self.current_position = [0.0, 0.0]
        self.is_homed = True

        print("Homing complete. Position initialized to (0.0, 0.0)")
        return {0: 0.0, 1: 0.0}
        
    def get_current_positions(self):
        """
        Return current tracked positions.

        Returns:
            tuple: (x, y) positions in mm
        """
        return tuple(self.current_position)
        
                
            
    def is_moving(self,axis=None):
        
        is_moving_x = True
        is_moving_y = True
        
        query_long_command = bytes([0x08, 0x00])         
        
        
        self.serial_port.write(query_long_command)
        
        read_qlong = self.serial_port.read(22)
        
        self.res_qlong = list(read_qlong)
        
        busy_bits= [self.res_qlong[2],self.res_qlong[12]]
        
        # 224,225 are values set by manufacturer
        
        if busy_bits[0] == 224:
            is_moving_x = False
        else:
            is_moving_x = True
            
        if busy_bits[1] == 225:
            is_moving_y = False
        else:
            is_moving_y = True
        
        movement = [is_moving_x,is_moving_y]
        return movement
        
         
    def get_endstop_minimums(self):
        """Return minimum position limits for all axes."""
        return (self.x_min, self.y_min)

    def get_endstop_maximums(self):
        """Return maximum position limits for all axes."""
        return (self.x_max, self.y_max)
    
   
        
        