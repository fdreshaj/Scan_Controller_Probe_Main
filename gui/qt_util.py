
from functools import wraps
import math

from PySide6.QtGui import QFocusEvent
from PySide6.QtWidgets import QSlider, QWidget, QLineEdit, QCompleter
from PySide6.QtCore import Qt, Slot

from scanner.plugin_setting import PluginSetting, PluginSettingString


class QPluginSetting(QLineEdit):
    _setting: PluginSetting
    _style_no_error: str

    def __init__(self, setting: PluginSetting, parent: QWidget | None = None) -> None:
        super().__init__(setting.get_value_as_string(), parent)
        self.setSetting(setting)
        self._style_no_error = self.styleSheet()
        self.textChanged.connect(self.text_changed_handler)

    def text_changed_handler(self, text: str) -> None:
        try:
            self._setting.set_value_from_string(text)
        except ValueError as ex:
            self.setStyleSheet("border: 2px solid red;")
            self.setToolTip(str(ex))
        else:
            self.setStyleSheet(self._style_no_error)
            self.setToolTip("")
    
    def setSetting(self, setting: PluginSetting):
        self._setting = setting
        if setting.read_only:
            self.setReadOnly(True)
        hints = setting.get_hints()
        if hints:
            comp = QCompleter(hints)
            comp.setCompletionMode(QCompleter.CompletionMode.UnfilteredPopupCompletion)
            self.setCompleter(comp)
    
    def focusInEvent(self, event: QFocusEvent) -> None:
        comp = self.completer()
        if comp is not None:
            self.completer().setCompletionPrefix("")
            self.completer().complete()
        return super().focusInEvent(event)



class QAxisPositionSlider(QSlider):
    _SLIDER_RESOLUTION: int = 1000000

    current_value: float
    endstop_minimum: float
    endstop_maximum: float

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.endstop_minimum = float(self.minimum())
        self.endstop_maximum = float(self.maximum())
        
        slider_min = self.minimum()
        slider_max = self.maximum()
        slider_val = self.sliderPosition()

        self.current_value = (slider_val-slider_min) / (slider_max-slider_min)

        super().setMinimum(0)
        super().setMaximum(self._SLIDER_RESOLUTION)
    
    @Slot(float)
    def setSliderPosition(self, value: float) -> None:
        slider_range = self.endstop_maximum - self.endstop_minimum
        if slider_range <= 0 or not math.isfinite(slider_range):
            self.setDisabled(True)
        self.current_value = max(min(value, self.endstop_maximum), self.endstop_minimum)
        set_val = int((self.current_value - self.endstop_minimum) / slider_range * self._SLIDER_RESOLUTION)
        super().setSliderPosition(set_val)
        

    @Slot(float)
    def setMinimum(self, min_value: float) -> None:
        self.endstop_minimum = min_value
        self.setSliderPosition(self.current_value)

    @Slot(float)
    def setMaximum(self, max_value: float) -> None:
        self.endstop_maximum = max_value
        self.setSliderPosition(self.current_value)








