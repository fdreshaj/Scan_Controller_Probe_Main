# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'ui_scanner.ui'
##
## Created by: Qt User Interface Compiler version 6.7.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDoubleSpinBox,
    QFormLayout, QFrame, QGridLayout, QLabel,
    QLayout, QLineEdit, QMainWindow, QMenuBar,
    QProgressBar, QPushButton, QSizePolicy, QSlider,
    QStatusBar, QTabWidget, QTextEdit, QWidget)

from gui.qt_util import QAxisPositionSlider

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(1120, 623)
        MainWindow.setAnimated(False)
        MainWindow.setDocumentMode(True)
        MainWindow.setTabShape(QTabWidget.Triangular)
        self.central_widget = QWidget(MainWindow)
        self.central_widget.setObjectName(u"central_widget")
        self.gridLayoutWidget_6 = QWidget(self.central_widget)
        self.gridLayoutWidget_6.setObjectName(u"gridLayoutWidget_6")
        self.gridLayoutWidget_6.setGeometry(QRect(20, 10, 1041, 551))
        self.main_layout = QGridLayout(self.gridLayoutWidget_6)
        self.main_layout.setObjectName(u"main_layout")
        self.main_layout.setSizeConstraint(QLayout.SetDefaultConstraint)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.config_layout = QFormLayout()
        self.config_layout.setObjectName(u"config_layout")

        self.main_layout.addLayout(self.config_layout, 2, 4, 1, 1)

        self.diplay_layout = QGridLayout()
        self.diplay_layout.setObjectName(u"diplay_layout")
        self.y_axis_slider = QAxisPositionSlider(self.gridLayoutWidget_6)
        self.y_axis_slider.setObjectName(u"y_axis_slider")
        self.y_axis_slider.setMinimum(-100)
        self.y_axis_slider.setMaximum(100)
        self.y_axis_slider.setOrientation(Qt.Vertical)
        self.y_axis_slider.setTickPosition(QSlider.TicksAbove)
        self.y_axis_slider.setTickInterval(50000)

        self.diplay_layout.addWidget(self.y_axis_slider, 0, 1, 1, 1)

        self.x_axis_slider = QAxisPositionSlider(self.gridLayoutWidget_6)
        self.x_axis_slider.setObjectName(u"x_axis_slider")
        self.x_axis_slider.setMinimum(-100)
        self.x_axis_slider.setMaximum(100)
        self.x_axis_slider.setOrientation(Qt.Horizontal)
        self.x_axis_slider.setInvertedAppearance(False)
        self.x_axis_slider.setTickPosition(QSlider.TicksAbove)
        self.x_axis_slider.setTickInterval(50000)

        self.diplay_layout.addWidget(self.x_axis_slider, 1, 0, 1, 1)

        self.xy_canvas = QWidget(self.gridLayoutWidget_6)
        self.xy_canvas.setObjectName(u"xy_canvas")

        self.diplay_layout.addWidget(self.xy_canvas, 0, 0, 1, 1)


        self.main_layout.addLayout(self.diplay_layout, 2, 0, 1, 1)

        self.xy_move_layout = QGridLayout()
        self.xy_move_layout.setObjectName(u"xy_move_layout")
        self.x_plus_button = QPushButton(self.gridLayoutWidget_6)
        self.x_plus_button.setObjectName(u"x_plus_button")

        self.xy_move_layout.addWidget(self.x_plus_button, 1, 2, 1, 1)

        self.y_plus_button = QPushButton(self.gridLayoutWidget_6)
        self.y_plus_button.setObjectName(u"y_plus_button")

        self.xy_move_layout.addWidget(self.y_plus_button, 0, 1, 1, 1)

        self.y_minus_button = QPushButton(self.gridLayoutWidget_6)
        self.y_minus_button.setObjectName(u"y_minus_button")

        self.xy_move_layout.addWidget(self.y_minus_button, 2, 1, 1, 1)

        self.xy_move_amount = QDoubleSpinBox(self.gridLayoutWidget_6)
        self.xy_move_amount.setObjectName(u"xy_move_amount")
        self.xy_move_amount.setDecimals(5)
        self.xy_move_amount.setMinimum(-1000000000000000.000000000000000)
        self.xy_move_amount.setMaximum(1000000000000000.000000000000000)
        self.xy_move_amount.setValue(10.000000000000000)

        self.xy_move_layout.addWidget(self.xy_move_amount, 1, 1, 1, 1)

        self.x_minus_button = QPushButton(self.gridLayoutWidget_6)
        self.x_minus_button.setObjectName(u"x_minus_button")

        self.xy_move_layout.addWidget(self.x_minus_button, 1, 0, 1, 1)


        self.main_layout.addLayout(self.xy_move_layout, 0, 0, 1, 1)

        self.settings_layout = QGridLayout()
        self.settings_layout.setObjectName(u"settings_layout")
        self.configure_file_button = QPushButton(self.gridLayoutWidget_6)
        self.configure_file_button.setObjectName(u"configure_file_button")
        self.configure_file_button.setCheckable(True)

        self.settings_layout.addWidget(self.configure_file_button, 3, 2, 1, 1)

        self.configure_motion_label = QLabel(self.gridLayoutWidget_6)
        self.configure_motion_label.setObjectName(u"configure_motion_label")

        self.settings_layout.addWidget(self.configure_motion_label, 0, 0, 1, 1)

        self.configure_motion_button = QPushButton(self.gridLayoutWidget_6)
        self.configure_motion_button.setObjectName(u"configure_motion_button")
        self.configure_motion_button.setCheckable(True)

        self.settings_layout.addWidget(self.configure_motion_button, 0, 2, 1, 1)

        self.configure_file_label = QLabel(self.gridLayoutWidget_6)
        self.configure_file_label.setObjectName(u"configure_file_label")

        self.settings_layout.addWidget(self.configure_file_label, 3, 0, 1, 1)

        self.configure_probe_label = QLabel(self.gridLayoutWidget_6)
        self.configure_probe_label.setObjectName(u"configure_probe_label")

        self.settings_layout.addWidget(self.configure_probe_label, 1, 0, 1, 1)

        self.configure_pattern_label = QLabel(self.gridLayoutWidget_6)
        self.configure_pattern_label.setObjectName(u"configure_pattern_label")

        self.settings_layout.addWidget(self.configure_pattern_label, 2, 0, 1, 1)

        self.configure_probe_button = QPushButton(self.gridLayoutWidget_6)
        self.configure_probe_button.setObjectName(u"configure_probe_button")
        self.configure_probe_button.setCheckable(True)

        self.settings_layout.addWidget(self.configure_probe_button, 1, 2, 1, 1)

        self.configure_pattern_button = QPushButton(self.gridLayoutWidget_6)
        self.configure_pattern_button.setObjectName(u"configure_pattern_button")
        self.configure_pattern_button.setCheckable(True)

        self.settings_layout.addWidget(self.configure_pattern_button, 2, 2, 1, 1)

        self.checkBox = QCheckBox(self.gridLayoutWidget_6)
        self.checkBox.setObjectName(u"checkBox")
        self.checkBox.setCheckable(False)

        self.settings_layout.addWidget(self.checkBox, 1, 1, 1, 1)

        self.motion_connected_checkbox = QCheckBox(self.gridLayoutWidget_6)
        self.motion_connected_checkbox.setObjectName(u"motion_connected_checkbox")
        self.motion_connected_checkbox.setCheckable(False)

        self.settings_layout.addWidget(self.motion_connected_checkbox, 0, 1, 1, 1)


        self.main_layout.addLayout(self.settings_layout, 2, 2, 1, 1)

        self.line_3 = QFrame(self.gridLayoutWidget_6)
        self.line_3.setObjectName(u"line_3")
        self.line_3.setFrameShape(QFrame.Shape.VLine)
        self.line_3.setFrameShadow(QFrame.Shadow.Sunken)

        self.main_layout.addWidget(self.line_3, 2, 1, 1, 1)

        self.line_2 = QFrame(self.gridLayoutWidget_6)
        self.line_2.setObjectName(u"line_2")
        self.line_2.setFrameShape(QFrame.Shape.VLine)
        self.line_2.setFrameShadow(QFrame.Shadow.Sunken)

        self.main_layout.addWidget(self.line_2, 0, 1, 1, 1)

        self.scan_layout = QGridLayout()
        self.scan_layout.setObjectName(u"scan_layout")
        self.scan_description_box = QTextEdit(self.gridLayoutWidget_6)
        self.scan_description_box.setObjectName(u"scan_description_box")

        self.scan_layout.addWidget(self.scan_description_box, 0, 1, 1, 1)

        self.time_remaining_label = QLabel(self.gridLayoutWidget_6)
        self.time_remaining_label.setObjectName(u"time_remaining_label")

        self.scan_layout.addWidget(self.time_remaining_label, 4, 0, 1, 1)

        self.start_scan_button = QPushButton(self.gridLayoutWidget_6)
        self.start_scan_button.setObjectName(u"start_scan_button")

        self.scan_layout.addWidget(self.start_scan_button, 0, 0, 1, 1)

        self.time_elapsed_label = QLabel(self.gridLayoutWidget_6)
        self.time_elapsed_label.setObjectName(u"time_elapsed_label")

        self.scan_layout.addWidget(self.time_elapsed_label, 2, 0, 1, 1)

        self.time_elapsed_box = QLineEdit(self.gridLayoutWidget_6)
        self.time_elapsed_box.setObjectName(u"time_elapsed_box")
        self.time_elapsed_box.setEnabled(True)
        self.time_elapsed_box.setReadOnly(True)

        self.scan_layout.addWidget(self.time_elapsed_box, 2, 1, 1, 1)

        self.time_remaining_box = QLineEdit(self.gridLayoutWidget_6)
        self.time_remaining_box.setObjectName(u"time_remaining_box")
        self.time_remaining_box.setReadOnly(True)

        self.scan_layout.addWidget(self.time_remaining_box, 4, 1, 1, 1)

        self.scan_progress_bar = QProgressBar(self.gridLayoutWidget_6)
        self.scan_progress_bar.setObjectName(u"scan_progress_bar")
        self.scan_progress_bar.setValue(50)

        self.scan_layout.addWidget(self.scan_progress_bar, 1, 0, 1, 2)


        self.main_layout.addLayout(self.scan_layout, 0, 4, 1, 1)

        self.z_move_layout = QGridLayout()
        self.z_move_layout.setObjectName(u"z_move_layout")
        self.z_plus_button = QPushButton(self.gridLayoutWidget_6)
        self.z_plus_button.setObjectName(u"z_plus_button")

        self.z_move_layout.addWidget(self.z_plus_button, 1, 0, 1, 1)

        self.z_minus_button = QPushButton(self.gridLayoutWidget_6)
        self.z_minus_button.setObjectName(u"z_minus_button")

        self.z_move_layout.addWidget(self.z_minus_button, 3, 0, 1, 1)

        self.z_move_amount = QDoubleSpinBox(self.gridLayoutWidget_6)
        self.z_move_amount.setObjectName(u"z_move_amount")
        self.z_move_amount.setDecimals(5)
        self.z_move_amount.setMinimum(-100000000000000000.000000000000000)
        self.z_move_amount.setMaximum(100000000000000000.000000000000000)
        self.z_move_amount.setValue(10.000000000000000)

        self.z_move_layout.addWidget(self.z_move_amount, 2, 0, 1, 1)

        self.z_axis_select = QComboBox(self.gridLayoutWidget_6)
        self.z_axis_select.setObjectName(u"z_axis_select")

        self.z_move_layout.addWidget(self.z_axis_select, 0, 0, 1, 1)

        self.z_axis_slider = QAxisPositionSlider(self.gridLayoutWidget_6)
        self.z_axis_slider.setObjectName(u"z_axis_slider")
        self.z_axis_slider.setMinimum(-100)
        self.z_axis_slider.setMaximum(100)
        self.z_axis_slider.setOrientation(Qt.Vertical)
        self.z_axis_slider.setTickPosition(QSlider.TicksAbove)
        self.z_axis_slider.setTickInterval(50000)

        self.z_move_layout.addWidget(self.z_axis_slider, 1, 1, 3, 1)


        self.main_layout.addLayout(self.z_move_layout, 0, 2, 1, 1)

        self.line_4 = QFrame(self.gridLayoutWidget_6)
        self.line_4.setObjectName(u"line_4")
        self.line_4.setFrameShape(QFrame.Shape.VLine)
        self.line_4.setFrameShadow(QFrame.Shadow.Sunken)

        self.main_layout.addWidget(self.line_4, 2, 3, 1, 1)

        self.line_5 = QFrame(self.gridLayoutWidget_6)
        self.line_5.setObjectName(u"line_5")
        self.line_5.setFrameShape(QFrame.Shape.VLine)
        self.line_5.setFrameShadow(QFrame.Shadow.Sunken)

        self.main_layout.addWidget(self.line_5, 0, 3, 1, 1)

        self.line_6 = QFrame(self.gridLayoutWidget_6)
        self.line_6.setObjectName(u"line_6")
        self.line_6.setFrameShape(QFrame.Shape.HLine)
        self.line_6.setFrameShadow(QFrame.Shadow.Sunken)

        self.main_layout.addWidget(self.line_6, 1, 2, 1, 1)

        self.line = QFrame(self.gridLayoutWidget_6)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFrameShadow(QFrame.Shadow.Sunken)

        self.main_layout.addWidget(self.line, 1, 0, 1, 1)

        self.line_8 = QFrame(self.gridLayoutWidget_6)
        self.line_8.setObjectName(u"line_8")
        self.line_8.setFrameShape(QFrame.Shape.HLine)
        self.line_8.setFrameShadow(QFrame.Shadow.Sunken)

        self.main_layout.addWidget(self.line_8, 1, 4, 1, 1)

        MainWindow.setCentralWidget(self.central_widget)
        self.menubar = QMenuBar(MainWindow)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 1120, 22))
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(MainWindow)
        self.statusbar.setObjectName(u"statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)

        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"MainWindow", None))
        self.x_plus_button.setText(QCoreApplication.translate("MainWindow", u"X+", None))
        self.y_plus_button.setText(QCoreApplication.translate("MainWindow", u"Y+", None))
        self.y_minus_button.setText(QCoreApplication.translate("MainWindow", u"Y-", None))
        self.x_minus_button.setText(QCoreApplication.translate("MainWindow", u"X-", None))
        self.configure_file_button.setText(QCoreApplication.translate("MainWindow", u"Configure", None))
        self.configure_motion_label.setText(QCoreApplication.translate("MainWindow", u"Motion Control", None))
        self.configure_motion_button.setText(QCoreApplication.translate("MainWindow", u"Configure", None))
        self.configure_file_label.setText(QCoreApplication.translate("MainWindow", u"Scan File", None))
        self.configure_probe_label.setText(QCoreApplication.translate("MainWindow", u"Probe", None))
        self.configure_pattern_label.setText(QCoreApplication.translate("MainWindow", u"Scan Pattern", None))
        self.configure_probe_button.setText(QCoreApplication.translate("MainWindow", u"Configure", None))
        self.configure_pattern_button.setText(QCoreApplication.translate("MainWindow", u"Configure", None))
        self.checkBox.setText(QCoreApplication.translate("MainWindow", u"Connected", None))
        self.motion_connected_checkbox.setText(QCoreApplication.translate("MainWindow", u"Connected", None))
        self.time_remaining_label.setText(QCoreApplication.translate("MainWindow", u"Time Remaining", None))
        self.start_scan_button.setText(QCoreApplication.translate("MainWindow", u"Start Scan", None))
        self.time_elapsed_label.setText(QCoreApplication.translate("MainWindow", u"Time Elapsed", None))
        self.z_plus_button.setText(QCoreApplication.translate("MainWindow", u"Z+", None))
        self.z_minus_button.setText(QCoreApplication.translate("MainWindow", u"Z-", None))
    # retranslateUi

