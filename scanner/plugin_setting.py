
from abc import ABC, abstractmethod

class PluginSetting(ABC):
    display_label: str
    read_only: bool

    def __init__(self, display_label: str, read_only: bool = False) -> None:
        self.display_label = display_label
        self.read_only = read_only
    
    @abstractmethod
    def set_value_from_string(self, value: str) -> None:
        pass

    @abstractmethod
    def get_value_as_string(self) -> str:
        pass

    def get_hints(self) -> tuple[str, ...]:
        return ()
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}('{self.display_label}', '{self.get_value_as_string()}')"




class PluginSettingString(PluginSetting):
    _value: str
    selection_options: list[str]
    restrict_selections: bool

    def __init__(self, display_label: str, default_value: str, read_only: bool = False, select_options: list[str] = [], restrict_selections: bool = False) -> None:
        super().__init__(display_label, read_only)
        self.selection_options = list(select_options)
        self.restrict_selections = restrict_selections
        self.value = default_value

    def set_value_from_string(self, value: str) -> None:
        self.value = value

    def get_value_as_string(self) -> str:
        return self.value
    
    def get_hints(self) -> tuple[str, ...]:
        return tuple(self.selection_options)

    @property
    def value(self) -> str:
        return self._value
    
    @value.setter
    def value(self, value: str) -> None:
        if self.restrict_selections and value not in self.selection_options:
            raise ValueError(f"Value must be one of {self.selection_options}.")
        self._value = value


class PluginSettingInteger(PluginSetting):
    _value: int
    _value_min: int | None
    _value_max: int | None

    def __init__(self, display_label: str, default_value: int, read_only: bool = False, value_min: int | None = None, value_max: int | None = None) -> None:
        super().__init__(display_label, read_only)
        self._value_min = value_min
        self._value_max = value_max
        if value_min is not None and value_max is not None and value_min > value_max:
            raise ValueError("Value minimum cannot be greater than the maximum.")
        self.value = int(default_value)

    def set_value_from_string(self, value: str) -> None:
        self.value = int(value)

    def get_value_as_string(self) -> str:
        return f"{self._value}"
    
    @property
    def value(self) -> int:
        return self._value

    @value.setter
    def value(self, value: int) -> None:
        if self._value_min is not None and value < self._value_min:
            raise ValueError(f"Value must not be less than {self._value_min}.")
        if self._value_max is not None and value > self._value_max:
            raise ValueError(f"Value must not be greater than {self._value_max}.")
        self._value = value
    
    @property
    def value_min(self) -> int | None:
        return self._value_min
    
    @property
    def value_max(self) -> int | None:
        return self._value_max


class PluginSettingFloat(PluginSetting):
    _value: float
    _value_min: float | None
    _value_max: float | None

    def __init__(self, display_label: str, default_value: float, read_only: bool = False, value_min: float | None = None, value_max: float | None = None) -> None:
        super().__init__(display_label, read_only)
        self._value_min = value_min
        self._value_max = value_max
        if value_min is not None and value_max is not None and value_min > value_max:
            raise ValueError("Value minimum cannot be greater than the maximum.")
        self.value = default_value

    def set_value_from_string(self, value: str) -> None:
        self.value = float(value)

    def get_value_as_string(self) -> str:
        return f"{self._value}"
    
    @property
    def value(self) -> float:
        return self._value
    
    @value.setter
    def value(self, value: float) -> None:
        if self._value_min is not None and value < self._value_min:
            raise ValueError(f"Value must not be less than {self._value_min}.")
        if self._value_max is not None and value > self._value_max:
            raise ValueError(f"Value must not be greater than {self._value_max}.")
        self._value = value
    
    @property
    def value_min(self) -> float | None:
        return self._value_min
    
    @property
    def value_max(self) -> float | None:
        return self._value_max


