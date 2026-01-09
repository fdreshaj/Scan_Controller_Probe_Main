from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGraphicsView, QGraphicsScene, QHBoxLayout,
    QPushButton, QLabel, QComboBox
)
from PySide6.QtCore import Qt, QTimer, QRectF
from PySide6.QtGui import (
    QPen, QPainter, QBrush, QColor, QLinearGradient, QFont
)
import h5py
import numpy as np


class VisualizerWindow(QWidget):
    
    def __init__(self, hdf5_filepath):
        super().__init__(None)
        self.setWindowTitle("Real-Time Scan Visualizer")
        self.resize(800, 700)
        
        self.hdf5_filepath = hdf5_filepath
        self.last_point_read = 0
        self.all_data = []
        self.all_x = []
        self.all_y = []
        self.frequencies = None
        self.freq_index = 0  # Which frequency to display
        
        # Setup UI
        self.setup_ui()
        
        # Setup timer for updating
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_visualization)
        self.timer.start(500)  # Update every 500ms
        
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # Top control bar
        control_layout = QHBoxLayout()
        
        self.status_label = QLabel("Waiting for data...")
        self.status_label.setFont(QFont("Arial", 10))
        control_layout.addWidget(self.status_label)
        
        control_layout.addStretch()
        
        # Frequency selector
        freq_label = QLabel("Frequency:")
        control_layout.addWidget(freq_label)
        
        self.freq_combo = QComboBox()
        self.freq_combo.currentIndexChanged.connect(self.on_frequency_changed)
        control_layout.addWidget(self.freq_combo)
        
        # Colormap selector
        colormap_label = QLabel("Colormap:")
        control_layout.addWidget(colormap_label)
        
        self.colormap_combo = QComboBox()
        self.colormap_combo.addItems(["Jet", "Viridis", "Hot", "Cool", "Grayscale"])
        self.colormap_combo.currentTextChanged.connect(self.redraw_data)
        control_layout.addWidget(self.colormap_combo)
        
        layout.addLayout(control_layout)
        
        # Graphics view
        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.Antialiasing)
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        layout.addWidget(self.view)
        
        # Bottom info bar
        info_layout = QHBoxLayout()
        self.points_label = QLabel("Points: 0")
        self.min_label = QLabel("Min: --")
        self.max_label = QLabel("Max: --")
        info_layout.addWidget(self.points_label)
        info_layout.addStretch()
        info_layout.addWidget(self.min_label)
        info_layout.addWidget(self.max_label)
        layout.addLayout(info_layout)
        
        self.setLayout(layout)
        
    def update_visualization(self):
        """Read new data from HDF5 file and update visualization"""
        try:
            with h5py.File(self.hdf5_filepath, 'r') as hf:
                # Read frequencies if not loaded
                if self.frequencies is None:
                    if '/Frequencies/Range' in hf:
                        self.frequencies = hf['/Frequencies/Range'][:]
                        self.populate_frequency_combo()
                
                # Check if data exists
                if '/Data/S11_real' not in hf:
                    return
                
                # Get current number of points
                current_num_points = hf['/Data/S11_real'].shape[0]
                
                # Read new data if available
                if current_num_points > self.last_point_read:
                    # Read new points
                    s11_real = hf['/Data/S11_real'][self.last_point_read:current_num_points, :]
                    s11_imag = hf['/Data/S11_imag'][self.last_point_read:current_num_points, :]
                    s11_complex = s11_real + 1j * s11_imag
                    
                    # Read coordinates
                    x_coords = hf['/Coords/x_data'][self.last_point_read:current_num_points]
                    y_coords = hf['/Coords/y_data'][self.last_point_read:current_num_points]
                    
                    # Append to stored data
                    if len(self.all_data) == 0:
                        self.all_data = s11_complex
                        self.all_x = x_coords
                        self.all_y = y_coords
                    else:
                        self.all_data = np.vstack([self.all_data, s11_complex])
                        self.all_x = np.concatenate([self.all_x, x_coords])
                        self.all_y = np.concatenate([self.all_y, y_coords])
                    
                    self.last_point_read = current_num_points
                    
                    # Update visualization
                    self.redraw_data()
                    
                    # Update status
                    self.status_label.setText(f"Live: {current_num_points} points scanned")
                    self.points_label.setText(f"Points: {current_num_points}")
                    
        except Exception as e:
            self.status_label.setText(f"Error: {str(e)}")
    
    def populate_frequency_combo(self):
        """Populate frequency dropdown"""
        if self.frequencies is not None:
            self.freq_combo.clear()
            for i, freq in enumerate(self.frequencies):
                freq_ghz = freq / 1e9
                self.freq_combo.addItem(f"{freq_ghz:.3f} GHz", i)
    
    def on_frequency_changed(self, index):
        """Handle frequency selection change"""
        if index >= 0:
            self.freq_index = self.freq_combo.currentData()
            self.redraw_data()
    
    def redraw_data(self):
        """Redraw all data points"""
        if len(self.all_data) == 0:
            return
        
        self.scene.clear()
        
        # Get data at selected frequency
        freq_data = self.all_data[:, self.freq_index]
        magnitudes = np.abs(freq_data)
        
        if len(magnitudes) == 0:
            return
        
        # Calculate bounds
        x_min, x_max = self.all_x.min(), self.all_x.max()
        y_min, y_max = self.all_y.min(), self.all_y.max()
        
        # Add padding
        padding = 20
        x_range = x_max - x_min if x_max != x_min else 1
        y_range = y_max - y_min if y_max != y_min else 1
        
        # Scale factor
        view_width = self.view.width() - 2 * padding
        view_height = self.view.height() - 2 * padding
        scale = min(view_width / x_range, view_height / y_range)
        
        # Normalize magnitudes for color mapping
        mag_min, mag_max = magnitudes.min(), magnitudes.max()
        if mag_max > mag_min:
            normalized_mags = (magnitudes - mag_min) / (mag_max - mag_min)
        else:
            normalized_mags = np.zeros_like(magnitudes)
        
        # Update min/max labels
        self.min_label.setText(f"Min: {mag_min:.4f}")
        self.max_label.setText(f"Max: {mag_max:.4f}")
        
        # Draw points
        point_size = 8
        for i in range(len(self.all_x)):
            x_scaled = (self.all_x[i] - x_min) * scale + padding
            y_scaled = (self.all_y[i] - y_min) * scale + padding
            
            # Get color based on magnitude
            color = self.get_color(normalized_mags[i])
            
            # Draw point
            self.scene.addEllipse(
                x_scaled - point_size/2,
                y_scaled - point_size/2,
                point_size,
                point_size,
                QPen(Qt.NoPen),
                QBrush(color)
            )
        
        # Draw scan path
        if len(self.all_x) > 1:
            pen = QPen(QColor(100, 100, 100, 100), 1, Qt.DashLine)
            for i in range(len(self.all_x) - 1):
                x1 = (self.all_x[i] - x_min) * scale + padding
                y1 = (self.all_y[i] - y_min) * scale + padding
                x2 = (self.all_x[i+1] - x_min) * scale + padding
                y2 = (self.all_y[i+1] - y_min) * scale + padding
                self.scene.addLine(x1, y1, x2, y2, pen)
        
        # Fit view
        self.view.setSceneRect(self.scene.itemsBoundingRect())
    
    def get_color(self, value):
        """Get color for normalized value (0-1) based on selected colormap"""
        colormap = self.colormap_combo.currentText()
        
        if colormap == "Jet":
            # Classic jet colormap
            if value < 0.25:
                r, g, b = 0, int(255 * value / 0.25), 255
            elif value < 0.5:
                r, g, b = 0, 255, int(255 * (0.5 - value) / 0.25)
            elif value < 0.75:
                r, g, b = int(255 * (value - 0.5) / 0.25), 255, 0
            else:
                r, g, b = 255, int(255 * (1 - value) / 0.25), 0
        
        elif colormap == "Viridis":
            # Approximate viridis
            r = int(255 * (0.267 + 0.005 * value))
            g = int(255 * (0.005 + 0.570 * value))
            b = int(255 * (0.329 + 0.528 * value))
        
        elif colormap == "Hot":
            # Hot colormap
            if value < 0.33:
                r, g, b = int(255 * value / 0.33), 0, 0
            elif value < 0.67:
                r, g, b = 255, int(255 * (value - 0.33) / 0.34), 0
            else:
                r, g, b = 255, 255, int(255 * (value - 0.67) / 0.33)
        
        elif colormap == "Cool":
            # Cool colormap
            r = int(255 * value)
            g = int(255 * (1 - value))
            b = 255
        
        else:  # Grayscale
            gray = int(255 * value)
            r, g, b = gray, gray, gray
        
        return QColor(r, g, b)
    
    def closeEvent(self, event):
        """Clean up when window is closed"""
        self.timer.stop()
        event.accept()

if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication, QFileDialog
    import sys
    
    app = QApplication(sys.argv)
    
    # Open file dialog to select HDF5 file
    hdf5_file, _ = QFileDialog.getOpenFileName(
        None,
        "Select HDF5 Scan File",
        "",
        "HDF5 Files (*.hdf5 *.h5);;All Files (*)"
    )
    
    if hdf5_file:
        window = VisualizerWindow(hdf5_file)
        window.show()
        sys.exit(app.exec())
    else:
        print("No file selected, exiting...")
        sys.exit(0)