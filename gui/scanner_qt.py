
from PySide6.QtCore import QObject, Signal, Slot

from scanner.scanner import Scanner

class ScannerQt(QObject):
    current_position_x = Signal(float)
    current_position_y = Signal(float)
    current_position_z = Signal(float)
    is_moving = Signal(bool)

    xy_move: float
    z_move: float
    
    scanner: Scanner

    def __init__(self, signal_scope=None) -> None:
        super().__init__()

        self.xy_move = 0.0
        self.z_move = 0.0

        self.scanner = Scanner(signal_scope=signal_scope)

    def close(self) -> None:
        print("!!!!!!!!!!!!!!!!!!!!!! Closing Qt Scanner Object !!!!!!!!!!!!!!!!!!!!!!")
        self.scanner.close()

    @Slot()
    def update_motion(self) -> None:
        """Update position display after movement commands."""
        if self.scanner.motion_controller.is_connected():
            try:
                positions = self.scanner.motion_controller.get_current_positions()
                for pos, signal in zip(positions, (self.current_position_x, self.current_position_y, self.current_position_z)):
                    signal.emit(pos)
            except Exception as e:
                print(f"Error updating motion positions: {e}")


    @Slot(float)
    def set_xy_move(self, move_amount: float) -> None:
        self.xy_move = move_amount

    @Slot(float)
    def set_z_move(self, move_amount: float) -> None:
        self.z_move = move_amount

    @Slot()
    def clicked_move_x_plus(self):
        self.scanner.motion_controller.move_relative({0:self.xy_move})
        self.update_motion()

    @Slot()
    def clicked_move_x_minus(self):
        self.scanner.motion_controller.move_relative({0:-self.xy_move})
        self.update_motion()

    @Slot()
    def clicked_move_y_plus(self):
        self.scanner.motion_controller.move_relative({1:self.xy_move})
        self.update_motion()

    @Slot()
    def clicked_move_y_minus(self):
        self.scanner.motion_controller.move_relative({1:-self.xy_move})
        self.update_motion()

    @Slot()
    def clicked_move_z_plus(self):
        self.scanner.motion_controller.move_relative({2:self.z_move})
        self.update_motion()

    @Slot()
    def clicked_move_z_minus(self):
        self.scanner.motion_controller.move_relative({2:-self.z_move})
        self.update_motion()










