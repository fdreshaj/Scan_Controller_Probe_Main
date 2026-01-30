#### SAR implementation from HDF5 file data
import h5py
import numpy as np
import sys
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGraphicsView, QGraphicsScene, QHBoxLayout,
    QPushButton, QLabel, QComboBox, QFileDialog, QApplication, QDoubleSpinBox
)
from PySide6.QtCore import Qt

class sar_window(QWidget):
    def __init__(self):
        super().__init__(None)
        self.setWindowTitle("SAR Implementation from HDF5")
        self.resize(1200, 850)
        
        # Physical Constants
        self.c = 299792458.0 
        
        # Data variables
        self.X = None
        self.Y = None
        self.Z = None
        self.F = None
        self.data = None 
        self.current_file = None
        
        self.setup_ui()

    def setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.control_layout = QHBoxLayout()
        
        # File Loading
        self.import_btn = QPushButton("📁 Load HDF5")
        self.import_btn.clicked.connect(self.import_new_file)
        self.control_layout.addWidget(self.import_btn)
        
        # S-parameter selector
        self.control_layout.addWidget(QLabel("S-Parameter:"))
        self.sparam_combo = QComboBox()
        self.sparam_combo.currentIndexChanged.connect(self.load_data_from_file)
        self.control_layout.addWidget(self.sparam_combo)

        # R (Range) Input
        self.control_layout.addWidget(QLabel("R (m):"))
        self.r_input = QDoubleSpinBox()
        self.r_input.setRange(0.001, 100.0)
        self.r_input.setValue(1.0)
        self.r_input.setDecimals(3)
        self.control_layout.addWidget(self.r_input)

        # ε_r Input
        self.control_layout.addWidget(QLabel("\u03B5\u1d63:")) 
        self.er_input = QDoubleSpinBox()
        self.er_input.setRange(1.0, 100.0)
        self.er_input.setValue(1.0)
        self.control_layout.addWidget(self.er_input)
        
        # Calculate Button
        self.calc_btn = QPushButton("Calculate & Save")
        self.calc_btn.setStyleSheet("background-color: #2ecc71; color: white; font-weight: bold;")
        self.calc_btn.clicked.connect(self.run_calculation)
        self.control_layout.addWidget(self.calc_btn)
        
        self.control_layout.addStretch()
        self.main_layout.addLayout(self.control_layout)
        
        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene)
        self.main_layout.addWidget(self.view)

    def import_new_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select HDF5", "", "h5 Files (*.h5 *.hdf5)")
        if file_path:
            self.current_file = file_path
            self.discover_sparams(file_path)

    def discover_sparams(self, file_path):
        """Discovers S-params using consistent SWMR flags."""
        try:
            with h5py.File(file_path, 'r', libver='latest', swmr=True) as hf:
                if '/Data' in hf:
                    keys = hf['/Data'].keys()
                    sparams = sorted(list(set(k.replace('_real', '').replace('_imag', '') for k in keys)))
                    self.sparam_combo.clear()
                    self.sparam_combo.addItems(sparams)
        except Exception as e:
            print(f"Discovery Error: {e}")

    def load_data_from_file(self):
        if not self.current_file: return
        sparam = self.sparam_combo.currentText()
        if not sparam: return

        try:
            with h5py.File(self.current_file, 'r', libver='latest', swmr=True) as hf:
                # Load spatial and frequency vectors
                self.F = hf['/Frequencies/Range'][:] if '/Frequencies/Range' in hf else None
                self.X = hf['/Coords/x_data'][:] if '/Coords/x_data' in hf else None
                self.Y = hf['/Coords/y_data'][:] if '/Coords/y_data' in hf else None
                self.Z = hf['/Coords/z_data'][:] if '/Coords/z_data' in hf else np.zeros_like(self.X)

                # Load Complex Data
                r_path, i_path = f'/Data/{sparam}_real', f'/Data/{sparam}_imag'
                if r_path in hf and i_path in hf:
                    self.data = hf[r_path][:] + 1j * hf[i_path][:]
                print(f"Loaded {sparam} successfully.")
        except Exception as e:
            print(f"Load Error: {e}")

    def run_calculation(self):
        if self.data is None:
            print("No data loaded.")
            return

        R = self.r_input.value()
        Er = self.er_input.value()
        
        # Prepare output container (same shape as input data)
        processed_data = np.zeros_like(self.data, dtype=complex)
        
        num_points = len(self.X)
        num_freqs = len(self.F)

        print(f"Calculating SAR for R={R}...")

        # Spatial Loop
        for i in range(num_points):
            # Frequency Loop
            for j in range(num_freqs):
                freq = self.F[j]
                
                # 1. Initialize k (wavenumber)
                # k = 2 * pi * f * sqrt(er) / c
                k = (2 * np.pi * freq * np.sqrt(Er)) / self.c
                
                # 2. Extract original complex value
                original_val = self.data[i, j]
                
                # 3. Compute SAR processed value
                # formula: val * e^(j*2*k*R) / R^2
                phase_term = np.exp(1j * 2 * k * R)
                processed_data[i, j] = (original_val * phase_term) / (R**2)

        self.save_to_hdf5(R, Er, processed_data)

    def save_to_hdf5(self, R, Er, sar_results):
        """Creates a new HDF5 file and saves the SAR result."""
        out_name = "SAR_Output.h5"
        group_name = f"R_{str(R).replace('.', '_')}"
        
        try:
            # 'a' mode: append if exists, create if not
            with h5py.File(out_name, 'a') as hf:
                # Remove existing group if recalculating same R
                if group_name in hf:
                    del hf[group_name]
                
                grp = hf.create_group(group_name)
                grp.attrs['R_value'] = R
                grp.attrs['E_r'] = Er
                
                # Save the processed complex data (split into real/imag for compatibility)
                grp.create_dataset("sar_real", data=np.real(sar_results), compression="gzip")
                grp.create_dataset("sar_imag", data=np.imag(sar_results), compression="gzip")
                
                # Save coordinates for reference
                grp.create_dataset("x", data=self.X)
                grp.create_dataset("y", data=self.Y)
                
            print(f"Results saved to {out_name} under group {group_name}")
        except Exception as e:
            print(f"Save Error: {e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = sar_window()
    window.show()
    sys.exit(app.exec())