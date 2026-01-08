from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGraphicsView, QGraphicsScene
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import (
    QPen, QPainter, QPalette, QPainterPath
)
from PySide6.QtWidgets import QPushButton,  QHBoxLayout
from PySide6.QtGui import QFont
import time
import math
from PySide6.QtGui import QFontMetrics


LANES = [
    ("VNA", Qt.blue),
    ("Motor", Qt.green),
    ("File I/O", Qt.yellow),
    ("Scan Pattern", Qt.cyan),
]
LANE_COLORS_DARK = {
    "VNA": Qt.cyan,
    "Motor": Qt.green,
    "File I/O": Qt.yellow,
    "Scan Pattern": Qt.magenta,
}

LANE_COLORS_LIGHT = {
    "VNA": Qt.blue,
    "Motor": Qt.darkGreen,
    "File I/O": Qt.darkYellow,
    "Scan Pattern": Qt.darkMagenta,
}

LANE_PHASES = {
    "VNA": 0.00,
    "Motor": 0.5,
    "File I/O": 1,
    "Scan Pattern": 1.81,
}


LANE_HEIGHT = 200
PIXELS_PER_SEC = 500
VIEW_WIDTH = 1920
VIEW_HEIGHT = LANE_HEIGHT * len(LANES)
WAVE_WAVELENGTH = 80.0
WAVE_SPEED = 100.0
OVERLAY_TOP_MARGIN = 50 



# -------------------------------
# Custom Graphics View (IMPORTANT)
# -------------------------------
class ScopeView(QGraphicsView):
    def __init__(self, scope):
        super().__init__()
        self.scope = scope
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setRenderHint(QPainter.Antialiasing, False)
        self.setMouseTracking(True)

    def drawForeground(self, painter: QPainter, rect):
        painter.save()
        painter.resetTransform()
        
        #t = time.perf_counter() - self.scope.start_time - self.scope.time_offset
        t = self.scope._current_scope_time()


        self.scope._draw_lane_labels(painter)
        self.scope._draw_marker(painter)
        self.scope._draw_time_readout(painter, t)
        self.scope._draw_error_banner(painter)
        self.scope._draw_delta_phase_table(painter, t)
        
        painter.restore()

    def mousePressEvent(self, event):
        if self.scope.marker_enabled:
            self.scope.marker_x = event.position().x()
            self.scope.dragging_marker = True
            self.viewport().update()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.scope.dragging_marker:
            self.scope.marker_x = event.position().x()
            self.viewport().update()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.scope.dragging_marker = False
        super().mouseReleaseEvent(event)




# -------------------------------
# Signal Scope Window
# -------------------------------
class SignalScope(QWidget):
    def __init__(self):
        super().__init__(None)
        self.paused = False
        self.pause_time = None
        self.time_offset = 0.0
        self.marker_enabled = False
        self.marker_x = None
        self.dragging_marker = False
        self.error_frozen = False
        self.error_message = None
        self.error_time = None
        self.error_lane = None   # e.g. "VNA", "Motor", "File I/O", "Scan Pattern"

        self.setFocusPolicy(Qt.StrongFocus)


        self.setWindowTitle("Signal Scope")
        self.setWindowFlags(Qt.Window)
        self.resize(VIEW_WIDTH, VIEW_HEIGHT + 20)

        layout = QVBoxLayout(self)

        self.scene = QGraphicsScene()
        self.scene.setSceneRect(0, 0, VIEW_WIDTH, VIEW_HEIGHT)

        self.view = ScopeView(self)
        self.view.setScene(self.scene)
        layout.addWidget(self.view)

        self.start_time = time.perf_counter()

        self.timer = QTimer()
        self.timer.timeout.connect(self._tick)
        self.timer.start(16)  # ~60 Hz

        # self.pause_btn = QPushButton("Pause")
        # self.pause_btn.setCheckable(True)
        # self.pause_btn.clicked.connect(self.toggle_pause)

        # layout.addWidget(self.pause_btn)
        
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(4, 4, 4, 4)
        top_bar.setSpacing(4)

        self.pause_btn = QPushButton("⏸")
        self.pause_btn.setCheckable(True)
        self.pause_btn.setFixedSize(28, 28)
        self.pause_btn.setToolTip("Pause / Resume")
        self.pause_btn.clicked.connect(self.toggle_pause)

        top_bar.addWidget(self.pause_btn)
        
        top_bar.addStretch()
        
        self.marker_btn = QPushButton("│")
        self.marker_btn.setFixedSize(28, 28)
        self.marker_btn.setToolTip("Create / Remove Marker")
        self.marker_btn.setCheckable(True)
        self.marker_btn.clicked.connect(self.toggle_marker)

        self.marker_btn.setFocusPolicy(Qt.NoFocus)
        self.marker_btn.setFlat(True)

        top_bar.addWidget(self.marker_btn)


        layout.insertLayout(0, top_bar)
    # -------------------------------
    # Theme helpers
    # -------------------------------
    def _is_dark_theme(self):
        bg = self.palette().color(QPalette.Window)
        return bg.lightness() < 128

    def _baseline_pen(self):
        color = Qt.white if self._is_dark_theme() else Qt.black
        pen = QPen(color)
        pen.setWidthF(0.6)
        return pen

    def _border_pen(self):
        color = Qt.white if self._is_dark_theme() else Qt.black
        pen = QPen(color)
        pen.setWidthF(0.5)
        pen.setCapStyle(Qt.FlatCap)
        return pen

    def _tick_pen(self, major=False):
        color = Qt.white if self._is_dark_theme() else Qt.black
        pen = QPen(color)
        pen.setWidthF(0.75 if major else 0.5)
        pen.setCapStyle(Qt.FlatCap)
        return pen

    def _lane_color(self, lane_name: str):
        if self._is_dark_theme():
            return LANE_COLORS_DARK[lane_name]
        else:
            return LANE_COLORS_LIGHT[lane_name]
    def create_marker(self):
        # Place marker at fixed screen position (e.g. 60% width)
        self.marker_x = int(self.view.viewport().width() * 0.6)
        self.marker_enabled = True
        self.view.viewport().update()
        
    def _marker_pen(self):
        color = Qt.white if self._is_dark_theme() else Qt.black
        pen = QPen(color)
        pen.setWidthF(5)
        pen.setCapStyle(Qt.FlatCap)
        return pen
    
    def toggle_marker(self, checked):
        if checked:
            # enable marker, wait for click to place
            self.marker_enabled = True
            self.marker_x = None
        else:
            # remove marker
            self.marker_enabled = False
            self.marker_x = None
            self.dragging_marker = False

        self.view.viewport().update()

    def keyPressEvent(self, event):
        key = event.key()

        # Pause / Resume
        if key == Qt.Key_Space:
            self.toggle_pause(not self.paused)
            self.pause_btn.setChecked(self.paused)
            return

        # Toggle marker
        if key == Qt.Key_M:
            new_state = not self.marker_enabled
            self.marker_btn.setChecked(new_state)   
            self.toggle_marker(new_state)
            return

        # Clear marker
        if key == Qt.Key_Escape:
            if self.marker_enabled:
                self.marker_enabled = False
                self.marker_x = None
                self.marker_btn.setChecked(False)
                self.view.viewport().update()
            return
        # Simulate error (DEV ONLY)
        if key == Qt.Key_E:
            mods = event.modifiers()

            if mods & Qt.ShiftModifier:
                lane = "Motor"
                msg = "Motor fault (simulated)"
            elif mods & Qt.ControlModifier:
                lane = "File I/O"
                msg = "File write error (simulated)"
            elif mods & Qt.AltModifier:
                lane = "Scan Pattern"
                msg = "Pattern generation error (simulated)"
            else:
                lane = "VNA"
                msg = "VNA timeout (simulated)"

            self.freeze_on_error(msg, lane)
            return
        if key == Qt.Key_Escape and event.modifiers() & Qt.ShiftModifier:
            self.clear_error()
            return

        # Marker nudging
        if self.marker_enabled and self.marker_x is not None:
            step = 10
            if event.modifiers() & Qt.ShiftModifier:
                step = 2

            if key == Qt.Key_Left:
                self.marker_x -= step
                self.view.viewport().update()
                return

            if key == Qt.Key_Right:
                self.marker_x += step
                self.view.viewport().update()
                return

        super().keyPressEvent(event)

    def _draw_marker(self, painter: QPainter):
        if not self.marker_enabled or self.marker_x is None:
            return

        pen = self._marker_pen()
        painter.setPen(pen)

        height = self.view.viewport().height()
        x = int(self.marker_x)

        painter.drawLine(x, 0, x, height)
        
    def _compute_delta_phases(self, t):
        ref = "VNA"
        ref_phase = self._lane_phase_at_marker(ref, t)

        deltas = {}

        for name, _ in LANES:
            phase = self._lane_phase_at_marker(name, t)
            delta = (phase - ref_phase) * 360.0
            deltas[name] = delta

        return deltas
    def _draw_delta_phase_table(self, painter: QPainter, t):
        if not self.marker_enabled or self.marker_x is None:
            return

        deltas = self._compute_delta_phases(t)

        painter.setFont(self._label_font())
        painter.setPen(self._label_pen())

        x0 = 60          # left margin
        y0 = 6           # top margin
        row_h = 16

        painter.drawText(x0, y0 + row_h, "ΔPhase (deg) wrt VNA")

        for i, (name, _) in enumerate(LANES):
            if name == "VNA":
                continue

            text = f"{name:12s}: {deltas[name]:6.1f}°"
            painter.drawText(x0, y0 + row_h * (i + 2), text)

    def _lane_phase_at_marker(self, lane_name, t):
        phase_offset = LANE_PHASES[lane_name] * WAVE_WAVELENGTH
        x = self.marker_x

        phase = ((x + phase_offset + t * WAVE_SPEED) % WAVE_WAVELENGTH) / WAVE_WAVELENGTH
        return phase

    def _time_at_marker(self, t_now):
        """
        Returns time (seconds since start) at marker x-position.
        """
        width = self.view.viewport().width()
        visible_time = width / PIXELS_PER_SEC

        # marker_x is in screen space
        frac = self.marker_x / width
        t_at_marker = t_now - (1.0 - frac) * visible_time
        return t_at_marker
    
    def _draw_time_readout(self, painter: QPainter, t_now):
        if not self.marker_enabled or self.marker_x is None:
            return

        t_marker = self._time_at_marker(t_now)

        painter.setFont(self._label_font())
        painter.setPen(self._label_pen())

        text = f"t = {t_marker:0.4f} s"

        # Draw slightly above the top border
        x = int(self.marker_x + 6)
        y = 14

        painter.drawText(x, y, text)
    def _current_scope_time(self):
        if self.paused:
            return self.pause_time - self.start_time - self.time_offset
        else:
            return time.perf_counter() - self.start_time - self.time_offset
    # -------------------------------
    # Main animation tick
    # -------------------------------
    def _tick(self):
        t = self._current_scope_time()

        x_offset = t * PIXELS_PER_SEC
        self.view.resetTransform()
        self.view.translate(-x_offset + VIEW_WIDTH * 0.85, 0)

        self.scene.clear()
        self._draw_waves(t)
        self._draw_lane_borders()
        self._draw_fake_impulses(t)

        self.view.viewport().update()

        
    def toggle_pause(self, checked):
        if checked:
            self.paused = True
            self.pause_time = time.perf_counter()
            self.pause_btn.setText("▶")
        else:
            resume_time = time.perf_counter()
            self.time_offset += resume_time - self.pause_time
            self.paused = False
            self.pause_time = None
            self.pause_btn.setText("⏸")


    # -------------------------------
    # Drawing routines
    # -------------------------------
    def _draw_waves(self, t):
        amplitude = LANE_HEIGHT * 0.25
        wavelength = 80.0
        speed = 100.0

        for i, (name, color) in enumerate(LANES):
            y0 = i * LANE_HEIGHT + LANE_HEIGHT // 2

            lane_color = self._lane_color(name)
            pen = QPen(lane_color)
            if self._lane_is_error(name):
                pen.setWidthF(10)          # emphasized
            else:
                pen.setWidthF(5)
            
            pen.setCapStyle(Qt.FlatCap)
            lane_color = self._lane_color(name)

           


            pen.setCapStyle(Qt.FlatCap)
            if self.error_frozen and not self._lane_is_error(name):
                c = pen.color()
                c.setAlpha(80)   # dim
                pen.setColor(c)


            path = QPainterPath()
            path.moveTo(0, y0)

            prev_level = None
            phase_offset = LANE_PHASES[name] * wavelength

            for x in range(0, VIEW_WIDTH, 4):
                phase = ((x + phase_offset + t * speed) % wavelength) / wavelength
                level = amplitude if phase < 0.5 else -amplitude

                if prev_level is not None and level != prev_level:
                    path.lineTo(x, y0 + prev_level)

                path.lineTo(x, y0 + level)
                prev_level = level

            self.scene.addPath(path, pen)




    def _draw_lane_borders(self):
        pen = self._border_pen()

        for i, (name, _) in enumerate(LANES):
            y_top = i * LANE_HEIGHT
            y_bot = y_top + LANE_HEIGHT

            pen = self._border_pen()

            if self._lane_is_error(name):
                pen.setWidthF(2.0)
                pen.setColor(Qt.red)

            self.scene.addLine(0, y_top, VIEW_WIDTH, y_top, pen)
            self.scene.addLine(0, y_bot, VIEW_WIDTH, y_bot, pen)



    def _draw_fake_impulses(self, t):
        if int(t * 10) % 10 != 0:
            return

        lane_index = int(t) % len(LANES)
        _, color = LANES[lane_index]

        x = t * PIXELS_PER_SEC
        y_center = lane_index * LANE_HEIGHT + LANE_HEIGHT // 2

        pen = QPen(color)
        pen.setWidthF(1.0)
        pen.setCapStyle(Qt.FlatCap)

        self.scene.addLine(
            x, y_center - 18,
            x, y_center + 18,
            pen
        )


    # -------------------------------
    # Static time ruler (foreground)
    # -------------------------------
    def _draw_static_time_ticks(self, painter: QPainter, width: int, height: int):
        pen_minor = self._tick_pen(False)
        pen_major = self._tick_pen(True)

        seconds_per_minor = 0.1
        seconds_per_major = 1.0

        pixels_per_sec = PIXELS_PER_SEC

        # Right edge = "now"
        t_now = time.perf_counter() - self.start_time

        visible_time = width / pixels_per_sec
        t_start = t_now - visible_time

        t = t_start - (t_start % seconds_per_minor)

        while t < t_now:
            x = int((t - t_start) * pixels_per_sec)

            is_major = abs(t % seconds_per_major) < 1e-3
            pen = pen_major if is_major else pen_minor
            tick_len = 14 if is_major else 7

            painter.setPen(pen)
            painter.drawLine(x, 0, x, tick_len)
        
            t += seconds_per_minor

    def _label_pen(self):
        return Qt.white if self._is_dark_theme() else Qt.black

    def _label_font(self):
        font = QFont("Segoe UI")  # or default
        font.setPointSize(10)
        font.setBold(True)
        return font
    def _draw_lane_labels(self, painter: QPainter):
        painter.setPen(self._label_pen())
        painter.setFont(self._label_font())

        x_margin = 8
        y_margin = 14   # distance from top border into lane

        for i, (name, _) in enumerate(LANES):
            y_top = i * LANE_HEIGHT

            painter.drawText(
                x_margin,
                y_top + y_margin,
                name
            )
    #### Error Checking
    def freeze_on_error(self, message: str, lane: str):
        if self.error_frozen:
            return

        self.error_frozen = True
        self.error_message = message
        self.error_lane = lane
        self.error_time = self._current_scope_time()

        # Pause scope
        if not self.paused:
            self.toggle_pause(True)
            self.pause_btn.setChecked(True)

        # Enable marker at "now"
        self.marker_enabled = True
        self.marker_btn.setChecked(True)
        self.marker_x = int(self.view.viewport().width() * 0.85)

        self.view.viewport().update()

        
    def _draw_error_banner(self, painter: QPainter):
        if not self.error_frozen:
            return

        painter.setFont(self._label_font())
        painter.setPen(Qt.red)

        text = f"ERROR [{self.error_lane}]: {self.error_message}"

        x = 10
        y = OVERLAY_TOP_MARGIN - 8   # sits clearly above lanes

        painter.drawText(x, y, text)


    def clear_error(self):
        self.error_frozen = False
        self.error_message = None
        self.error_lane = None
        self.error_time = None
        self.view.viewport().update()

    
    def _lane_is_error(self, lane_name):
        return self.error_frozen and self.error_lane == lane_name

