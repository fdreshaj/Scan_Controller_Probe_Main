# Fixed plugin for the GM215 motor 
from scanner.motion_controller import MotionControllerPlugin
from scanner.plugin_setting import PluginSettingString, PluginSettingInteger, PluginSettingFloat
import serial
from serial.tools import list_ports
from scanner.Plugins import geckoInstructions
import time

class motion_controller_plugin(MotionControllerPlugin):
    
    def __init__(self):
        super().__init__()
        
        self.scanner_type = PluginSettingString(
            "Scanner Type",
            "Big Scanner",
            select_options=["Big Scanner", "N-d Scanner"],
            restrict_selections=True
        )
        self.add_setting_pre_connect(self.scanner_type)
        
        self.current_position = [0.0, 0.0, 0.0]
        self.is_homed = False
        
        # Boundaries initialized to 0
        self.x_min = self.x_max = 0.0
        self.y_min = self.y_max = 0.0
        self.z_min = self.z_max = 0.0
        
        ports = [port.device for port in list_ports.comports()]
        if not ports: ports = ["NO_PORTS_FOUND"]
        
        self.motion_address = PluginSettingString("Select Address", ports[0], select_options=ports, restrict_selections=True)
        self.axis_settings = PluginSettingString("Choose Axis","X",select_options=["X","Y","Z","W"],restrict_selections=True)
        self.position_multiplier = PluginSettingFloat("Position Multiplier",39.4)
        self.microstep_multiplier = PluginSettingFloat("Microstep Multiplier", 10)
        self.travel_velocity = PluginSettingInteger("Travel Velocity",50)
        self.acceleration = PluginSettingFloat("Acceleration",100)
        self.idle_timeout = PluginSettingFloat("0-25.5s",2.5)
        self.idle_Percent = PluginSettingFloat("0-99",25)
        self.amps = PluginSettingFloat("Amps 0-7",3)
        
        # Register settings
        for setting in [self.motion_address, self.axis_settings, self.position_multiplier, 
                        self.microstep_multiplier, self.travel_velocity, self.acceleration, 
                        self.idle_timeout, self.idle_Percent, self.amps]:
            self.add_setting_pre_connect(setting)
        
    def connect(self):
        # SYNCED WITH BIGTREETECH: Set boundary limits
        scanner_type_str = self.scanner_type.value
        if scanner_type_str == "Big Scanner":
            self.x_min, self.x_max = 0.0, 600.0
            self.y_min, self.y_max = 0.0, 600.0
            self.z_min, self.z_max = 0.0, 0.0
        else:
            self.x_min, self.x_max = 0.0, 300.0
            self.y_min, self.y_max = 0.0, 300.0
            self.z_min, self.z_max = 0.0, 300.0
        
        port_name = self.motion_address.value
        self.serial_port = serial.Serial(port=port_name, baudrate=115200, timeout=1)
        
        # Initialize motor config (Current/Idle settings)
        self.set_config(self.amps.value, self.idle_Percent.value, self.idle_timeout.value)
        print(f"Connected to {port_name}")

    def _check_limit_violation(self, axis_idx, new_pos):
        """Standardized safety check matching BigTreeTech logic."""
        limits = [(self.x_min, self.x_max), (self.y_min, self.y_max), (self.z_min, self.z_max)]
        axis_names = ["X", "Y", "Z"]
        min_lim, max_lim = limits[axis_idx]
        
        if new_pos < min_lim or new_pos > max_lim:
            raise ValueError(f"LIMIT VIOLATION: {axis_names[axis_idx]} move to {new_pos:.2f} "
                             f"exceeds [{min_lim}, {max_lim}]")

    def move_relative(self, move_dist: dict) -> dict:
        if not self.is_homed:
            raise RuntimeError("Motors must be homed before movement.")
        
        # 1. Validate all boundaries first (Safety First)
        for axis_idx, delta in move_dist.items():
            new_pos = self.current_position[axis_idx] + delta
            self._check_limit_violation(axis_idx, new_pos)
        
        # 2. Execute movement
        pos_mult = float(self.position_multiplier.value)
        micro_mult = float(self.microstep_multiplier.value)
        
        for axis_idx, delta in move_dist.items():
            is_negative = -1 if delta < 0 else 1
            raw_steps = int(abs(delta) * pos_mult * micro_mult)
            
            motion_insn = geckoInstructions.MoveInsn(line=0, axis=axis_idx, relative=is_negative, n=raw_steps, chain=False)
            self._send_binary_cmd(motion_insn.get_binary())
            
            # Wait for specific axis to stop
            while self.is_moving()[axis_idx]:
                time.sleep(0.01)
            
            self.current_position[axis_idx] += delta
            
        return {i: self.current_position[i] for i in range(3)}

    def move_absolute(self, move_pos: dict) -> dict:
        """Converts absolute request to relative steps for the Gecko controller."""
        relative_map = {}
        for axis_idx, target_pos in move_pos.items():
            relative_map[axis_idx] = target_pos - self.current_position[axis_idx]
        
        return self.move_relative(relative_map)

    def home(self, axes=None):
        print("Homing axes...")
        # Reset homed status during the process
        busy_bit = self.is_moving()
        while busy_bit[0] and busy_bit[1] == True:
            busy_bit = self.is_moving()
            
        self.is_homed = False
        
        # 1. Set slow homing velocity
        original_vel = self.travel_velocity.value
        self.travel_velocity.value = 10
        self.set_velocity()

        # 2. Send Homing Command (Gecko specific)
        self.serial_port.write(bytes([0x04, 0x00, 0x00, 0x02, 0x00, 0x00])) # X
        busy_bit = self.is_moving()
        while busy_bit[0] == True:
            busy_bit = self.is_moving()
            
        self.serial_port.write(bytes([0x04, 0x00, 0x00, 0x62, 0x00, 0x00])) # Y
        self.is_homed = True
        self.move_absolute({0:-2})
        
        busy_bit = self.is_moving()
        while busy_bit[1] == True:
            busy_bit = self.is_moving()

        # 3. Post-Home Position Initialization (Logic sync with Ground Truth)
        if self.scanner_type.value == "N-d Scanner":
            self.current_position = [0.0, 0.0, 300.0]
        else:
            self.current_position = [0.0, 0.0, 0.0]
            
        # 4. Restore velocity
        self.travel_velocity.value = original_vel
        self.set_velocity()
        
        self.is_homed = True
        return {i: self.current_position[i] for i in range(3)}

    def _send_binary_cmd(self, binary_val):
        """Helper to handle Gecko 4-byte packet wrapping."""
        h1 = (binary_val >> 24) & 0xFF
        h2 = (binary_val >> 16) & 0xFF
        l1 = (binary_val >> 8) & 0xFF
        l2 = binary_val & 0xFF
        
        self.serial_port.write(bytes([0x04, 0x00, h2, h1, l2, l1]))

    def disconnect(self):
        self.serial_port.close()
        self.is_homed = False