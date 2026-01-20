#### SAR implementation from HDF5 file data
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGraphicsView, QGraphicsScene, QHBoxLayout,
    QPushButton, QLabel, QComboBox
)
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QFileDialog, QApplication, QDoubleSpinBox, QMessageBox
)
from PySide6.QtCore import Qt, QTimer, QRectF
from PySide6.QtGui import (
    QPen, QPainter, QBrush, QColor, QLinearGradient, QFont
)
import h5py
import numpy as np
import sys

class sar_window(QWidget):
    def __init__(self):
        super().__init__(None)
        self.setWindowTitle("SAR Implementation from HDF5")
        self.resize(1200, 850)
        
        self.setup_ui()

    def setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.control_layout = QHBoxLayout()
        
        self.import_btn = QPushButton("📁 Load HDF5")
        self.import_btn.clicked.connect(self.import_new_file)
        self.control_layout.addWidget(self.import_btn)
        self.control_layout.addStretch()
        self.main_layout.addLayout(self.control_layout)
        
        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.Antialiasing)
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.main_layout.addWidget(self.view)
        
        
        
    def import_new_file(self):
        file, _ = QFileDialog.getOpenFileName(self, "Select HDF5 S Parameter file", "", "h5 Files (*.h5 *.hdf5);;All Files (*)")
       
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = sar_window()
    window.show()
    sys.exit(app.exec())