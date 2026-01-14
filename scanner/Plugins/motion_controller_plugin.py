#This plugin is for the GM215 motor 

from scanner.motion_controller import MotionControllerPlugin
from scanner.plugin_setting import PluginSettingString, PluginSettingInteger, PluginSettingFloat
import serial
from serial.tools import list_ports
from scanner.Plugins import geckoInstructions
import time
import tkinter as tk
from tkinter import messagebox

class motion_controller_plugin(MotionControllerPlugin):
    
    def __init__(self):
        super().__init__()
        
        # Scanner type selection for boundary checking (matching bigtreetechMotor.py)
        self.scanner_type = PluginSettingString(
            "Scanner Type",
            "Big Scanner",
            select_options=["Big Scanner", "N-d Scanner"],
            restrict_selections=True
        )
        self.add_setting_pre_connect(self.scanner_type)
        
        # Position tracking variables
        self.current_position = [0.0, 0.0, 0.0]  # [X, Y, Z]
        self.is_homed = False
        
        # Boundary limits based on scanner type (initialized in connect())
        self.x_min = 0.0
        self.x_max = 0.0
        self.y_min = 0.0
        self.y_max = 0.0
        self.z_min = 0.0
        self.z_max = 0.0
        
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
        self.add_setting_pre_connect(self.position_multiplier) 
        self.add_setting_pre_connect(self.microstep_multiplier)
        self.add_setting_pre_connect(self.travel_velocity)
        self.add_setting_pre_connect(self.acceleration)
        self.add_setting_pre_connect(self.idle_timeout)
        self.add_setting_pre_connect(self.idle_Percent)
        self.add_setting_pre_connect(self.amps)
        
        
    def connect(self):
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
        
        port_name = self.motion_address.value
       
        self.serial_port = serial.Serial(
            port=port_name,
            baudrate=115200,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=1  # seconds
        )
        
        amp_val = PluginSettingFloat.get_value_as_string(self.amps)
        amp_float = float(amp_val)
        idle_percent = PluginSettingFloat.get_value_as_string(self.idle_Percent)
        idle_p_int = int(idle_percent)
        idle_time = PluginSettingFloat.get_value_as_string(self.idle_timeout)
        idle_t_float = float(idle_time)
        
        config_insn_x = geckoInstructions.ConfigureInsn(line=0, axis=0, i=amp_float, p=idle_p_int, s=idle_t_float)
        config_insn_y = geckoInstructions.ConfigureInsn(line=0, axis=1, i=amp_float, p=idle_p_int, s=idle_t_float)
        
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
        
        print(f"Connected to {port_name}")
        
        
    def disconnect(self):
        self.serial_port.close()
        self.is_homed = False  # Reset homed state on disconnect
        print("Disconnected from motor controller")
    
    
    def get_axis_display_names(self):
        pass
    
    
    def get_axis_units(self):
        pass
    
    
    def set_config(self, amps, idle_p, idle_time):
        amp_float = float(amps)
        idle_p_int = int(idle_p)
        idle_t_float = float(idle_time)
        
        PluginSettingFloat.set_value_from_string(self.amps, f"{amp_float}")
        PluginSettingFloat.set_value_from_string(self.idle_Percent, f"{idle_p_int}")
        PluginSettingFloat.set_value_from_string(self.idle_timeout, f"{idle_t_float}")
        
        config_insn_x = geckoInstructions.ConfigureInsn(line=0, axis=0, i=amp_float, p=idle_p_int, s=idle_t_float)
        config_insn_y = geckoInstructions.ConfigureInsn(line=0, axis=1, i=amp_float, p=idle_p_int, s=idle_t_float)
        
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
        vel = float(PluginSettingInteger.get_value_as_string(self.travel_velocity))
        pos_mult = float(PluginSettingFloat.get_value_as_string(self.position_multiplier))
        micro_mult = float(PluginSettingFloat.get_value_as_string(self.microstep_multiplier))
        
        vel_final = pos_mult * micro_mult * 0.261 * vel
        vel_int = int(vel_final)
        
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
        if accels is None:
            acc = float(PluginSettingInteger.get_value_as_string(self.acceleration))
        else:
            acc = float(accels)
            PluginSettingFloat.set_value_from_string(self.acceleration, f"{accels}")
            
        pos_mult = float(PluginSettingFloat.get_value_as_string(self.position_multiplier))
        micro_mult = float(PluginSettingFloat.get_value_as_string(self.microstep_multiplier))
        
        acc_final = pos_mult * micro_mult * 0.261 * acc * (1/1000)
        acc_int = int(acc_final)
        
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

        self.serial_port.write(bytes([0x04, 0x00, high_last_pair_x, high_first_pair_x, low_last_pair_x, low_first_pair_x]))
        self.serial_port.write(bytes([0x04, 0x00, high_last_pair_y, high_first_pair_y, low_last_pair_y, low_first_pair_y]))
    
    
    def _check_boundary(self, axis_idx: int, target_pos: float) -> None:
        """
        Check if target position is within boundaries for the given axis.
        Raises ValueError if boundary would be violated.
        
        Args:
            axis_idx: Axis index (0=X, 1=Y, 2=Z)
            target_pos: Target position in mm
        """
        if axis_idx == 0:  # X axis
            if target_pos < self.x_min or target_pos > self.x_max:
                raise ValueError(
                    f"LIMIT VIOLATION: X-axis movement to {target_pos:.2f} mm "
                    f"exceeds boundaries [{self.x_min:.2f}, {self.x_max:.2f}] mm. "
                    f"Command stopped."
                )
        elif axis_idx == 1:  # Y axis
            if target_pos < self.y_min or target_pos > self.y_max:
                raise ValueError(
                    f"LIMIT VIOLATION: Y-axis movement to {target_pos:.2f} mm "
                    f"exceeds boundaries [{self.y_min:.2f}, {self.y_max:.2f}] mm. "
                    f"Command stopped."
                )
        elif axis_idx == 2:  # Z axis
            if target_pos < self.z_min or target_pos > self.z_max:
                raise ValueError(
                    f"LIMIT VIOLATION: Z-axis movement to {target_pos:.2f} mm "
                    f"exceeds boundaries [{self.z_min:.2f}, {self.z_max:.2f}] mm. "
                    f"Command stopped."
                )
    
    
    def move_relative(self, move_dist: dict) -> dict:
        """
        Move by a relative distance from current position.
        
        Args:
            move_dist: Dictionary mapping axis index to distance in mm
                       e.g., {0: 10.0, 1: -5.0} moves X +10mm, Y -5mm
        
        Returns:
            Dictionary of new positions after movement
        """
        if not self.is_homed:
            raise RuntimeError("Motors must be homed before movement. Call home() first.")
        
        if not isinstance(move_dist, dict) or not move_dist:
            raise ValueError("Error: Input must be a non-empty dictionary.")
        
        # Check boundaries BEFORE executing any movement
        for axis_idx, delta in move_dist.items():
            new_potential_pos = self.current_position[axis_idx] + delta
            self._check_boundary(axis_idx, new_potential_pos)
        
        # Execute movements for each axis
        pos_mult = float(PluginSettingFloat.get_value_as_string(self.position_multiplier))
        micro_mult = float(PluginSettingFloat.get_value_as_string(self.microstep_multiplier))
        
        for axis_idx, delta in move_dist.items():
            if axis_idx not in [0, 1, 2]:
                print(f"Warning: Unexpected axis index '{axis_idx}'. Skipping.")
                continue
            
            # Determine sign for relative movement
            if delta < 0:
                is_negative = -1
                raw_value = int(abs(delta))
            else:
                is_negative = 1
                raw_value = int(abs(delta))
            
            raw_value = int(raw_value * pos_mult * micro_mult)
            
            motion_insn = geckoInstructions.MoveInsn(line=0, axis=axis_idx, relative=is_negative, n=raw_value, chain=False)
            binary = motion_insn.get_binary()
            
            high_first_pair = (binary >> 24) & 0xFF
            high_last_pair = (binary >> 16) & 0xFF
            low_first_pair = (binary >> 8) & 0xFF
            low_last_pair = binary & 0xFF
            
            self.serial_port.write(bytes([0x04, 0x00, high_last_pair, high_first_pair, low_last_pair, low_first_pair]))
            
            # Wait for movement to complete
            movement = self.is_moving()
            while movement[axis_idx]:
                movement = self.is_moving()
            
            # Update tracked position
            self.current_position[axis_idx] += delta
        
        print(f"Position updated (Relative): X={self.current_position[0]:.2f}, Y={self.current_position[1]:.2f}, Z={self.current_position[2]:.2f}")
        return {i: self.current_position[i] for i in range(3)}
    
    
    def move_absolute(self, move_pos: dict) -> dict:
        """
        Move to an absolute position.
        
        Args:
            move_pos: Dictionary mapping axis index to target position in mm
                      e.g., {0: 100.0, 1: 200.0} moves to X=100mm, Y=200mm
        
        Returns:
            Dictionary of new positions after movement
        """
        if not self.is_homed:
            raise RuntimeError("Motors must be homed before absolute movement. Call home() first.")
        
        if not isinstance(move_pos, dict) or not move_pos:
            raise ValueError("Error: Input must be a non-empty dictionary.")
        
        # Check boundaries BEFORE executing any movement
        for axis_idx, target_pos in move_pos.items():
            self._check_boundary(axis_idx, target_pos)
        
        pos_mult = float(PluginSettingFloat.get_value_as_string(self.position_multiplier))
        micro_mult = float(PluginSettingFloat.get_value_as_string(self.microstep_multiplier))
        
        # Execute movements for each axis
        for axis_idx, target_pos in move_pos.items():
            if axis_idx not in [0, 1, 2]:
                print(f"Warning: Unexpected axis index '{axis_idx}'. Skipping.")
                continue
            
            # Calculate relative movement needed to reach absolute position
            delta = target_pos - self.current_position[axis_idx]
            
            if delta < 0:
                is_negative = -1
                raw_value = int(abs(delta))
            else:
                is_negative = 1
                raw_value = int(abs(delta))
            
            raw_value = int(raw_value * pos_mult * micro_mult)
            
            motion_insn = geckoInstructions.MoveInsn(line=0, axis=axis_idx, relative=is_negative, n=raw_value, chain=False)
            binary = motion_insn.get_binary()
            
            high_first_pair = (binary >> 24) & 0xFF
            high_last_pair = (binary >> 16) & 0xFF
            low_first_pair = (binary >> 8) & 0xFF
            low_last_pair = binary & 0xFF
            
            self.serial_port.write(bytes([0x04, 0x00, high_last_pair, high_first_pair, low_last_pair, low_first_pair]))
            
            # Wait for movement to complete
            movement = self.is_moving()
            while movement[axis_idx]:
                movement = self.is_moving()
            
            # Update tracked position to target
            self.current_position[axis_idx] = target_pos
        
        print(f"Position updated (Absolute): X={self.current_position[0]:.2f}, Y={self.current_position[1]:.2f}, Z={self.current_position[2]:.2f}")
        return {i: self.current_position[i] for i in range(3)}


    def home(self, axes=None):
        """
        Home the specified axes and initialize position tracking.
        
        After homing:
        - Big Scanner: Position is (0, 0, 0)
        - N-d Scanner: Position is (0, 0, 300) - Z starts at top
        
        Args:
            axes: List of axis indices to home (e.g., [0, 1, 2])
        
        Returns:
            Dictionary of homed positions
        """
        if axes is None:
            axes = [0, 1, 2]  # Home all axes by default
        
        print(f"Homing axes {axes}...")
        
        busy_bit = self.is_moving()
        while busy_bit[0] and busy_bit[1]:
            busy_bit = self.is_moving()

        temp_vel = PluginSettingInteger.get_value_as_string(self.travel_velocity)
        PluginSettingFloat.set_value_from_string(self.travel_velocity, "10")
        self.set_velocity()

        self.serial_port.write(bytes([0x04, 0x00, 0x00, 0x02, 0x00, 0x00]))

        busy_bit = self.is_moving()
        while busy_bit[0]:
            busy_bit = self.is_moving()

        self.serial_port.write(bytes([0x04, 0x00, 0x00, 0x62, 0x00, 0x00]))
        
        # Temporarily bypass homing check for initial move
        self.is_homed = True
        self.current_position = [0.0, 0.0, 0.0]  # Temporary position for boundary check
        
        # Small move to clear home switch
        pos_mult = float(PluginSettingFloat.get_value_as_string(self.position_multiplier))
        micro_mult = float(PluginSettingFloat.get_value_as_string(self.microstep_multiplier))
        raw_value = int(2 * pos_mult * micro_mult)
        
        motion_insn = geckoInstructions.MoveInsn(line=0, axis=0, relative=-1, n=raw_value, chain=False)
        binary_x = motion_insn.get_binary()
        
        high_first_pair = (binary_x >> 24) & 0xFF
        high_last_pair = (binary_x >> 16) & 0xFF
        low_first_pair = (binary_x >> 8) & 0xFF
        low_last_pair = binary_x & 0xFF
        
        self.serial_port.write(bytes([0x04, 0x00, high_last_pair, high_first_pair, low_last_pair, low_first_pair]))
        
        busy_bit = self.is_moving()
        while busy_bit[1]:
            busy_bit = self.is_moving()

        PluginSettingFloat.set_value_from_string(self.travel_velocity, f"{temp_vel}")
        self.set_velocity()
        
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


    def get_current_positions(self) -> tuple:
        """
        Return current tracked positions.
        
        Returns:
            tuple: (x, y, z) positions in mm
        """
        return tuple(self.current_position)
            
            
    def is_moving(self, axis=None) -> list:
        """
        Check if motors are currently moving.
        
        Args:
            axis: Optional specific axis to check
        
        Returns:
            List of booleans [x_moving, y_moving, z_moving]
        """
        is_moving_x = True
        is_moving_y = True
        
        query_long_command = bytes([0x08, 0x00])         
        
        self.serial_port.write(query_long_command)
        read_qlong = self.serial_port.read(22)
        self.res_qlong = list(read_qlong)
        
        busy_bits = [self.res_qlong[2], self.res_qlong[12]]
        
        # 224, 225 are values set by manufacturer
        if busy_bits[0] == 224:
            is_moving_x = False
        else:
            is_moving_x = True
            
        if busy_bits[1] == 225:
            is_moving_y = False
        else:
            is_moving_y = True
        
        movement = [is_moving_x, is_moving_y, False]
        return movement
        
         
    def get_endstop_minimums(self) -> tuple:
        """Return minimum position limits for all axes."""
        return (self.x_min, self.y_min, self.z_min)

    
    def get_endstop_maximums(self) -> tuple:
        """Return maximum position limits for all axes."""
        return (self.x_max, self.y_max, self.z_max)