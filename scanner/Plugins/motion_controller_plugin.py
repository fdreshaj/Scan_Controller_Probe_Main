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

        # Scanner type selection for boundary checking
        self.scanner_type = PluginSettingString(
            "Scanner Type",
            "N-d Scanner",
            select_options=["Big Scanner", "N-d Scanner"],
            restrict_selections=True
        )

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


        # Add scanner type as first setting
        self.add_setting_pre_connect(self.scanner_type)

        self.add_setting_pre_connect(self.motion_address)

        self.add_setting_pre_connect(self.axis_settings)

        self.add_setting_pre_connect(self.position_multiplier) #2

        self.add_setting_pre_connect(self.microstep_multiplier)

        self.add_setting_pre_connect(self.travel_velocity)

        self.add_setting_pre_connect(self.acceleration)

        self.add_setting_pre_connect(self.idle_timeout)

        self.add_setting_pre_connect(self.idle_Percent)

        self.add_setting_pre_connect(self.amps) #8

        # Position tracking variables
        self.current_position = [0.0, 0.0, 0.0]  # [X, Y, Z]
        self.is_homed = False

        # Boundary limits based on scanner type
        self.x_min = 0.0
        self.x_max = 0.0
        self.y_min = 0.0
        self.y_max = 0.0
        self.z_min = 0.0
        self.z_max = 0.0
        
        
        
        
        
    def connect(self):
        """
        Connect to GCODE motion controller with auto-detection.
        Loops through available ports until a GCODE device responds.
        """

        # Set boundary limits based on scanner type
        scanner_type_str = self.scanner_type.value
        if scanner_type_str == "Big Scanner":
            # Big Scanner: 600x600 mm (X, Y only)
            self.x_min = 0.0
            self.x_max = 600.0
            self.y_min = 0.0
            self.y_max = 600.0
            self.z_min = 0.0
            self.z_max = 0.0  # No Z axis for Big Scanner
            print("Scanner boundaries set: Big Scanner (600x600 mm, X-Y only)")
        else:  # "N-d Scanner"
            # N-d Scanner: 300x300x300 mm cube
            self.x_min = 0.0
            self.x_max = 300.0
            self.y_min = 0.0
            self.y_max = 300.0
            self.z_min = 0.0
            self.z_max = 300.0
            print("Scanner boundaries set: N-d Scanner (300x300x300 mm cube)")

        # Auto-detect GCODE device by trying all ports
        ports = [port.device for port in list_ports.comports()]

        if not ports:
            raise ConnectionError("No serial ports found on system")

        connected = False
        last_error = None

        print(f"Attempting to auto-detect GCODE device on {len(ports)} available port(s)...")

        for port_name in ports:
            try:
                print(f"  Trying {port_name}...")

                # Attempt to open serial connection
                test_serial = serial.Serial(
                    port=port_name,
                    baudrate=115200,
                    bytesize=serial.EIGHTBITS,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE,
                    timeout=1  # seconds
                )

                # Send a query command to test if it's a GCODE device
                # Query long command (0x08, 0x00) - standard GCODE status query
                test_serial.write(bytes([0x08, 0x00]))
                response = test_serial.read(22)

                # Check if we got a valid response (22 bytes expected)
                if len(response) == 22:
                    print(f"  ✓ GCODE device detected on {port_name}")
                    self.serial_port = test_serial
                    connected = True

                    # Update the motion_address setting to reflect actual connected port
                    PluginSettingString.set_value_from_string(self.motion_address, port_name)
                    break
                else:
                    # Not a GCODE device or wrong protocol
                    test_serial.close()
                    print(f"  ✗ Not a GCODE device (received {len(response)} bytes, expected 22)")

            except (serial.SerialException, OSError) as e:
                last_error = e
                print(f"  ✗ Failed to connect: {e}")
                continue

        if not connected:
            error_msg = f"Failed to detect GCODE device on any available port. Last error: {last_error}"
            print(f"✗ {error_msg}")
            raise ConnectionError(error_msg)

        print(f"✓ Successfully connected to GCODE device on {self.serial_port.port}")
       
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
        Move to absolute position with boundary checking and position tracking.

        Args:
            move_pos: Dictionary mapping axis index to target position {0: x_pos, 1: y_pos, 2: z_pos}

        Raises:
            ValueError: If movement would violate endstop boundaries
        """

        if not self.is_homed:
            raise RuntimeError("Motors must be homed before absolute movement. Call home() first.")

        if not isinstance(move_pos, dict) or not move_pos:
            raise ValueError("Error: Input must be a non-empty dictionary.")

        # Check boundaries BEFORE executing movement
        for axis_idx, target_pos in move_pos.items():
            if axis_idx == 0:  # X axis
                if target_pos < self.x_min or target_pos > self.x_max:
                    raise ValueError(
                        f"ENDSTOP VIOLATION: X-axis movement to {target_pos:.2f} mm "
                        f"exceeds boundaries [{self.x_min:.2f}, {self.x_max:.2f}] mm. "
                        f"Command stopped."
                    )
            elif axis_idx == 1:  # Y axis
                if target_pos < self.y_min or target_pos > self.y_max:
                    raise ValueError(
                        f"ENDSTOP VIOLATION: Y-axis movement to {target_pos:.2f} mm "
                        f"exceeds boundaries [{self.y_min:.2f}, {self.y_max:.2f}] mm. "
                        f"Command stopped."
                    )
            elif axis_idx == 2:  # Z axis
                if target_pos < self.z_min or target_pos > self.z_max:
                    raise ValueError(
                        f"ENDSTOP VIOLATION: Z-axis movement to {target_pos:.2f} mm "
                        f"exceeds boundaries [{self.z_min:.2f}, {self.z_max:.2f}] mm. "
                        f"Command stopped."
                    )

        pos_mult = float(PluginSettingFloat.get_value_as_string(self.position_multiplier))
        micro_mult = float(PluginSettingFloat.get_value_as_string(self.microstep_multiplier))

        # Execute movements for each axis in the dictionary
        for axis_idx, target_pos in move_pos.items():
            is_negative = 0
            raw_value = target_pos
            axis_num = axis_idx

            if axis_num not in [0, 1, 2]:
                print(f"Warning: Unexpected axis index '{axis_num}'. Skipping.")
                continue

            # Calculate relative movement from current position
            relative_movement = target_pos - self.current_position[axis_num]

            if relative_movement < 0:
                is_negative = -1
                raw_value = int(abs(relative_movement))
            else:
                is_negative = 1
                raw_value = int(abs(relative_movement))

            raw_value = int(raw_value * pos_mult * micro_mult)

            motion_insn = geckoInstructions.MoveInsn(line=0, axis=axis_num, relative=is_negative, n=raw_value, chain=False)
            binary_x = motion_insn.get_binary()

            high_first_pair = (binary_x >> 24) & 0xFF
            high_last_pair = (binary_x >> 16) & 0xFF
            low_first_pair = (binary_x >> 8) & 0xFF
            low_last_pair = binary_x & 0xFF

            self.serial_port.write(bytes([0x04, 0x00, high_last_pair, high_first_pair, low_last_pair, low_first_pair]))

            # Update tracked position
            self.current_position[axis_num] = target_pos

        print(f"Position updated: X={self.current_position[0]:.2f}, Y={self.current_position[1]:.2f}, Z={self.current_position[2]:.2f}")
        
        
        
    def home(self, axes=None):
        """
        Home the specified axes and initialize position tracking.

        After homing:
        - Big Scanner: Position is (0, 0, 0)
        - N-d Scanner: Position is (0, 0, 300) - Z starts at top

        Args:
            axes: List of axis indices to home (e.g., [0, 1, 2])
        """
        if axes is None:
            axes = [0, 1, 2]  # Home all axes by default

        print(f"Homing axes: {axes}")

        # TODO: Send actual homing commands to hardware
        # For now, assume homing completes successfully

        # Set initial position based on scanner type
        scanner_type_str = self.scanner_type.value
        if scanner_type_str == "N-d Scanner":
            # N-d Scanner: Z starts at 300 mm (top of cube)
            self.current_position = [0.0, 0.0, 300.0]
            print("Homing complete. Position initialized to (0, 0, 300) mm")
        else:
            # Big Scanner: All axes at 0
            self.current_position = [0.0, 0.0, 0.0]
            print("Homing complete. Position initialized to (0, 0, 0) mm")

        self.is_homed = True

        return {axis: self.current_position[axis] for axis in axes}

    def get_current_positions(self):
        """
        Return current tracked positions.

        Returns:
            tuple: (x, y, z) positions in mm
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
        return (self.x_min, self.y_min, self.z_min)


    def get_endstop_maximums(self):
        """Return maximum position limits for all axes."""
        return (self.x_max, self.y_max, self.z_max)
    
   
        
        