#This plugin is for the GM215 motor 

from scanner.motion_controller import MotionControllerPlugin
from scanner.plugin_setting import PluginSettingString, PluginSettingInteger, PluginSettingFloat
import serial
from serial.tools import list_ports

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
        
        self.position_multiplier = PluginSettingFloat("Position Multiplier",0)
        
        self.microstep_multiplier = PluginSettingFloat("Microstep Multiplier", 0)
        
        self.travel_velocity = PluginSettingFloat("Travel Velocity",0)
        
        self.acceleration = PluginSettingFloat("Acceleration",0)
        
        self.idle_timeout = PluginSettingFloat("0-25.5s",0)
        
        self.idle_Percent = PluginSettingFloat("0-99",0)
        
        self.amps = PluginSettingFloat("Amps 0-7",0)
        
        
        
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
        # Command to get the version: 0x04 0x00 0x0E 0x00
        version_command = bytes([0x0E, 0x00]) # Updated command
        
        run_command = bytes([0x04, 0x00])
        
        # X_config_command = bytes([0xE01, 0X00])
        
        # x_command = bytes([0x03E8, 0X2180]) # x+1000 command
        
        query_short_command = bytes([0x08, 0x00])
        
        #self.serial_port.write(query_short_command)
        self.serial_port.write(bytes([0x04,0x00,0xD4,0x60,0x14,0x00 ])) #+20 Y axis
        #
        #self.serial_port.write(bytes([0x04,0x00,0x14,0x00,0x14,0x00])) #move +20 X axis
        
        #move -20 [0x04,0x00,0x14,0x01,0x14,0x00]
        
        #self.serial_port.write(run_command)    
            
        # response = self.serial_port.read(22)
        # print(response)
        
        ### HIGH  0000000000010100  LOW 0000000000010100
        ### HIGH 14 LOW 14 
        
    def disconnect(self):
        pass
    
    def get_axis_display_names(self):
        pass
    
    def get_axis_units(self):
        pass
    
    def set_velocity(self, velocities):
        pass
    
    def set_acceleration(self, accels):
        pass
    
    def move_relative(self, move_dist):
        pass #Move command 
    
    def move_absolute(self, move_pos):
        pass
    
    def home(self, axes):
        pass
    
    def get_current_positions(self):
        pass
    
    def is_moving(self):
        pass
    
    def get_endstop_minimums(self):
        pass

    
    def get_endstop_maximums(self):
        pass
        
            # EXAMPLE 1:   BASIC POINT TO POINT MOTION 
            #     x_config: 
            #     x configure: 1 amps, idle at 50% after 1 seconds 
            #     x limit cw 12000000 
            #     x offset 1000 
            #     y_config: 
            #     y configure: 1.5 amps, idle at 50% after 1 seconds 
            #     y limit cw 12000000 
            #     y offset 1000 
            #     start: 
            #     x acceleration 512  
            #     x velocity 1000  
            #     y acceleration 512 
            #     y velocity 1000 
            #     home x, y   
            #     analog inputs to {0}  
            #     vector axis are {0}  
            #     x acceleration 128  
            #     x velocity 8000  
            #     y acceleration 128   
            #     y velocity 8000 
            #     motion1: 
            #     x+10000, y+10000 
            #     x-10000, y-10000 
            #     goto motion1                           
            #     34 
            #     ; NO AXIS USING ANALOG   
            #     ; NO AXIS USING VECTOR 
            #     ; RUN ACCELERATION 
            #     ; RUN VELOCITY 
            #     ; REPEAT. INFINITE LOOP 
            #     ; GO HOME ACCELERATION 
            #     ; GO HOME VELOCITY 
            #     ; X & Y GO HOME SIMULTANEOUSLY 
            #     ; NO AXIS USING ANALOG   
            #     ; NO AXIS USING VECTOR 
            #     ; RUN ACCELERATION 
            #     ; RUN VELOCITY 
            #     ; REPEAT. INFINITE LOOP 



            # EXAMPLE 2:  BASIC VECTOR MOTION 
            #     x_config: 
            #     x configure: 1 amps, idle at 50% after 1 seconds 
            #     x limit cw 12000000 
            #     x offset 1000   
            #     y_config: 
            #     y configure: 1 amps, idle at 50% after 1 seconds 
            #     y limit cw 12000000 
            #     y offset 1000 
            #     start: 
            #     x acceleration 512  
            #     x velocity 1000  
            #     y acceleration 512 
            #     y velocity 1000 
            #     home x, y   
            #     vector axis are x, y                 
            #     x acceleration 128 
            #     y acceleration 128 
            #     x velocity 8000                 
            #     y velocity 4000 
            #     motion1: 
            #     x+10000, y+10000     
            #     x-10000, y-10000     
            #     goto motion1  
            #     ; GO HOME ACCELERATION 
            #     ; GO HOME VELOCITY 
            #     ; X & Y GO HOME SIMULTANEOUSLY 
            #     ; X & Y AXIS VECTOR MOTION 
            #     ; SET DIFFERENT VELOCITY FOR TESTING 
            #     ; INFINITE LOOP
            
            