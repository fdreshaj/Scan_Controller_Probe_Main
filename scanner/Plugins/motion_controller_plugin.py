
from scanner.motion_controller import MotionControllerPlugin
from scanner.plugin_setting import PluginSettingString, PluginSettingInteger, PluginSettingFloat

class motion_controller_plugin(MotionControllerPlugin):
    
    def __init__(self):
        
        super().__init__()
        self.motion = None
    
    def connect(self):
        pass  
      
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
        pass
    
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
        
    