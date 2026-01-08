from PySide6.QtWidgets import QWidget, QVBoxLayout, QGraphicsView, QGraphicsScene
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPen
import time
from PySide6.QtGui import QPainter
from PySide6.QtGui import QPalette
from PySide6.QtGui import QPainterPath  
import math

LANES = [
    ("VNA", Qt.blue),
    ("Motor", Qt.green),
    ("File I/O", Qt.yellow),
    ("Scan Pattern", Qt.cyan),
]

LANE_HEIGHT = 200
PIXELS_PER_SEC = 500
VIEW_HEIGHT = LANE_HEIGHT * len(LANES)
VIEW_WIDTH = 1920


class SignalScope(QWidget):
    def __init__(self):
        super().__init__(None)

        self.setWindowTitle("Signal Scope")
        self.setWindowFlags(Qt.Window)
        self.resize(VIEW_WIDTH, VIEW_HEIGHT + 20)

        layout = QVBoxLayout(self)

        self.view = QGraphicsView()
        #self.view.setRenderHint(QPainter.Antialiasing, False)
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        layout.addWidget(self.view)

        self.scene = QGraphicsScene()
        self.view.setScene(self.scene)
        self.scene.setSceneRect(0, 0, VIEW_WIDTH, VIEW_HEIGHT)

        self.start_time = time.perf_counter()

        self._draw_lane_baselines()

        # Fake live scope update
        self.timer = QTimer()
        self.timer.timeout.connect(self._tick)
        self.timer.start(16)  # ~60 Hz

    def _draw_lane_baselines(self):
        self.scene.clear()
        self.baseline_items = []

        pen = self._baseline_pen()

        for i, _ in enumerate(LANES):
            y0 = i * LANE_HEIGHT + LANE_HEIGHT // 2

            path = []
            for x in range(0, VIEW_WIDTH, 6):
                path.append((x, y0))

            self.baseline_items.append((y0, path, pen))

            
    def _tick(self):
        now = time.perf_counter()
        t = now - self.start_time

        x_offset = t * PIXELS_PER_SEC
        self.view.resetTransform()
        self.view.translate(-x_offset + VIEW_WIDTH * 0.8, 0)

        self._draw_waves(t)
        self._draw_fake_impulses(t)

    def _draw_waves(self, t):
        self.scene.clear()

        pen = self._baseline_pen()

        for i, _ in enumerate(LANES):
            y0 = i * LANE_HEIGHT + LANE_HEIGHT // 2

            path = QPainterPath()
            path.moveTo(0, y0)

            for x in range(0, VIEW_WIDTH, 6):
                phase = (x * 0.02) - (t * 4.0)
                y = y0 + math.sin(phase) * 2.0   # subtle wave
                path.lineTo(x, y)

            self.scene.addPath(path, pen)
            
    def _draw_fake_impulses(self, t):
        if int(t * 10) % 10 != 0:
            return

        lane_index = int(t) % len(LANES)
        _, color = LANES[lane_index]

        x = t * PIXELS_PER_SEC
        y_center = lane_index * LANE_HEIGHT + LANE_HEIGHT // 2

        pen = QPen(color)
        pen.setWidthF(0.5)          # thin, crisp impulse
        pen.setCapStyle(Qt.FlatCap)

        self.scene.addLine(
            x, y_center - 12,
            x, y_center + 12,
            pen
        )

    def _is_dark_theme(self):
        bg = self.palette().color(QPalette.Window)
        return bg.lightness() < 128
    
    def _baseline_pen(self):
        if self._is_dark_theme():
            return QPen(Qt.white, 1)
        else:
            return QPen(Qt.black, 1)
