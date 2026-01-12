#############
###############
# S-Parameter Visualizer 
############### FIXED: Real-time updating now works continuously
#############


from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGraphicsView, QGraphicsScene, QHBoxLayout,
    QPushButton, QLabel, QComboBox, QGraphicsPixmapItem, QSlider
)
from PySide6.QtCore import Qt, QTimer, QRectF
from PySide6.QtGui import (
    QPen, QPainter, QBrush, QColor, QLinearGradient, QFont, QImage, QPixmap
)
import h5py
import numpy as np

class ZoomableGraphicsView(QGraphicsView):
    """Custom QGraphicsView with mouse wheel zoom"""
    
    def __init__(self, scene):
        super().__init__(scene)
        self.zoom_factor = 1.15
        self.min_zoom = 0.1
        self.max_zoom = 10.0
        self.current_zoom = 1.0
    
    def wheelEvent(self, event):
        """Handle mouse wheel for zooming"""
        # Get the wheel delta (positive = zoom in, negative = zoom out)
        delta = event.angleDelta().y()
        
        if delta > 0:
            # Zoom in
            factor = self.zoom_factor
            new_zoom = self.current_zoom * factor
            
            if new_zoom <= self.max_zoom:
                self.scale(factor, factor)
                self.current_zoom = new_zoom
        else:
            # Zoom out
            factor = 1.0 / self.zoom_factor
            new_zoom = self.current_zoom * factor
            
            if new_zoom >= self.min_zoom:
                self.scale(factor, factor)
                self.current_zoom = new_zoom
        
        event.accept()
    
    def reset_zoom(self):
        """Reset zoom to 1:1"""
        self.resetTransform()
        self.current_zoom = 1.0

class VisualizerWindow(QWidget):
    
    def __init__(self, hdf5_filepath):
        super().__init__(None)
        self.setWindowTitle("Real-Time Scan Visualizer")
        self.resize(900, 800)
        
        self.hdf5_filepath = hdf5_filepath
        self.last_point_read = 0
        self.all_data = {}  # Dictionary to store data for each S-parameter
        self.all_x = []
        self.all_y = []
        self.frequencies = None
        self.freq_index = 0
        self.total_points_expected = None
        self.available_sparams = []
        self.current_sparam = None
        
        # Grid parameters
        self.grid_x = None
        self.grid_y = None
        self.is_uniform = False
        
        # Animation parameters
        self.is_playing = False
        self.play_timer = QTimer()
        self.play_timer.timeout.connect(self.play_next_frame)
        self.play_speed = 0.05  # ms per frame
        
        # Setup UI
        self.setup_ui()
        
        # Do initial read to get metadata
        self.initial_setup()
        
        # Setup timer for updating - ALWAYS runs to check for changes
        self.timer = QTimer()
        self.timer.timeout.connect(self.check_for_updates)
        self.timer.start(500)  # Check every 500ms
        
        # Do initial visualization
        self.update_visualization()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # Top control bar
        control_layout = QHBoxLayout()
        
        # Import button
        self.import_button = QPushButton("📁")
        self.import_button.clicked.connect(self.import_new_file)
        control_layout.addWidget(self.import_button)
        
        self.status_label = QLabel("Waiting for data...")
        self.status_label.setFont(QFont("Arial", 10))
        control_layout.addWidget(self.status_label)
        
        control_layout.addStretch()
        
        # S-parameter selector
        sparam_label = QLabel("S-Parameter:")
        control_layout.addWidget(sparam_label)
        
        self.sparam_combo = QComboBox()
        self.sparam_combo.currentTextChanged.connect(self.on_sparam_changed)
        control_layout.addWidget(self.sparam_combo)
        
        # Data type selector
        datatype_label = QLabel("Display:")
        control_layout.addWidget(datatype_label)
        
        self.datatype_combo = QComboBox()
        self.datatype_combo.addItems(["Magnitude", "Phase", "Real", "Imaginary"])
        self.datatype_combo.currentTextChanged.connect(self.redraw_data)
        control_layout.addWidget(self.datatype_combo)
        
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
        self.view = ZoomableGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.Antialiasing)
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.view.setDragMode(QGraphicsView.ScrollHandDrag)  # Enable drag to pan
        self.view.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)  # Zoom at mouse cursor
        layout.addWidget(self.view)
        
        
        # Frequency slider section
        freq_slider_layout = QVBoxLayout()
        
        # Frequency label
        freq_label_layout = QHBoxLayout()
        freq_label_layout.addWidget(QLabel("Frequency:"))
        self.freq_value_label = QLabel("--")
        self.freq_value_label.setFont(QFont("Arial", 10, QFont.Bold))
        freq_label_layout.addWidget(self.freq_value_label)
        freq_label_layout.addStretch()
        freq_slider_layout.addLayout(freq_label_layout)
        
        # Slider with play button
        slider_control_layout = QHBoxLayout()
        
        self.freq_slider = QSlider(Qt.Horizontal)
        self.freq_slider.setMinimum(0)
        self.freq_slider.setMaximum(0)
        self.freq_slider.setValue(0)
        self.freq_slider.setTickPosition(QSlider.TicksBelow)
        self.freq_slider.setTickInterval(10)
        self.freq_slider.valueChanged.connect(self.on_slider_changed)
        slider_control_layout.addWidget(self.freq_slider)
        
        # Play/Pause button
        self.play_button = QPushButton("▶ Play")
        self.play_button.setFixedWidth(80)
        self.play_button.clicked.connect(self.toggle_play)
        self.play_button.setEnabled(False)  # Disabled until data loads
        slider_control_layout.addWidget(self.play_button)
        
        freq_slider_layout.addLayout(slider_control_layout)
        
        layout.addLayout(freq_slider_layout)
        
        # Bottom info bar
        info_layout = QHBoxLayout()
        self.points_label = QLabel("Points: 0")
        self.grid_label = QLabel("Grid: --")
        self.min_label = QLabel("Min: --")
        self.max_label = QLabel("Max: --")
        info_layout.addWidget(self.points_label)
        info_layout.addWidget(self.grid_label)
        info_layout.addStretch()
        info_layout.addWidget(self.min_label)
        info_layout.addWidget(self.max_label)
        layout.addLayout(info_layout)
        
        self.setLayout(layout)
    
    def toggle_play(self):
        """Toggle play/pause for frequency animation"""
        if self.is_playing:
            # Stop playing
            self.is_playing = False
            self.play_timer.stop()
            self.play_button.setText("▶ Play")
        else:
            # Start playing
            self.is_playing = True
            self.play_timer.start(self.play_speed)
            self.play_button.setText("⏸ Pause")
    
    def play_next_frame(self):
        """Advance to next frequency frame"""
        if self.frequencies is None:
            return
        
        # Advance to next frequency
        next_index = self.freq_index + 1
        
        # Loop back to start if at end
        if next_index >= len(self.frequencies):
            next_index = 0
        
        # Update slider (this will trigger redraw)
        self.freq_slider.setValue(next_index)
    
    def initial_setup(self):
        """Initial setup - read metadata and discover S-parameters"""
        try:
            with h5py.File(self.hdf5_filepath, 'r', libver='latest', swmr=True) as hf:
                # Try to read expected number of points
                if 'numPoints' in hf.attrs:
                    self.total_points_expected = int(hf.attrs['numPoints'])
                
                # Check if uniform
                if 'wasUniform' in hf.attrs:
                    was_uniform_raw = hf.attrs['wasUniform']
                    if isinstance(was_uniform_raw, (str, bytes)):
                        self.is_uniform = str(was_uniform_raw).lower() in ['true', '1']
                    else:
                        self.is_uniform = bool(was_uniform_raw)
                
                # Discover available S-parameters
                self.discover_sparameters()
                        
        except Exception as e:
            print(f"Error in initial setup: {e}")
    
    def check_for_updates(self):
        """Check for new data and update if needed"""
        # Always call update_visualization - it will check internally
        # if there's actually new data to display.
        # We can't rely on file size/mtime for zero-padded HDF5 files.
        self.update_visualization()
    
    def discover_sparameters(self):
        """Discover available S-parameters in the HDF5 file"""
        try:
            with h5py.File(self.hdf5_filepath, 'r', libver='latest', swmr=True) as hf:
                if '/Data' not in hf:
                    return
                
                data_group = hf['/Data']
                sparams_found = set()
                
                # Look for datasets with _real or _imag suffix
                for dataset_name in data_group.keys():
                    if dataset_name.endswith('_real'):
                        sparam_name = dataset_name[:-5]  # Remove '_real'
                        sparams_found.add(sparam_name)
                    elif dataset_name.endswith('_imag'):
                        sparam_name = dataset_name[:-5]  # Remove '_imag'
                        sparams_found.add(sparam_name)
                    else:
                        # Real-only data (no suffix)
                        sparams_found.add(dataset_name)
                
                # Sort S-parameters (S11, S12, S21, S22, etc.)
                self.available_sparams = sorted(list(sparams_found))
                
                # Populate combo box
                self.sparam_combo.clear()
                for sparam in self.available_sparams:
                    self.sparam_combo.addItem(sparam)
                
                # Set default to first available
                if len(self.available_sparams) > 0:
                    self.current_sparam = self.available_sparams[0]
                    
                print(f"Found S-parameters: {self.available_sparams}")
                        
        except Exception as e:
            print(f"Error discovering S-parameters: {e}")
    
    def on_sparam_changed(self, sparam_name):
        """Handle S-parameter selection change"""
        if sparam_name and sparam_name in self.available_sparams:
            self.current_sparam = sparam_name
            # Reload data for this S-parameter
            self.last_point_read = 0
            self.all_data = {}
            self.update_visualization()
    
    def populate_frequency_slider(self):
        """Setup frequency slider with frequency data"""
        if self.frequencies is not None:
            num_freqs = len(self.frequencies)
            self.freq_slider.setMaximum(num_freqs - 1)
            self.freq_slider.setValue(0)
            self.update_frequency_label()
            
            # Enable play button once frequencies are loaded
            self.play_button.setEnabled(True)

    def import_new_file(self):
        """Import a new HDF5 file"""
        from PySide6.QtWidgets import QFileDialog
        
        # Stop any ongoing playback
        if self.is_playing:
            self.toggle_play()
        
        # Open file dialog
        hdf5_file, _ = QFileDialog.getOpenFileName(
            self,
            "Select HDF5 Scan File",
            "",
            "HDF5 Files (*.hdf5 *.h5);;All Files (*)"
        )
        
        if hdf5_file:
            # Reset all state
            self.hdf5_filepath = hdf5_file
            self.last_point_read = 0
            self.all_data = {}
            self.all_x = []
            self.all_y = []
            self.frequencies = None
            self.freq_index = 0
            self.total_points_expected = None
            self.available_sparams = []
            self.current_sparam = None
            self.grid_x = None
            self.grid_y = None
            self._view_fitted = False  # Reset view fit flag
            
            # Clear scene
            self.scene.clear()
            
            # Reset UI elements
            self.sparam_combo.clear()
            self.freq_slider.setValue(0)
            self.freq_slider.setMaximum(0)
            self.play_button.setEnabled(False)
            self.status_label.setText("Loading new file...")
            
            # Re-setup and update
            self.initial_setup()
            self.update_visualization()

    def on_slider_changed(self, value):
        """Handle frequency slider change"""
        self.freq_index = value
        self.update_frequency_label()
        self.redraw_data()
    
    def update_frequency_label(self):
        """Update the frequency label based on slider position"""
        if self.frequencies is not None and self.freq_index < len(self.frequencies):
            freq_hz = self.frequencies[self.freq_index]
            freq_ghz = freq_hz / 1e9
            self.freq_value_label.setText(f"{freq_ghz:.4f} GHz")
        else:
            self.freq_value_label.setText("--")
    
    def detect_grid_structure(self):
        """Detect grid dimensions from coordinate data"""
        if len(self.all_x) == 0:
            return
        
        # Find unique coordinates
        unique_x = np.unique(self.all_x)
        unique_y = np.unique(self.all_y)
        
        self.grid_x = len(unique_x)
        self.grid_y = len(unique_y)
        
        self.grid_label.setText(f"Grid: {self.grid_x} × {self.grid_y}")
        
    def find_actual_data_count(self, hf, real_path):
        """
        Find the actual number of written points in a zero-padded dataset.
        Looks for the last row that has non-zero data.
        """
        dataset = hf[real_path]
        total_rows = dataset.shape[0]
        
        # First check if there's a currentPoint attribute or similar
        for attr_name in ['currentPoint', 'current_point', 'num_written', 'write_index', 'nPoints']:
            if attr_name in hf.attrs:
                return int(hf.attrs[attr_name])
            if attr_name in dataset.attrs:
                return int(dataset.attrs[attr_name])
        
        # Start search from where we last found data (optimization)
        # This helps detect new data faster
        start_idx = max(0, self.last_point_read - 1)
        
        # First, check if there's new data beyond our last read point
        # by checking a few rows ahead
        if start_idx > 0 and start_idx < total_rows:
            # Check if data exists at positions beyond last_point_read
            check_idx = min(start_idx + 10, total_rows - 1)
            row = dataset[check_idx, :]
            if np.any(row != 0):
                # There's data ahead, search forward from here
                start_idx = check_idx
        
        # Check if last row is non-zero (file is complete)
        last_row = dataset[total_rows - 1, :]
        if np.any(last_row != 0):
            return total_rows
        
        # Check if first row is zero (no data yet)
        first_row = dataset[0, :]
        if np.all(first_row == 0):
            return 0
        
        # Binary search for the boundary
        low, high = start_idx, total_rows - 1
        while low < high:
            mid = (low + high + 1) // 2
            row = dataset[mid, :]
            if np.any(row != 0):
                low = mid
            else:
                high = mid - 1
        
        # low is now the index of the last non-zero row
        return low + 1  # Return count (index + 1)
    
    def update_visualization(self):
        """Read new data from HDF5 file and update visualization"""
        if not self.current_sparam:
            return
        
        try:
            with h5py.File(self.hdf5_filepath, 'r', libver='latest', swmr=True) as hf:
                # Read frequencies if not loaded
                if self.frequencies is None:
                    if '/Frequencies/Range' in hf:
                        self.frequencies = hf['/Frequencies/Range'][:]
                        self.populate_frequency_slider()
                
                # Check if data exists for current S-parameter
                real_path = f'/Data/{self.current_sparam}_real'
                imag_path = f'/Data/{self.current_sparam}_imag'
                
                if real_path not in hf:
                    return
                
                # Refresh datasets to get latest data (critical for SWMR)
                hf[real_path].refresh()
                if imag_path in hf:
                    hf[imag_path].refresh()
                if '/Coords/x_data' in hf:
                    hf['/Coords/x_data'].refresh()
                if '/Coords/y_data' in hf:
                    hf['/Coords/y_data'].refresh()
                
                # Find actual number of written points (not just array size)
                current_num_points = self.find_actual_data_count(hf, real_path)
                
                if current_num_points == 0:
                    self.status_label.setText("Waiting for data...")
                    return
                
                # Read new data if available
                if current_num_points > self.last_point_read:
                    # Read only the actual written data
                    sparam_real = hf[real_path][:current_num_points, :]
                    if imag_path in hf:
                        sparam_imag = hf[imag_path][:current_num_points, :]
                        self.all_data[self.current_sparam] = sparam_real + 1j * sparam_imag
                    else:
                        self.all_data[self.current_sparam] = sparam_real
                    
                    # Read coordinates
                    self.all_x = hf['/Coords/x_data'][:current_num_points]
                    self.all_y = hf['/Coords/y_data'][:current_num_points]
                    
                    self.last_point_read = current_num_points
                    
                    # Detect grid structure
                    self.detect_grid_structure()
                    
                    # Update visualization
                    self.redraw_data()
                    
                    # Update status
                    total_size = hf[real_path].shape[0]
                    progress = (current_num_points / total_size) * 100
                    status_text = f"Live: {current_num_points}/{total_size} points ({progress:.1f}%)"
                    if current_num_points >= total_size:
                        status_text = f"Complete: {current_num_points} points"
                    self.status_label.setText(status_text)
                    
                    self.points_label.setText(f"Points: {current_num_points}")
                    
        except Exception as e:
            self.status_label.setText(f"Error: {str(e)}")
            print(f"Error in update_visualization: {e}")
    
    def redraw_data(self):
            """Redraw data as heatmap"""
            if self.current_sparam not in self.all_data:
                return
            
            data = self.all_data[self.current_sparam]
            
            if data is None or len(data) == 0:
                return
            
            if self.grid_x is None or self.grid_y is None:
                return
            
            # Store the current view transform before clearing
            view_transform = self.view.transform()
            
            self.scene.clear()
            
            # Get data at selected frequency
            freq_data = data[:, self.freq_index]
            
            # Get data type
            datatype = self.datatype_combo.currentText()
            if datatype == "Magnitude":
                display_data = np.abs(freq_data)
            elif datatype == "Phase":
                display_data = np.angle(freq_data)
            elif datatype == "Real":
                display_data = np.real(freq_data)
            else:  # Imaginary
                display_data = np.imag(freq_data)
            
            # Map points to grid
            grid_data = self.map_to_grid(display_data)
            
            if grid_data is None:
                return
            
            # Update min/max labels
            data_min, data_max = np.nanmin(grid_data), np.nanmax(grid_data)
            self.min_label.setText(f"Min: {data_min:.4f}")
            self.max_label.setText(f"Max: {data_max:.4f}")
            
            # Create heatmap image
            heatmap_image = self.create_heatmap_image(grid_data, data_min, data_max)
            
            # Convert to pixmap and add to scene
            pixmap = QPixmap.fromImage(heatmap_image)
            pixmap_item = QGraphicsPixmapItem(pixmap)
            self.scene.addItem(pixmap_item)
            
            # Only fit view on first draw, otherwise restore previous transform
            if not hasattr(self, '_view_fitted'):
                self.view.fitInView(self.scene.itemsBoundingRect(), Qt.KeepAspectRatio)
                self._view_fitted = True
            else:
                # Restore the previous view transform
                self.view.setTransform(view_transform)
    
    def map_to_grid(self, data):
        """Map scattered data points to regular grid"""
        # Find unique sorted coordinates
        unique_x = np.sort(np.unique(self.all_x))
        unique_y = np.sort(np.unique(self.all_y))
        
        # Create grid
        grid = np.full((len(unique_x), len(unique_y)), np.nan)
        
        # Map each point to grid
        for i in range(len(self.all_x)):
            ix = np.argmin(np.abs(unique_x - self.all_x[i]))
            iy = np.argmin(np.abs(unique_y - self.all_y[i]))
            grid[ix, iy] = data[i]
        
        return grid
    
    def create_heatmap_image(self, grid_data, data_min, data_max):
        """Create QImage from grid data"""
        height, width = grid_data.shape
        
        # Normalize data
        if data_max > data_min:
            normalized = (grid_data - data_min) / (data_max - data_min)
        else:
            normalized = np.zeros_like(grid_data)
        
        # Create image with larger pixels for visibility
        scale_factor = 4
        image = QImage(width * scale_factor, height * scale_factor, QImage.Format_RGB32)
        
        # Fill image
        for ix in range(height):
            for iy in range(width):
                if np.isnan(normalized[ix, iy]):
                    color = QColor(128, 128, 128)  # Gray for missing data
                else:
                    color = self.get_color(normalized[ix, iy])
                
                # Fill scaled block
                for px in range(scale_factor):
                    for py in range(scale_factor):
                        image.setPixelColor(
                            iy * scale_factor + py,
                            ix * scale_factor + px,
                            color
                        )
        
        return image
    
    def get_color(self, value):
        """Get color for normalized value (0-1) based on selected colormap"""
        colormap = self.colormap_combo.currentText()
        
        if colormap == "Jet":
            if value < 0.25:
                r, g, b = 0, int(255 * value / 0.25), 255
            elif value < 0.5:
                r, g, b = 0, 255, int(255 * (0.5 - value) / 0.25)
            elif value < 0.75:
                r, g, b = int(255 * (value - 0.5) / 0.25), 255, 0
            else:
                r, g, b = 255, int(255 * (1 - value) / 0.25), 0
        
        elif colormap == "Viridis":
            r = int(255 * (0.267 + 0.005 * value))
            g = int(255 * (0.005 + 0.570 * value))
            b = int(255 * (0.329 + 0.528 * value))
        
        elif colormap == "Hot":
            if value < 0.33:
                r, g, b = int(255 * value / 0.33), 0, 0
            elif value < 0.67:
                r, g, b = 255, int(255 * (value - 0.33) / 0.34), 0
            else:
                r, g, b = 255, 255, int(255 * (value - 0.67) / 0.33)
        
        elif colormap == "Cool":
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
        self.play_timer.stop()
        event.accept()


# For testing
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