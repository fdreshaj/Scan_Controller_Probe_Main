
from itertools import product
import time

from scanner.plugin_setting import PluginSetting

from scanner.motion_controller import MotionController
from scanner.probe_controller import ProbeController

from scanner.gcode_simulator import GcodeSimulator
from scanner.probe_simulator import ProbeSimulator
from scanner.VNA_Plugin import VNAProbePlugin
from scanner.plugin_switcher import PluginSwitcher
import csv
import globals

class Scanner():
    _motion_controller: MotionController
    _probe_controller: ProbeController
    
    
    def __init__(self, motion_controller: MotionController | None = None, probe_controller: ProbeController | None = None) -> None:
        if motion_controller is None:
            self._motion_controller = MotionController(GcodeSimulator())
        else:
            self._motion_controller = motion_controller
        
        if probe_controller is None:
            if globals.value_flag == "initial":

                self._probe_controller = ProbeController(PluginSwitcher())
            elif globals.value_flag == "VNA MS46524B":
                self._probe_controller = ProbeController(VNAProbePlugin())
            elif globals.value_flag == "VNA 37397C":
                pass #### Add the plugins by their global the value names here, don't forget to update the Plugin Switcher settings and Test Scanner GUI connection settings 
                     #### set_configuration_settings is the relevant method in test scanner gui file 
            elif globals.value_flag == "ETC ...":
                pass
        else:
            if globals.value_flag == "initial":

                self._probe_controller = ProbeController(PluginSwitcher())
            elif globals.value_flag == "VNA MS46524B":
                self._probe_controller = ProbeController(VNAProbePlugin())

    def run_scan(self) -> None:
        scan_xy = [(float(x) - 20, float(40 - y if x%20==10 else y) - 20) for x,y in product(range(0, 50, 10), repeat=2)]

        start = time.time()
        for (i, (x, y)) in enumerate(scan_xy):
            self._motion_controller.move_absolute({0:x, 1:y})
            if i == 0:
                self._probe_controller.scan_begin()
            else:
                self._probe_controller.scan_read_measurement(i - 1, (x, y))

            while self._motion_controller.is_moving():
                time.sleep(0.001)

            self._probe_controller.scan_trigger_and_wait(i, (x, y))
        
        self._motion_controller.move_absolute({0:0, 1:0})
        sdata = self._probe_controller.scan_read_measurement(len(scan_xy), (x, y))
        self._probe_controller.scan_end()
        freqs = self._probe_controller.get_xaxis_coords() 
        with open("vna_sparams.csv", "w", newline="") as csvfile:
            writer = csv.writer(csvfile)
            # header: Freq, then for each channel Real,Imag
            header = ["Frequency(Hz)"]
            for name in sdata:
                header += [f"{name}_Re", f"{name}_Im"]
            writer.writerow(header)

            # assume all channels have same length as freqs
            N = len(freqs)
            for i in range(N):
                row = [freqs[i]]
                for pts in sdata.values():
                    c = pts[i]
                    row += [c.real, c.imag]
                writer.writerow(row)

        print(f"Total time elapsed: {time.time() - start} seconds.")

    def close(self) -> None:
        self._motion_controller.disconnect()
        self._probe_controller.disconnect()
    
    @property
    def motion_controller(self) -> MotionController:
        return self._motion_controller
    
    @property
    def probe_controller(self) -> ProbeController:
        return self._probe_controller










