
from itertools import product
import time

from scanner.scanner import Scanner


scanner = Scanner()

try:
    scanner.motion_controller.connect()
    scanner.probe_controller.connect()

    scanner.motion_controller.set_velocity({0: 50, 1:50, 2:50})

    print(scanner.motion_controller.get_settings())
    print(scanner.probe_controller._probe.settings)

    scanner.run_scan()
finally:
    scanner.close()












