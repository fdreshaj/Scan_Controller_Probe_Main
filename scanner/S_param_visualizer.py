#############
###############
# S-Parameter Visualizer 
############### FIXED: Real-time updating now works continuously
#############


import os
import sys

if __package__ in (None, ""):
    # Being run as a plain script (`python scanner/S_param_visualizer.py`).
    # Python puts the script's own directory on sys.path, not the repo root, so
    # `import scanner` would find scanner/scanner.py -- a module, not the
    # package -- and blow up. Put the repo root first so the package wins.
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGraphicsView, QGraphicsScene, QHBoxLayout,
    QPushButton, QLabel, QComboBox, QGraphicsPixmapItem, QSlider,
    QDoubleSpinBox, QCheckBox, QSplitter, QFileDialog
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QPainter, QColor, QFont, QImage, QPixmap
import h5py
import numpy as np

from scanner import sparam_processing as sp

# The trace panel needs a line plot. matplotlib is already a dependency of the
# application (gui/plotter.py), but this window is also runnable standalone, so
# the import is guarded: without it the heatmap still works and the trace panel
# is simply not offered.
try:
    import matplotlib
    matplotlib.use("QtAgg")
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    TRACE_PLOT_AVAILABLE = True
except Exception as _trace_import_error:  # pragma: no cover - environment dependent
    print(f"Trace panel disabled (matplotlib unavailable): {_trace_import_error}")
    TRACE_PLOT_AVAILABLE = False

#: Domain the slider and heatmap operate in.
DOMAIN_FREQUENCY = "Frequency"
DOMAIN_TIME = "Time (FFT)"

#: Zero-padding for the whole-scan transform. Every measurement point is
#: transformed at once, so padding multiplies the memory held for the scan --
#: a 10k-point x 1001-frequency scan is already 160 MB as complex128. Padding
#: only interpolates the axis, it adds no resolution, and the heatmap slider
#: steps bin by bin where interpolation buys nothing. The single-point trace
#: plot pads properly because there it does help read a peak off the curve.
HEATMAP_PAD_FACTOR = 1
TRACE_PAD_FACTOR = 8

class ZoomableGraphicsView(QGraphicsView):
    """Custom QGraphicsView with mouse wheel zoom and click-to-select."""

    #: Emitted with the scene position of a left click, so the window can work
    #: out which measurement point the operator picked for the trace panel.
    point_clicked = Signal(float, float)

    def __init__(self, scene):
        super().__init__(scene)
        self.zoom_factor = 1.15
        self.min_zoom = 0.1
        self.max_zoom = 10.0
        self.current_zoom = 1.0

    def mousePressEvent(self, event):
        """Report left clicks, then hand the event on so panning still works."""
        if event.button() == Qt.LeftButton:
            scene_pos = self.mapToScene(event.position().toPoint())
            self.point_clicked.emit(scene_pos.x(), scene_pos.y())
        super().mousePressEvent(event)


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
    

class VisualizerWindow(QWidget):
    """Live heatmap of a scan, with FFT, delay-filter and phase views.

    Two ways in:

    * The scanner GUI constructs it with the path of the scan it just started,
      and the window follows the file as points are written.
    * On its own -- ``python -m scanner.S_param_visualizer`` -- with no path.
      The window opens empty with everything but the Import button disabled,
      and comes to life once a file is chosen.

    A path that does not exist is treated as the empty case rather than an
    error, so a mistyped or not-yet-created file leaves a usable window.
    """

    def __init__(self, hdf5_filepath=None):
        super().__init__(None)
        self.setWindowTitle("Real-Time Scan Visualizer")
        self.resize(900, 800)

        self.hdf5_filepath = hdf5_filepath
        if hdf5_filepath:
            self.setWindowTitle(
                f"Real-Time Scan Visualizer - {os.path.basename(hdf5_filepath)}"
            )
        self.last_point_read = 0
        self.all_data = {}  # Dictionary to store data for each S-parameter
        self.all_x = []
        self.all_y = []
        self.frequencies = None      # as stored in the file (GHz for scan files)
        self.freqs_hz = None         # the same axis normalised to Hz
        self.freq_index = 0          # index into the current domain's axis
        self.total_points_expected = None
        self.available_sparams = []
        self.current_sparam = None

        #: Pixels per grid cell in the rendered heatmap. The click handler
        #: divides by this to get back to a grid index, so the renderer and the
        #: hit test must agree on one value.
        self.heatmap_scale_factor = 4

        # Grid parameters
        self.grid_x = None
        self.grid_y = None
        self.is_uniform = False
        self.unique_x = None
        self.unique_y = None
        self.grid_point_index = None  # grid cell -> index into all_data rows
        self._grid_ix = None          # cached cell index per point (x axis)
        self._grid_iy = None          # cached cell index per point (y axis)

        # FFT / filter / phase pipeline
        self._processed = None        # complex data after filter + domain transform
        self._axis_values = None      # Hz in frequency domain, seconds in time domain
        self._display_matrix = None   # cache for sweep-dependent modes (unwrapped phase)
        self._display_matrix_mode = None
        self.selected_point = None    # row index of the pixel shown in the trace panel
        self._transform_error = False # a transform message is on the status bar
        self._data_status = "Waiting for data..."
        
        # Animation parameters
        self.is_playing = False
        self.play_timer = QTimer()
        self.play_timer.timeout.connect(self.play_next_frame)
        self.play_speed = 0.05  # ms per frame
        
        # Setup UI
        self.setup_ui()

        # Do initial read to get metadata
        self.initial_setup()

        # Setup timer for updating - ALWAYS runs to check for changes.
        # It is harmless with no file loaded: check_for_updates returns early.
        self.timer = QTimer()
        self.timer.timeout.connect(self.check_for_updates)
        self.timer.start(500)  # Check every 500ms

        # Do initial visualization
        self.update_visualization()
        self.update_enabled_state()

    # ----------------------------------------------------------------------
    # Empty state
    # ----------------------------------------------------------------------

    def has_file(self) -> bool:
        """Whether a readable scan file is currently loaded."""
        return bool(self.hdf5_filepath) and os.path.isfile(self.hdf5_filepath)

    def update_enabled_state(self):
        """Grey out everything that needs data, leaving only Import.

        Running the visualizer on its own opens an empty window. Rather than
        offering controls that would do nothing -- or worse, raise -- the whole
        toolbar is disabled until a file is loaded, so the one thing that *is*
        actionable is obvious.
        """
        loaded = self.has_file() and bool(self.available_sparams)

        for widget in (
            self.sparam_combo,
            self.datatype_combo,
            self.colormap_combo,
            self.domain_combo,
            self.window_combo,
            self.filter_combo,
            self.freq_slider,
            self.trace_checkbox,
        ):
            widget.setEnabled(loaded)

        # These two have their own rules on top of "is a file loaded".
        self.cutoff_spin.setEnabled(
            loaded and self.filter_combo.currentText() != sp.FILTER_OFF
        )
        self.trace_checkbox.setEnabled(loaded and TRACE_PLOT_AVAILABLE)
        self.play_button.setEnabled(
            loaded and self.freq_slider.maximum() > 0
        )

        if not loaded:
            self.show_empty_state()

    def show_empty_state(self):
        """Put a short instruction where the heatmap would be."""
        self.scene.clear()
        message = self.scene.addText(
            "No scan loaded\n\n"
            "Use “📁 Import HDF5…” above to open a scan file (.hdf5, .h5)",
            QFont("Arial", 13),
        )
        message.setDefaultTextColor(QColor(130, 130, 130))
        # Show it at its natural size and centred. fitInView would scale a
        # short string up to fill the whole viewport.
        self.view.resetTransform()
        self.view.current_zoom = 1.0
        self.view.setSceneRect(message.boundingRect())
        self.view.centerOn(message)
        # The next real draw must re-fit to the data, not keep this transform.
        self._view_fitted = False

        if self.hdf5_filepath and not os.path.isfile(self.hdf5_filepath):
            self.status_label.setText(
                f"File not found: {os.path.basename(self.hdf5_filepath)}"
            )
        else:
            self.status_label.setText("No file loaded")

        self.points_label.setText("Points: 0")
        self.grid_label.setText("Grid: --")
        self.min_label.setText("Min: --")
        self.max_label.setText("Max: --")
        self.freq_value_label.setText("--")

    def setup_ui(self):
        layout = QVBoxLayout()
        
        # Top control bar
        control_layout = QHBoxLayout()
        
        # Import button. The one control that is always live -- with nothing
        # loaded it is the only thing on the toolbar that does anything, so it
        # carries a label rather than a bare icon.
        self.import_button = QPushButton("📁 Import HDF5…")
        self.import_button.setToolTip("Open an HDF5 scan file (.hdf5, .h5)")
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
        self.datatype_combo.addItems(list(sp.DISPLAY_MODES))
        self.datatype_combo.currentTextChanged.connect(self.on_display_mode_changed)
        control_layout.addWidget(self.datatype_combo)
        
        # Colormap selector
        colormap_label = QLabel("Colormap:")
        control_layout.addWidget(colormap_label)
        
        self.colormap_combo = QComboBox()
        self.colormap_combo.addItems(["Jet", "Viridis", "Hot", "Cool", "Grayscale"])
        self.colormap_combo.currentTextChanged.connect(self.redraw_data)
        control_layout.addWidget(self.colormap_combo)
        
        layout.addLayout(control_layout)

        # ------------------------------------------------------------------
        # Second control row: FFT domain and delay filter
        # ------------------------------------------------------------------
        transform_layout = QHBoxLayout()

        transform_layout.addWidget(QLabel("Domain:"))
        self.domain_combo = QComboBox()
        self.domain_combo.addItems([DOMAIN_FREQUENCY, DOMAIN_TIME])
        self.domain_combo.setToolTip(
            "Frequency: the measured sweep.\n"
            "Time (FFT): the sweep inverse-transformed to a delay/range profile, "
            "so the slider steps through range instead of frequency."
        )
        self.domain_combo.currentTextChanged.connect(self.on_domain_changed)
        transform_layout.addWidget(self.domain_combo)

        transform_layout.addWidget(QLabel("Window:"))
        self.window_combo = QComboBox()
        self.window_combo.addItems(list(sp.WINDOW_NAMES))
        self.window_combo.setToolTip(
            "Applied across the sweep before the FFT. Suppresses the sidelobes "
            "that would otherwise smear a strong reflection along the range "
            "axis. 'None' gives the sharpest peak and the worst sidelobes."
        )
        self.window_combo.currentTextChanged.connect(self.on_transform_changed)
        transform_layout.addWidget(self.window_combo)

        transform_layout.addSpacing(16)

        transform_layout.addWidget(QLabel("Filter:"))
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(list(sp.FILTER_MODES))
        self.filter_combo.setToolTip(
            "Filters the sweep by delay content.\n"
            "Low Pass keeps short delays: removes multipath and late echoes.\n"
            "High Pass keeps long delays: removes antenna mismatch and the "
            "direct coupling that dominates a near-field scan."
        )
        self.filter_combo.currentTextChanged.connect(self.on_transform_changed)
        transform_layout.addWidget(self.filter_combo)

        transform_layout.addWidget(QLabel("Cutoff:"))
        self.cutoff_spin = QDoubleSpinBox()
        self.cutoff_spin.setDecimals(3)
        self.cutoff_spin.setSuffix(" ns")
        self.cutoff_spin.setMinimum(0.0)
        self.cutoff_spin.setMaximum(1.0e6)
        self.cutoff_spin.setSingleStep(0.1)
        self.cutoff_spin.setValue(1.0)
        self.cutoff_spin.setEnabled(False)
        self.cutoff_spin.setToolTip("Delay at which the filter rolls off.")
        self.cutoff_spin.valueChanged.connect(self.on_transform_changed)
        transform_layout.addWidget(self.cutoff_spin)

        self.cutoff_range_label = QLabel("")
        self.cutoff_range_label.setToolTip(
            "The cutoff delay expressed as a two-way distance in free space."
        )
        transform_layout.addWidget(self.cutoff_range_label)

        transform_layout.addStretch()

        self.trace_checkbox = QCheckBox("Trace panel")
        self.trace_checkbox.setChecked(False)
        self.trace_checkbox.setEnabled(TRACE_PLOT_AVAILABLE)
        if not TRACE_PLOT_AVAILABLE:
            self.trace_checkbox.setToolTip("matplotlib is not installed")
        else:
            self.trace_checkbox.setToolTip(
                "Show the full response of one pixel. Click the heatmap to pick one."
            )
        self.trace_checkbox.toggled.connect(self.on_trace_toggled)
        transform_layout.addWidget(self.trace_checkbox)

        layout.addLayout(transform_layout)

        # Graphics view
        self.scene = QGraphicsScene()
        self.view = ZoomableGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.Antialiasing)
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.view.setDragMode(QGraphicsView.ScrollHandDrag)  # Enable drag to pan
        self.view.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)  # Zoom at mouse cursor
        self.view.point_clicked.connect(self.on_heatmap_clicked)

        # Heatmap on top, optional trace plot underneath.
        self.display_splitter = QSplitter(Qt.Vertical)
        self.display_splitter.addWidget(self.view)

        self.trace_canvas = None
        if TRACE_PLOT_AVAILABLE:
            self.trace_figure = Figure(figsize=(5, 2.2), tight_layout=True)
            self.trace_canvas = FigureCanvas(self.trace_figure)
            self.trace_axes = self.trace_figure.add_subplot(111)
            self.trace_canvas.setMinimumHeight(160)
            self.trace_canvas.setVisible(False)
            self.display_splitter.addWidget(self.trace_canvas)

        self.display_splitter.setStretchFactor(0, 3)
        layout.addWidget(self.display_splitter)


        # Frequency slider section
        freq_slider_layout = QVBoxLayout()
        
        # Frequency label
        freq_label_layout = QHBoxLayout()
        self.axis_name_label = QLabel("Frequency:")
        freq_label_layout.addWidget(self.axis_name_label)
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
        """Advance one bin along whichever axis the slider is showing."""
        axis = self.current_axis_values()
        if axis is None or len(axis) == 0:
            return

        next_index = self.freq_index + 1
        if next_index >= len(axis):
            next_index = 0  # loop

        # Updating the slider triggers the redraw.
        self.freq_slider.setValue(next_index)
    
    def initial_setup(self):
        """Initial setup - read metadata and discover S-parameters"""
        if not self.has_file():
            return
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
        # With no file loaded there is nothing to poll, and re-opening a
        # missing path twice a second would just churn.
        if not self.has_file():
            return
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
            self._invalidate_processing()
            self.update_visualization()
    
    # ----------------------------------------------------------------------
    # FFT / filter pipeline
    # ----------------------------------------------------------------------

    def _invalidate_processing(self):
        """Drop the cached transform. Call after anything that changes it."""
        self._processed = None
        self._axis_values = None
        self._display_matrix = None
        self._display_matrix_mode = None

    def _ensure_processed(self):
        """Apply the filter and domain transform, caching the result.

        Both are whole-scan operations, so recomputing them on every slider
        step would make the frequency animation crawl. The cache is dropped by
        `_invalidate_processing` whenever new data arrives or a control that
        feeds the pipeline changes.

        Returns True when `self._processed` and `self._axis_values` are usable.
        """
        if self._processed is not None:
            return True

        raw = self.all_data.get(self.current_sparam)
        if raw is None or len(raw) == 0 or self.freqs_hz is None:
            return False
        if np.ndim(raw) != 2 or raw.shape[1] != len(self.freqs_hz):
            return False

        data = np.asarray(raw, dtype=complex)

        try:
            filter_mode = self.filter_combo.currentText()
            if filter_mode != sp.FILTER_OFF:
                cutoff_s = self.cutoff_spin.value() * 1e-9
                data = sp.apply_filter(data, self.freqs_hz, filter_mode, cutoff_s)

            if self.domain_combo.currentText() == DOMAIN_TIME:
                times, data = sp.to_time_domain(
                    data,
                    self.freqs_hz,
                    window=self.window_combo.currentText(),
                    pad_factor=HEATMAP_PAD_FACTOR,
                )
                self._axis_values = times
            else:
                self._axis_values = np.asarray(self.freqs_hz, dtype=float)
        except ValueError as exc:
            # A non-uniform sweep is the usual cause. Say so rather than
            # showing a plausible but meaningless transform.
            self._transform_error = True
            self.status_label.setText(f"Transform unavailable: {exc}")
            return False

        if self._transform_error:
            # The operator has changed something that fixed it; put the data
            # status back rather than leaving a stale error on screen.
            self._transform_error = False
            self.status_label.setText(self._data_status)

        self._processed = data
        return True

    def _display_slice(self):
        """The real-valued data for the current slider position.

        Most display modes are per-sample, so they are applied to the single
        column the slider selects. Unwrapped phase is not: it needs the whole
        sweep, so for that mode the transform runs across the full matrix once
        and is cached.
        """
        if not self._ensure_processed():
            return None

        index = min(self.freq_index, self._processed.shape[1] - 1)
        mode = self.datatype_combo.currentText()

        if mode in sp.SWEEP_DEPENDENT_MODES:
            if self._display_matrix is None or self._display_matrix_mode != mode:
                self._display_matrix = sp.to_display(self._processed, mode, axis=-1)
                self._display_matrix_mode = mode
            return self._display_matrix[:, index]

        return sp.to_display(self._processed[:, index], mode)

    def on_display_mode_changed(self, _mode=None):
        self._display_matrix = None
        self._display_matrix_mode = None
        self.redraw_data()
        self.update_trace_plot()

    def on_domain_changed(self, _domain=None):
        """Switch the slider and heatmap between frequency and range."""
        self._invalidate_processing()
        self.freq_index = 0
        self.populate_axis_slider()
        self.redraw_data()
        self.update_trace_plot()

    def on_transform_changed(self, _value=None):
        """A filter or window change: re-run the pipeline, keep the position."""
        self.cutoff_spin.setEnabled(
            self.filter_combo.currentText() != sp.FILTER_OFF
        )
        self.update_cutoff_range_label()
        self._invalidate_processing()
        self.populate_axis_slider(keep_position=True)
        self.redraw_data()
        self.update_trace_plot()

    def update_cutoff_range_label(self):
        """Show the cutoff delay as a distance, which is what an operator
        actually has in mind when gating out a reflection."""
        if self.filter_combo.currentText() == sp.FILTER_OFF:
            self.cutoff_range_label.setText("")
            return
        cutoff_s = self.cutoff_spin.value() * 1e-9
        metres = sp.time_to_range(cutoff_s)
        self.cutoff_range_label.setText(f"(≈ {metres * 100:.1f} cm two-way)")

    def configure_filter_defaults(self):
        """Pick a starting cutoff and a sane range once the sweep is known."""
        if self.freqs_hz is None or len(self.freqs_hz) < 2:
            return
        try:
            # Half the unambiguous span: past that the delay bins fold back on
            # themselves and a larger cutoff changes nothing.
            span_ns = sp.max_filter_delay(self.freqs_hz) * 1e9
            default_ns = sp.suggested_cutoff(self.freqs_hz) * 1e9
        except ValueError:
            return

        self.cutoff_spin.blockSignals(True)
        self.cutoff_spin.setMaximum(span_ns)
        self.cutoff_spin.setSingleStep(max(span_ns / 200.0, 1e-3))
        self.cutoff_spin.setValue(default_ns)
        self.cutoff_spin.blockSignals(False)
        self.update_cutoff_range_label()

    def current_axis_values(self):
        """The axis the slider indexes: Hz, or seconds in the FFT view."""
        if self._axis_values is not None:
            return self._axis_values
        if self.domain_combo.currentText() == DOMAIN_FREQUENCY:
            return self.freqs_hz
        return None

    def populate_axis_slider(self, keep_position=False):
        """Size the slider to the current domain's axis."""
        if not self._ensure_processed():
            # Fall back to the raw frequency axis so the slider is usable as
            # soon as frequencies are known, before any data has arrived.
            if self.freqs_hz is None:
                return
            num_bins = len(self.freqs_hz)
        else:
            num_bins = self._processed.shape[1]

        previous = self.freq_index if keep_position else 0
        self.freq_slider.blockSignals(True)
        self.freq_slider.setMaximum(max(num_bins - 1, 0))
        self.freq_index = min(previous, num_bins - 1)
        self.freq_slider.setValue(self.freq_index)
        self.freq_slider.blockSignals(False)

        self.update_axis_label()
        self.play_button.setEnabled(num_bins > 1)

    # Kept under the old name so any external caller keeps working.
    def populate_frequency_slider(self):
        self.populate_axis_slider()

    def import_new_file(self):
        """Import a new HDF5 file.

        The only control that stays live with nothing loaded, so it is also the
        entry point when the visualizer is run on its own.
        """
        # Stop any ongoing playback
        if self.is_playing:
            self.toggle_play()

        # Start the dialog in the directory of the current file, if there is
        # one -- scans from a session tend to live together.
        start_dir = ""
        if self.hdf5_filepath:
            start_dir = os.path.dirname(os.path.abspath(self.hdf5_filepath))

        # Open file dialog
        hdf5_file, _ = QFileDialog.getOpenFileName(
            self,
            "Select HDF5 Scan File",
            start_dir,
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
            self.freqs_hz = None
            self.freq_index = 0
            self.total_points_expected = None
            self.available_sparams = []
            self.current_sparam = None
            self.grid_x = None
            self.grid_y = None
            self.unique_x = None
            self.unique_y = None
            self.grid_point_index = None
            self._grid_ix = None
            self._grid_iy = None
            self.selected_point = None
            self._invalidate_processing()
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

            if not self.available_sparams:
                # A readable file with no /Data group, or not a scan file at
                # all. Say so instead of leaving a blank window with live
                # controls that have nothing to act on.
                self.update_enabled_state()
                self.status_label.setText(
                    f"No S-parameter data in {os.path.basename(hdf5_file)}"
                )
                return

            self.setWindowTitle(
                f"Real-Time Scan Visualizer - {os.path.basename(hdf5_file)}"
            )
            self.update_enabled_state()

    def on_slider_changed(self, value):
        """Handle slider change (frequency bin, or range bin in the FFT view)"""
        self.freq_index = value
        self.update_axis_label()
        self.redraw_data()
        self.update_trace_plot()

    def update_axis_label(self):
        """Label the slider position in the units of the current domain.

        In the FFT view the delay is also shown as a two-way distance, which is
        what the operator is actually looking for when range-gating a target.
        """
        axis = self.current_axis_values()
        if axis is None or len(axis) == 0 or self.freq_index >= len(axis):
            self.freq_value_label.setText("--")
            return

        if self.domain_combo.currentText() == DOMAIN_TIME:
            delay_s = float(axis[self.freq_index])
            metres = sp.time_to_range(delay_s)
            self.axis_name_label.setText("Range:")
            self.freq_value_label.setText(
                f"{delay_s * 1e9:.3f} ns   ({metres * 100:.2f} cm two-way)"
            )
        else:
            # `freqs_hz` is normalised on load, so this is Hz regardless of
            # whether the file stored GHz.
            self.axis_name_label.setText("Frequency:")
            self.freq_value_label.setText(f"{float(axis[self.freq_index]) / 1e9:.4f} GHz")

    # Kept under the old name so any external caller keeps working.
    def update_frequency_label(self):
        self.update_axis_label()
    
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
        if not self.has_file() or not self.current_sparam:
            return
        
        try:
            with h5py.File(self.hdf5_filepath, 'r', libver='latest', swmr=True) as hf:
                # Read frequencies if not loaded
                if self.frequencies is None:
                    if '/Frequencies/Range' in hf:
                        self.frequencies = hf['/Frequencies/Range'][:]
                        # The scan writer stores GHz; a plugin may hand over Hz.
                        # Every transform here needs Hz, so settle it once.
                        self.freqs_hz = sp.normalize_frequencies_to_hz(self.frequencies)
                        self.configure_filter_defaults()
                        self.populate_axis_slider()
                
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

                    # The pipeline cache is keyed to the data it was built
                    # from, so new rows must drop it. The grid mapping is keyed
                    # to the coordinates, which have also just grown.
                    self._invalidate_processing()
                    self._grid_ix = None
                    self._grid_iy = None

                    # Detect grid structure
                    self.detect_grid_structure()

                    # Update visualization
                    self.populate_axis_slider(keep_position=True)
                    self.redraw_data()
                    self.update_trace_plot()
                    
                    # Update status
                    total_size = hf[real_path].shape[0]
                    progress = (current_num_points / total_size) * 100
                    status_text = f"Live: {current_num_points}/{total_size} points ({progress:.1f}%)"
                    if current_num_points >= total_size:
                        status_text = f"Complete: {current_num_points} points"
                    self._data_status = status_text
                    if not self._transform_error:
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

            # Run the filter / FFT pipeline and take the selected slice. In the
            # frequency domain with no filter this is the same value the old
            # code read straight out of `data`.
            display_data = self._display_slice()
            if display_data is None:
                return

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
            
            # The empty-state placeholder pins the scene rect to the size of
            # its text. Nothing else resets it, so without this the scrollable
            # area stays text-sized and the heatmap will not fit to the view.
            self.view.setSceneRect(self.scene.itemsBoundingRect())

            # Only fit view on first draw, otherwise restore previous transform
            # getattr, not hasattr: import_new_file sets this back to False to
            # ask for a re-fit, and hasattr would stay True forever, leaving a
            # newly imported scan at the previous file's zoom.
            if not getattr(self, '_view_fitted', False):
                self.view.fitInView(self.scene.itemsBoundingRect(), Qt.KeepAspectRatio)
                self._view_fitted = True
            else:
                # Restore the previous view transform
                self.view.setTransform(view_transform)
    
    @staticmethod
    def _nearest_indices(sorted_values, queries):
        """Index of the closest entry of `sorted_values` for each query.

        Vectorised equivalent of ``argmin(abs(sorted_values - q))`` per query.
        `searchsorted` finds the insertion point in O(log n); the neighbour
        comparison then picks whichever side is actually nearer, so the result
        matches the original argmin even when coordinates carry float drift.
        """
        sorted_values = np.asarray(sorted_values, dtype=float)
        queries = np.asarray(queries, dtype=float)
        if sorted_values.size == 1:
            return np.zeros(queries.shape, dtype=int)

        right = np.searchsorted(sorted_values, queries)
        right = np.clip(right, 1, sorted_values.size - 1)
        left = right - 1
        pick_right = np.abs(queries - sorted_values[left]) > np.abs(
            sorted_values[right] - queries
        )
        return np.where(pick_right, right, left)

    def _ensure_grid_indices(self):
        """Work out which grid cell each measurement point falls in.

        Cached: the mapping depends only on the coordinates, which change when
        new points arrive, not when the frequency slider moves or the display
        mode changes. Recomputing it per redraw was the dominant cost of
        scrubbing the range slider on a large scan.
        """
        if self._grid_ix is not None and len(self._grid_ix) == len(self.all_x):
            return True
        if len(self.all_x) == 0:
            return False

        self.unique_x = np.sort(np.unique(self.all_x))
        self.unique_y = np.sort(np.unique(self.all_y))

        self._grid_ix = self._nearest_indices(self.unique_x, self.all_x)
        self._grid_iy = self._nearest_indices(self.unique_y, self.all_y)

        index_grid = np.full((len(self.unique_x), len(self.unique_y)), -1, dtype=int)
        index_grid[self._grid_ix, self._grid_iy] = np.arange(len(self.all_x))
        self.grid_point_index = index_grid
        return True

    def map_to_grid(self, data):
        """Map scattered data points to a regular grid.

        The cell each point belongs to is cached by `_ensure_grid_indices`, so
        this is a single scatter-assign per redraw.
        """
        if not self._ensure_grid_indices():
            return None

        grid = np.full((len(self.unique_x), len(self.unique_y)), np.nan)
        grid[self._grid_ix, self._grid_iy] = np.asarray(data)[: len(self._grid_ix)]
        return grid

    # ----------------------------------------------------------------------
    # Trace panel
    # ----------------------------------------------------------------------

    def on_trace_toggled(self, checked):
        if self.trace_canvas is None:
            return
        self.trace_canvas.setVisible(checked)
        if checked:
            self.update_trace_plot()

    def on_heatmap_clicked(self, scene_x, scene_y):
        """Turn a click on the heatmap into the measurement point under it.

        `create_heatmap_image` draws grid cell (ix, iy) as a `scale_factor`
        block at image column `iy`, row `ix` -- the image axes are transposed
        relative to the grid, so the mapping back is y->row, x->column.
        """
        if self.grid_point_index is None:
            return

        scale = self.heatmap_scale_factor
        row = int(scene_y // scale)   # index into unique_x
        col = int(scene_x // scale)   # index into unique_y

        rows, cols = self.grid_point_index.shape
        if not (0 <= row < rows and 0 <= col < cols):
            return

        point = int(self.grid_point_index[row, col])
        if point < 0:
            return  # an empty cell: nothing measured here yet

        self.selected_point = point
        if not self.trace_checkbox.isChecked() and TRACE_PLOT_AVAILABLE:
            self.trace_checkbox.setChecked(True)  # triggers the redraw
        else:
            self.update_trace_plot()

    def update_trace_plot(self):
        """Draw the full response of the selected pixel.

        A heatmap can only ever show one frequency or one range bin at a time.
        The FFT and phase views are about how a point behaves *across* the
        sweep, so this panel is where they are actually readable: the range
        profile of a pixel, or its phase ramp against frequency.

        The unfiltered response is drawn behind the filtered one whenever a
        filter is active, so the effect of the cutoff is visible rather than
        inferred.
        """
        if self.trace_canvas is None or not self.trace_checkbox.isChecked():
            return

        self.trace_axes.clear()

        raw = self.all_data.get(self.current_sparam)
        if raw is None or self.selected_point is None or self.freqs_hz is None:
            self.trace_axes.text(
                0.5, 0.5, "Click a pixel to plot its response",
                ha="center", va="center", transform=self.trace_axes.transAxes,
                color="gray",
            )
            self.trace_canvas.draw_idle()
            return

        if self.selected_point >= len(raw):
            return

        mode = self.datatype_combo.currentText()
        filter_mode = self.filter_combo.currentText()
        in_time_domain = self.domain_combo.currentText() == DOMAIN_TIME
        trace_raw = np.asarray(raw[self.selected_point], dtype=complex)

        try:
            curves = []
            if filter_mode != sp.FILTER_OFF:
                curves.append(("Unfiltered", trace_raw, 0.35))
                cutoff_s = self.cutoff_spin.value() * 1e-9
                filtered = sp.apply_filter(
                    trace_raw, self.freqs_hz, filter_mode, cutoff_s
                )
                curves.append((filter_mode, filtered, 1.0))
            else:
                curves.append(("S-parameter", trace_raw, 1.0))

            for label, values, alpha in curves:
                if in_time_domain:
                    axis, values = sp.to_time_domain(
                        values,
                        self.freqs_hz,
                        window=self.window_combo.currentText(),
                        pad_factor=TRACE_PAD_FACTOR,
                    )
                    axis = axis * 1e9  # ns
                else:
                    axis = np.asarray(self.freqs_hz, dtype=float) / 1e9  # GHz

                self.trace_axes.plot(
                    axis, sp.to_display(values, mode), label=label, alpha=alpha,
                    linewidth=1.2,
                )
        except ValueError as exc:
            self.trace_axes.text(
                0.5, 0.5, f"Cannot plot: {exc}",
                ha="center", va="center", transform=self.trace_axes.transAxes,
                color="firebrick", wrap=True,
            )
            self.trace_canvas.draw_idle()
            return

        # Mark where the heatmap slider currently sits.
        axis_values = self.current_axis_values()
        if axis_values is not None and self.freq_index < len(axis_values):
            marker = float(axis_values[self.freq_index])
            marker = marker * 1e9 if in_time_domain else marker / 1e9
            self.trace_axes.axvline(marker, color="k", linestyle=":", linewidth=1.0)

        # Show where the filter cuts, so the cutoff is not a blind number.
        if filter_mode != sp.FILTER_OFF and in_time_domain:
            self.trace_axes.axvline(
                self.cutoff_spin.value(), color="firebrick",
                linestyle="--", linewidth=1.0,
            )

        x_label = "Delay (ns)" if in_time_domain else "Frequency (GHz)"
        self.trace_axes.set_xlabel(x_label, fontsize=8)
        # Most mode names already carry their unit ("Phase (deg)"); appending
        # it again would just make the label long enough to be clipped.
        units = sp.display_units(mode)
        y_label = mode if "(" in mode else f"{mode} [{units}]"
        self.trace_axes.set_ylabel(y_label, fontsize=8)
        self.trace_axes.tick_params(labelsize=7)
        self.trace_axes.grid(True, alpha=0.3)
        if len(curves) > 1:
            self.trace_axes.legend(fontsize=7)

        x_pos, y_pos = self.point_coordinates(self.selected_point)
        self.trace_axes.set_title(
            f"Point {self.selected_point}  (x={x_pos:.2f}, y={y_pos:.2f} mm)",
            fontsize=8,
        )
        self.trace_canvas.draw_idle()

    def point_coordinates(self, index):
        """The scan coordinates of a measurement point, for labelling."""
        try:
            return float(self.all_x[index]), float(self.all_y[index])
        except (IndexError, TypeError, ValueError):
            return float("nan"), float("nan")
    
    def create_heatmap_image(self, grid_data, data_min, data_max):
        """Create QImage from grid data.

        Vectorised. The original built the image with a per-pixel
        ``setPixelColor`` loop, which cost ~60 ms for a 60x60 grid -- fine when
        the slider only stepped through frequency occasionally, but the FFT
        view makes scrubbing the range axis the main way you read the data, and
        the play button animates it. `_colormap_rgb` produces exactly the same
        colours as `get_color`; `test_sparam_visualizer.py` asserts that.
        """
        height, width = grid_data.shape

        # Normalize data
        if data_max > data_min:
            normalized = (grid_data - data_min) / (data_max - data_min)
        else:
            normalized = np.zeros_like(grid_data)

        rgb = self._colormap_rgb(normalized)

        # Enlarge each grid cell into a solid block.
        scale_factor = self.heatmap_scale_factor
        rgb = np.repeat(np.repeat(rgb, scale_factor, axis=0), scale_factor, axis=1)
        rgb = np.ascontiguousarray(rgb)

        image = QImage(
            rgb.data,
            width * scale_factor,
            height * scale_factor,
            rgb.strides[0],
            QImage.Format_RGB888,
        )
        # QImage wraps the buffer without owning it, and `rgb` is a local that
        # is about to go out of scope. copy() detaches it onto Qt's own memory.
        return image.copy()

    def _colormap_rgb(self, normalized):
        """Map normalised values in [0, 1] to an (h, w, 3) uint8 RGB array.

        Mirrors `get_color` exactly, including its int() truncation, so the
        vectorised renderer is pixel-identical to the original loop. NaN cells
        (grid positions not yet measured) become mid grey.
        """
        colormap = self.colormap_combo.currentText()

        values = np.asarray(normalized, dtype=float)
        missing = np.isnan(values)
        v = np.where(missing, 0.0, values)

        # int() truncates toward zero, which for these non-negative
        # expressions is what astype(np.int32) does.
        def trunc(a):
            return np.clip(a, 0, 255).astype(np.int32)

        if colormap == "Jet":
            r = np.zeros_like(v, dtype=np.int32)
            g = np.zeros_like(v, dtype=np.int32)
            b = np.zeros_like(v, dtype=np.int32)

            m = v < 0.25
            r[m], g[m], b[m] = 0, trunc(255 * v[m] / 0.25), 255

            m = (v >= 0.25) & (v < 0.5)
            r[m], g[m], b[m] = 0, 255, trunc(255 * (0.5 - v[m]) / 0.25)

            m = (v >= 0.5) & (v < 0.75)
            r[m], g[m], b[m] = trunc(255 * (v[m] - 0.5) / 0.25), 255, 0

            m = v >= 0.75
            r[m], g[m], b[m] = 255, trunc(255 * (1 - v[m]) / 0.25), 0

        elif colormap == "Viridis":
            r = trunc(255 * (0.267 + 0.005 * v))
            g = trunc(255 * (0.005 + 0.570 * v))
            b = trunc(255 * (0.329 + 0.528 * v))

        elif colormap == "Hot":
            r = np.zeros_like(v, dtype=np.int32)
            g = np.zeros_like(v, dtype=np.int32)
            b = np.zeros_like(v, dtype=np.int32)

            m = v < 0.33
            r[m], g[m], b[m] = trunc(255 * v[m] / 0.33), 0, 0

            m = (v >= 0.33) & (v < 0.67)
            r[m], g[m], b[m] = 255, trunc(255 * (v[m] - 0.33) / 0.34), 0

            m = v >= 0.67
            r[m], g[m], b[m] = 255, 255, trunc(255 * (v[m] - 0.67) / 0.33)

        elif colormap == "Cool":
            r = trunc(255 * v)
            g = trunc(255 * (1 - v))
            b = np.full_like(r, 255)

        else:  # Grayscale
            gray = trunc(255 * v)
            r = g = b = gray

        rgb = np.stack([r, g, b], axis=-1).astype(np.uint8)
        rgb[missing] = 128  # gray for missing data
        return rgb
    
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


def main(argv=None):
    """Run the visualizer on its own.

        python -m scanner.S_param_visualizer [scan.h5]

    With no argument the window opens empty and the only live control is
    Import -- no modal file dialog blocks startup, so the window is always
    there to look at. A path given on the command line is loaded straight away.
    """
    from PySide6.QtWidgets import QApplication

    argv = sys.argv if argv is None else argv
    app = QApplication.instance() or QApplication(argv)

    path = argv[1] if len(argv) > 1 else None
    if path and not os.path.isfile(path):
        print(f"Warning: {path} not found; opening empty.")

    window = VisualizerWindow(path)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
