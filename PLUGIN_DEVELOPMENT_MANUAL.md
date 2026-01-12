# Plugin Development Manual
## Scan Controller Probe System

**Version:** 1.0
**Last Updated:** January 2026

---

## Table of Contents

1. [Introduction](#introduction)
2. [Plugin System Overview](#plugin-system-overview)
3. [Probe Plugin Development](#probe-plugin-development)
4. [Motion Controller Plugin Development](#motion-controller-plugin-development)
5. [Plugin Settings System](#plugin-settings-system)
6. [Connection Best Practices](#connection-best-practices)
7. [Testing Your Plugin](#testing-your-plugin)
8. [Common Pitfalls and Troubleshooting](#common-pitfalls-and-troubleshooting)
9. [Quick Reference Templates](#quick-reference-templates)

---

## Introduction

This manual guides lab members through developing custom plugins for the Scan Controller Probe system. The plugin architecture allows you to integrate new probes (VNAs, radars, sensors) and motion controllers without modifying the core system.

### Who Should Read This Manual

- Lab members developing drivers for new instruments
- Researchers integrating custom hardware
- Anyone extending the scanning system capabilities

---

## Plugin System Overview

### Architecture

The system uses two main plugin types:

1. **Probe Plugins** - For measurement instruments (VNAs, sensors, radars)
2. **Motion Controller Plugins** - For positioning systems (motors, stages)

### Plugin Loading

Plugins are loaded dynamically via the Plugin Switcher system:
- Click "Configure" button for Probe or Motion
- Select your plugin `.py` file via file dialog
- Plugin instantiates in pre-connected state
- Configure settings, then connect
- Settings persist across plugin re-instantiation

---

## Probe Plugin Development

### Base Class Requirements

All probe plugins must inherit from `ProbePlugin` and implement the required abstract methods.

### Required Imports

```python
from scanner.probe_controller import ProbePlugin
from scanner.plugin_setting import (
    PluginSettingString,
    PluginSettingInteger,
    PluginSettingFloat
)
```

### Abstract Methods (Must Implement)

#### 1. Connection Management

```python
def connect(self) -> None:
    """
    Establish connection to the probe instrument.

    Best Practice: Use VISA or socket connections for reliability.

    Example:
        - VISA: pyvisa.ResourceManager().open_resource(address)
        - Socket: Custom socket connection via TCP/IP

    This method should:
    - Open communication with the instrument
    - Configure initial instrument settings
    - Query/set frequency ranges (if applicable)
    - Validate connection success
    """
    pass

def disconnect(self) -> None:
    """
    Cleanly close connection to the probe instrument.

    This method should:
    - Close communication channels
    - Release instrument resources
    - Reset any connection state variables
    """
    pass
```

**RECOMMENDED CONNECTION METHODS:**
- **VISA (Preferred):** Most reliable for lab instruments supporting VISA protocol
- **Socket:** For instruments with raw TCP/IP socket interfaces
- **Serial:** For instruments with RS-232/USB serial interfaces

#### 2. Data Description Methods

```python
def get_xaxis_coords(self) -> tuple[float, ...]:
    """
    Return the X-axis coordinates for measurements.

    For VNAs: Return frequency points
    For time-domain: Return time points
    For custom sensors: Return appropriate X-axis values

    Returns:
        tuple of floats representing X-axis measurement points

    Example (from Simplified_VNA_Plugin.py:140-150):
        raw = self.vna.query(":SENS1:FREQ:DATA?")
        if raw.startswith("#"):
            hdr_digits = int(raw[1])
            raw = raw[2 + hdr_digits:]
        parts = re.split(r"[,\s]+", raw.strip())
        return tuple(map(float, parts))
    """
    pass

def get_xaxis_units(self) -> str:
    """
    Return the units for X-axis.

    Returns:
        String representing X-axis units

    Example:
        return "Hz"      # For VNA frequency
        return "s"       # For time-domain
        return "mm"      # For spatial measurements
    """
    pass

def get_yaxis_units(self) -> tuple[str, ...] | str:
    """
    Return the units for Y-axis measurements.

    Returns:
        String or tuple of strings for Y-axis units

    Example:
        return "dB"           # Single unit
        return ("V", "V")     # Multiple channels with same units
    """
    pass

def get_channel_names(self) -> tuple[str, ...]:
    """
    Return names of all measurement channels.

    For VNAs: Return S-parameter names (S11, S21, etc.)
    For multi-channel sensors: Return channel identifiers

    Returns:
        tuple of strings with channel names

    Example (from Simplified_VNA_Plugin.py:158-159):
        return self.selected_params  # e.g., ("S11", "S21", "S12", "S22")

    Example for custom sensor:
        return ("Temperature", "Humidity", "Pressure")
    """
    pass
```

#### 3. Measurement Methods

```python
def scan_begin(self) -> None:
    """
    Prepare instrument for scan sequence.

    Called once at the start of a scan before any measurements.

    This method should:
    - Put instrument in appropriate measurement mode
    - Trigger any initialization sweeps
    - Wait for instrument to be ready

    Example (from Simplified_VNA_Plugin.py:161-163):
        self.vna.write(":TRIG:SING")
        self.vna.query("*OPC?")  # Wait for operation complete
    """
    pass

def scan_trigger_and_wait(
    self,
    scan_index: int,
    scan_location: tuple[float, ...]
) -> list[list[float]] | list[float] | None:
    """
    Trigger a measurement and wait for completion.

    Called at each scan point before scan_read_measurement().

    Args:
        scan_index: Current point index in the scan
        scan_location: (X, Y, Z) position of current measurement

    Returns:
        Measurement data OR None if data will be read separately

    Note: Can return None if scan_read_measurement() handles data retrieval
    """
    pass

def scan_read_measurement(
    self,
    scan_index: int,
    scan_location: tuple[float, ...]
) -> list[list[float]] | list[float] | None:
    """
    Read measurement data from the instrument.

    **CRITICAL:** This is where you return the actual measurement data.

    Args:
        scan_index: Current point index in the scan
        scan_location: (X, Y, Z) position of current measurement

    Returns:
        Dictionary mapping channel names to complex numpy arrays
        OR list of lists of floats for multi-channel data
        OR list of floats for single-channel data

    **IMPORTANT RETURN FORMAT (from Simplified_VNA_Plugin.py:178-186):**

        results = {}
        for idx, name in enumerate(self.get_channel_names(), start=1):
            raw = self.vna.query(f":CALC1:PAR{idx}:DATA:SDAT?")
            tokens = self._strip_block(raw)
            vals = list(map(float, tokens))
            # Convert to complex values (real, imag pairs)
            results[name] = np.array([
                complex(vals[i], vals[i+1])
                for i in range(0, len(vals), 2)
            ])
        return results

    The system expects:
    - Dictionary keys: Channel names from get_channel_names()
    - Dictionary values: Complex numpy arrays of measurement data
    - Array length: Must match get_xaxis_coords() length

    For VNA S-parameters:
    - Parse real/imaginary pairs from instrument
    - Convert to complex numbers
    - Return as numpy array

    For real-valued sensors:
    - Return real measurements as complex with zero imaginary part
    - OR return simple list of floats
    """
    pass

def scan_end(self) -> None:
    """
    Clean up after scan sequence completes.

    Called once at the end of a scan after all measurements.

    This method should:
    - Return instrument to idle state
    - Stop any continuous measurements
    - Perform any necessary cleanup

    Example:
        self.instrument.write(":ABORT")  # Stop measurement
    """
    pass
```

### Complete Example: VNA Probe Plugin

```python
from scanner.probe_controller import ProbePlugin
from scanner.plugin_setting import PluginSettingString, PluginSettingInteger, PluginSettingFloat
import pyvisa
import numpy as np
import re


class MyVNAPlugin(ProbePlugin):
    """Example VNA plugin demonstrating best practices."""

    def __init__(self):
        super().__init__()

        # Pre-connection settings (configured before connecting)
        self.address = PluginSettingString(
            "VISA Address",
            "TCPIP0::192.168.1.100::inst0::INSTR"
        )
        self.timeout = PluginSettingInteger("Timeout (ms)", 20000)
        self.freq_start = PluginSettingFloat("Start Freq (Hz)", 1e9)
        self.freq_stop = PluginSettingFloat("Stop Freq (Hz)", 10e9)

        # Add settings to pre-connect configuration
        self.add_setting_pre_connect(self.address)
        self.add_setting_pre_connect(self.timeout)
        self.add_setting_pre_connect(self.freq_start)
        self.add_setting_pre_connect(self.freq_stop)

        # State variables
        self.vna = None
        self.frequency_points = None

    def connect(self) -> None:
        """Connect to VNA using VISA (RECOMMENDED METHOD)."""
        # Open VISA resource
        rm = pyvisa.ResourceManager()
        self.vna = rm.open_resource(self.address.value)
        self.vna.timeout = self.timeout.value

        # Configure VNA
        self.vna.write(f":SENS1:FREQ:STAR {self.freq_start.value}")
        self.vna.write(f":SENS1:FREQ:STOP {self.freq_stop.value}")

        # Query frequency points
        raw = self.vna.query(":SENS1:FREQ:DATA?")
        self.frequency_points = self._parse_block_data(raw)

        print(f"Connected to VNA at {self.address.value}")

    def disconnect(self) -> None:
        """Cleanly disconnect from VNA."""
        if self.vna:
            self.vna.close()
            self.vna = None

    def get_xaxis_coords(self) -> tuple[float, ...]:
        """Return frequency points."""
        return tuple(self.frequency_points)

    def get_xaxis_units(self) -> str:
        """Return frequency units."""
        return "Hz"

    def get_yaxis_units(self) -> str:
        """Return S-parameter units."""
        return "Complex"

    def get_channel_names(self) -> tuple[str, ...]:
        """Return S-parameter names."""
        return ("S11", "S21")

    def scan_begin(self) -> None:
        """Initialize VNA for scanning."""
        self.vna.write(":TRIG:SOUR BUS")
        self.vna.query("*OPC?")

    def scan_trigger_and_wait(self, scan_index: int, scan_location: tuple[float, ...]) -> None:
        """Trigger measurement and wait."""
        self.vna.write("*TRG")
        self.vna.query("*OPC?")
        return None

    def scan_read_measurement(self, scan_index: int, scan_location: tuple[float, ...]) -> dict:
        """
        Read S-parameter data from VNA.

        CRITICAL: Return format must be dict mapping channel names to complex arrays.
        """
        results = {}

        for idx, name in enumerate(self.get_channel_names(), start=1):
            # Query S-parameter data (real/imag format)
            raw = self.vna.query(f":CALC1:PAR{idx}:DATA:SDAT?")
            tokens = self._parse_block_data(raw)
            vals = list(map(float, tokens))

            # Convert interleaved real/imag to complex array
            results[name] = np.array([
                complex(vals[i], vals[i+1])
                for i in range(0, len(vals), 2)
            ])

        return results

    def scan_end(self) -> None:
        """Clean up after scan."""
        self.vna.write(":SENS1:HOLD:FUNC HOLD")

    def _parse_block_data(self, raw: str) -> list[str]:
        """Helper to parse IEEE 488.2 block data format."""
        if raw.startswith("#"):
            hdr_digits = int(raw[1])
            raw = raw[2 + hdr_digits:]
        return re.split(r"[,\s]+", raw.strip())
```

---

## Motion Controller Plugin Development

### Base Class Requirements

All motion controller plugins must inherit from `MotionControllerPlugin`.

### Required Imports

```python
from scanner.motion_controller import MotionControllerPlugin
from scanner.plugin_setting import (
    PluginSettingString,
    PluginSettingInteger,
    PluginSettingFloat
)
```

### Abstract Methods (Must Implement)

#### 1. Connection Management

```python
def connect(self) -> None:
    """
    Establish connection to motion controller.

    RECOMMENDED CONNECTION METHODS:
    - Serial (pyserial): For USB/RS-232 controllers
    - Socket: For Ethernet-based controllers
    - VISA: For GPIB-based controllers

    This method should:
    - Open communication port/socket
    - Initialize controller settings
    - Configure axis parameters
    - Home axes if required
    """
    pass

def disconnect(self) -> None:
    """
    Cleanly disconnect from motion controller.

    This method should:
    - Stop any active motion
    - Close communication channels
    - Release resources
    """
    pass
```

#### 2. Axis Configuration

```python
def get_axis_display_names(self) -> tuple[str, ...]:
    """
    Return display names for motion axes.

    Returns:
        tuple of axis names

    Example:
        return ("X", "Y", "Z")
        return ("Azimuth", "Elevation", "Range")
    """
    pass

def get_axis_units(self) -> tuple[str, ...]:
    """
    Return units for each axis.

    Returns:
        tuple of unit strings matching axis order

    Example:
        return ("mm", "mm", "mm")
        return ("deg", "deg", "m")
    """
    pass
```

#### 3. Motion Control

```python
def set_velocity(self, velocities: dict[int, float]) -> None:
    """
    Set velocity for specified axes.

    Args:
        velocities: Dictionary mapping axis index to velocity value
                   {0: 50.0, 1: 50.0}  # Set X and Y to 50 mm/s

    Example:
        for axis_idx, vel in velocities.items():
            self.controller.write(f"VEL{axis_idx}:{vel}")
    """
    pass

def set_acceleration(self, accels: dict[int, float]) -> None:
    """
    Set acceleration for specified axes.

    Args:
        accels: Dictionary mapping axis index to acceleration value

    Example:
        for axis_idx, accel in accels.items():
            self.controller.write(f"ACC{axis_idx}:{accel}")
    """
    pass

def move_relative(self, move_dist: dict[int, float]) -> dict[int, float] | None:
    """
    Move specified axes by relative distances.

    Args:
        move_dist: Dictionary mapping axis index to distance
                  {0: 10.0, 1: -5.0}  # Move X +10mm, Y -5mm

    Returns:
        Final positions after move (or None to use commanded positions)

    Example:
        for axis_idx, dist in move_dist.items():
            self.controller.write(f"MOVR{axis_idx}:{dist}")
    """
    pass

def move_absolute(self, move_pos: dict[int, float]) -> dict[int, float] | None:
    """
    Move specified axes to absolute positions.

    Args:
        move_pos: Dictionary mapping axis index to target position
                 {0: 100.0, 1: 50.0}  # Move X to 100mm, Y to 50mm

    Returns:
        Final positions after move (or None to use commanded positions)

    Example:
        for axis_idx, pos in move_pos.items():
            self.controller.write(f"MOVA{axis_idx}:{pos}")
    """
    pass

def home(self, axes: list[int]) -> dict[int, float]:
    """
    Home specified axes.

    Args:
        axes: List of axis indices to home [0, 1, 2]

    Returns:
        Dictionary of final homed positions

    Example:
        for axis_idx in axes:
            self.controller.write(f"HOME{axis_idx}")
        # Wait for completion
        return {0: 0.0, 1: 0.0, 2: 0.0}
    """
    pass
```

#### 4. Status Queries

```python
def get_current_positions(self) -> tuple[float, ...]:
    """
    Query current positions of all axes.

    Returns:
        tuple of current positions for all axes

    Example:
        response = self.controller.query("POS?")
        # Parse response: "X:10.00 Y:20.00 Z:30.00"
        positions = self._parse_positions(response)
        return tuple(positions)
    """
    pass

def is_moving(self, axis=None) -> list[bool]:
    """
    Check if axes are currently moving.

    **CRITICAL REQUIREMENT:**
    Must return a list of booleans for ALL axes (typically 3: X, Y, Z).
    Each boolean indicates if that axis is moving.

    Args:
        axis: Optional axis index (can be ignored, check all axes)

    Returns:
        List of booleans: [False, False, False] when not moving
                         [True, False, False] when X axis moving

    Example from motion_controller_plugin.py:323-352:

        is_moving_x = True
        is_moving_y = True
        is_moving_z = False  # If you have 3 axes

        query_command = bytes([0x08, 0x00])
        self.serial_port.write(query_command)
        response = self.serial_port.read(22)

        # Parse busy bits from controller response
        busy_bits = [response[2], response[12]]

        # Controller-specific logic to determine motion state
        if busy_bits[0] == 224:  # Example: 224 means idle
            is_moving_x = False
        else:
            is_moving_x = True

        if busy_bits[1] == 225:  # Example: 225 means idle
            is_moving_y = False
        else:
            is_moving_y = True

        # CRITICAL: Return list of booleans, one per axis
        return [is_moving_x, is_moving_y, is_moving_z]

    **IMPORTANT:**
    - Must return a list, NOT a single boolean
    - List length should match number of axes (typically 3)
    - All values False when no motion occurring
    - Controller must be polled to get real-time motion state
    """
    pass

def get_endstop_minimums(self) -> tuple[float, ...]:
    """
    Return minimum position limits for all axes.

    Returns:
        tuple of minimum positions

    Example:
        return (0.0, 0.0, 0.0)
    """
    pass

def get_endstop_maximums(self) -> tuple[float, ...]:
    """
    Return maximum position limits for all axes.

    Returns:
        tuple of maximum positions

    Example:
        return (300.0, 300.0, 300.0)
    """
    pass
```

#### 5. Configuration

```python
def set_config(self, amps, idle_p, idle_time):
    """
    Configure controller-specific parameters.

    This method is controller-specific. Implement as needed.

    Args:
        amps: Motor current in amperes
        idle_p: Idle current percentage
        idle_time: Idle timeout in seconds
    """
    pass
```

### Complete Example: Serial Motion Controller

```python
from scanner.motion_controller import MotionControllerPlugin
from scanner.plugin_setting import PluginSettingString, PluginSettingFloat, PluginSettingInteger
import serial
from serial.tools import list_ports


class MyMotionController(MotionControllerPlugin):
    """Example serial motion controller plugin."""

    def __init__(self):
        super().__init__()

        # Detect available COM ports
        ports = [port.device for port in list_ports.comports()]
        if not ports:
            ports = ["NO_PORTS_FOUND"]

        # Pre-connection settings
        self.port = PluginSettingString(
            "Serial Port",
            ports[0],
            select_options=ports,
            restrict_selections=True
        )
        self.velocity = PluginSettingFloat("Velocity (mm/s)", 50.0)
        self.acceleration = PluginSettingFloat("Acceleration (mm/s²)", 100.0)

        self.add_setting_pre_connect(self.port)
        self.add_setting_pre_connect(self.velocity)
        self.add_setting_pre_connect(self.acceleration)

        # State variables
        self.serial_port = None

    def connect(self) -> None:
        """Connect via serial port (RECOMMENDED for most motion controllers)."""
        self.serial_port = serial.Serial(
            port=self.port.value,
            baudrate=115200,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=1.0
        )

        # Initialize controller
        self.set_velocity({0: self.velocity.value, 1: self.velocity.value, 2: self.velocity.value})
        self.set_acceleration({0: self.acceleration.value, 1: self.acceleration.value, 2: self.acceleration.value})

        print(f"Connected to motion controller on {self.port.value}")

    def disconnect(self) -> None:
        """Disconnect from controller."""
        if self.serial_port:
            self.serial_port.close()
            self.serial_port = None

    def get_axis_display_names(self) -> tuple[str, ...]:
        """Return axis names."""
        return ("X", "Y", "Z")

    def get_axis_units(self) -> tuple[str, ...]:
        """Return axis units."""
        return ("mm", "mm", "mm")

    def set_velocity(self, velocities: dict[int, float]) -> None:
        """Set velocity for specified axes."""
        for axis_idx, vel in velocities.items():
            command = f"VEL{axis_idx}:{vel}\n"
            self.serial_port.write(command.encode())

    def set_acceleration(self, accels: dict[int, float]) -> None:
        """Set acceleration for specified axes."""
        for axis_idx, accel in accels.items():
            command = f"ACC{axis_idx}:{accel}\n"
            self.serial_port.write(command.encode())

    def move_relative(self, move_dist: dict[int, float]) -> None:
        """Move by relative distance."""
        for axis_idx, dist in move_dist.items():
            command = f"MOVR{axis_idx}:{dist}\n"
            self.serial_port.write(command.encode())
        return None

    def move_absolute(self, move_pos: dict[int, float]) -> None:
        """Move to absolute position."""
        for axis_idx, pos in move_pos.items():
            command = f"MOVA{axis_idx}:{pos}\n"
            self.serial_port.write(command.encode())
        return None

    def home(self, axes: list[int]) -> dict[int, float]:
        """Home specified axes."""
        for axis_idx in axes:
            command = f"HOME{axis_idx}\n"
            self.serial_port.write(command.encode())

        # Wait for homing to complete
        while any(self.is_moving()):
            time.sleep(0.1)

        return {0: 0.0, 1: 0.0, 2: 0.0}

    def get_current_positions(self) -> tuple[float, ...]:
        """Query current positions."""
        self.serial_port.write(b"POS?\n")
        response = self.serial_port.readline().decode()

        # Parse response: "X:10.00 Y:20.00 Z:30.00"
        parts = response.split()
        positions = []
        for part in parts:
            positions.append(float(part.split(":")[1]))

        return tuple(positions)

    def is_moving(self, axis=None) -> list[bool]:
        """
        Check if axes are moving.

        CRITICAL: Must return list of booleans for all axes!
        """
        self.serial_port.write(b"MOVING?\n")
        response = self.serial_port.readline().decode().strip()

        # Example response: "1,0,0" (X moving, Y and Z stopped)
        moving_states = [bool(int(x)) for x in response.split(",")]

        # Ensure we always return a list with 3 booleans
        while len(moving_states) < 3:
            moving_states.append(False)

        return moving_states

    def get_endstop_minimums(self) -> tuple[float, ...]:
        """Return minimum limits."""
        return (0.0, 0.0, 0.0)

    def get_endstop_maximums(self) -> tuple[float, ...]:
        """Return maximum limits."""
        return (300.0, 300.0, 300.0)

    def set_config(self, amps, idle_p, idle_time):
        """Configure motor parameters."""
        pass  # Implement controller-specific configuration
```

---

## Plugin Settings System

### Available Setting Types

```python
from scanner.plugin_setting import (
    PluginSettingString,
    PluginSettingInteger,
    PluginSettingFloat
)
```

### PluginSettingString

```python
# Simple string
address = PluginSettingString("IP Address", "192.168.1.100")

# Dropdown selection
mode = PluginSettingString(
    "Operation Mode",
    "Normal",
    select_options=["Normal", "Fast", "Precision"],
    restrict_selections=True  # User must select from options
)

# Add to plugin
self.add_setting_pre_connect(address)
self.add_setting_pre_connect(mode)

# Access value
ip = address.value
selected_mode = mode.value
```

### PluginSettingInteger

```python
# Integer with min/max constraints
num_points = PluginSettingInteger(
    "Number of Points",
    default=100,
    value_min=10,
    value_max=1000
)

self.add_setting_pre_connect(num_points)

# Access value
points = num_points.value
```

### PluginSettingFloat

```python
# Float with constraints
frequency = PluginSettingFloat(
    "Center Frequency (GHz)",
    default=5.0,
    value_min=0.1,
    value_max=20.0
)

self.add_setting_pre_connect(frequency)

# Access value
freq = frequency.value
```

### Pre-Connect vs Post-Connect Settings

```python
def __init__(self):
    super().__init__()

    # Pre-connect: Configured BEFORE connecting to instrument
    # Examples: Address, port, connection parameters
    self.address = PluginSettingString("Address", "...")
    self.add_setting_pre_connect(self.address)

    # Post-connect: Configured AFTER connecting to instrument
    # Examples: Measurement parameters, instrument modes
    self.averaging = PluginSettingInteger("Averaging", 10)
    self.add_setting_post_connect(self.averaging)
```

### Reading and Writing Settings

```python
# Reading settings
value_str = PluginSettingFloat.get_value_as_string(self.frequency)
value_float = float(value_str)

# Writing settings
PluginSettingFloat.set_value_from_string(self.frequency, "5.5")
PluginSettingInteger.set_value_from_string(self.num_points, "200")
```

---

## Connection Best Practices

### 1. VISA Connections (RECOMMENDED for Lab Instruments)

**Best for:** VNAs, spectrum analyzers, signal generators, oscilloscopes

**Advantages:**
- Industry standard protocol
- Reliable timeout handling
- Automatic buffer management
- Wide instrument support

```python
import pyvisa

def connect(self) -> None:
    rm = pyvisa.ResourceManager()
    self.instrument = rm.open_resource(self.address.value)
    self.instrument.timeout = self.timeout.value

    # Test connection
    idn = self.instrument.query("*IDN?")
    print(f"Connected to: {idn}")
```

**Common VISA Address Formats:**
- TCPIP: `TCPIP0::192.168.1.100::inst0::INSTR`
- GPIB: `GPIB0::10::INSTR`
- USB: `USB0::0x1234::0x5678::SERIAL::INSTR`
- Socket: `TCPIP0::192.168.1.100::5025::SOCKET`

### 2. Socket Connections (RECOMMENDED for Raw TCP/IP)

**Best for:** Custom instruments, embedded systems, network devices

```python
import socket

def connect(self) -> None:
    self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    self.sock.settimeout(5.0)

    host, port = self.address.value.split(":")
    self.sock.connect((host, int(port)))

    print(f"Connected via socket to {host}:{port}")

def query(self, command: str) -> str:
    self.sock.sendall(command.encode() + b'\n')
    response = self.sock.recv(4096).decode()
    return response.strip()
```

### 3. Serial Connections (RECOMMENDED for Motion Controllers)

**Best for:** Motor controllers, embedded boards, Arduino, servo drives

```python
import serial
from serial.tools import list_ports

def connect(self) -> None:
    self.serial_port = serial.Serial(
        port=self.port.value,
        baudrate=115200,
        bytesize=serial.EIGHTBITS,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        timeout=1.0
    )

    # Flush buffers
    self.serial_port.reset_input_buffer()
    self.serial_port.reset_output_buffer()
```

### Error Handling

Always implement robust error handling:

```python
def connect(self) -> None:
    try:
        # Connection code here
        self.instrument = rm.open_resource(self.address.value)
    except pyvisa.VisaIOError as e:
        raise ConnectionError(f"Failed to connect to {self.address.value}: {e}")
    except Exception as e:
        raise ConnectionError(f"Unexpected error during connection: {e}")

def disconnect(self) -> None:
    try:
        if self.instrument:
            self.instrument.close()
    except Exception as e:
        print(f"Warning: Error during disconnect: {e}")
    finally:
        self.instrument = None
```

---

## Testing Your Plugin

### 1. File Naming

Save your plugin with a descriptive name:
- `my_vna_plugin.py`
- `my_motion_controller.py`
- `custom_radar_plugin.py`

### 2. Standalone Testing

Add a test section to your plugin:

```python
if __name__ == "__main__":
    """Test the plugin standalone."""
    print("Testing Plugin...")

    # Create plugin instance
    plugin = MyVNAPlugin()

    # Test connection
    try:
        plugin.connect()
        print("✓ Connection successful")

        # Test data retrieval
        freqs = plugin.get_xaxis_coords()
        print(f"✓ Frequency points: {len(freqs)}")

        channels = plugin.get_channel_names()
        print(f"✓ Channels: {channels}")

        # Test measurement
        plugin.scan_begin()
        plugin.scan_trigger_and_wait(0, (0, 0, 0))
        data = plugin.scan_read_measurement(0, (0, 0, 0))
        print(f"✓ Measurement data: {list(data.keys())}")

        plugin.disconnect()
        print("✓ Disconnect successful")

    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
```

Run your plugin directly:
```bash
python my_plugin.py
```

### 3. Integration Testing

1. Start the Scan Controller GUI
2. Click "Configure" for Probe or Motion
3. Select your plugin file
4. Configure settings in pre-connect state
5. Click "Connect"
6. Verify connection succeeds
7. Configure post-connect settings
8. Test with a small scan pattern

### 4. Debugging Tips

```python
# Add debug prints
def scan_read_measurement(self, scan_index, scan_location):
    print(f"DEBUG: Reading measurement at index {scan_index}, location {scan_location}")

    # Your code here
    data = self.instrument.query("DATA?")
    print(f"DEBUG: Raw data length: {len(data)}")

    results = self._parse_data(data)
    print(f"DEBUG: Parsed {len(results)} channels")

    return results
```

---

## Common Pitfalls and Troubleshooting

### 1. Motion Controller is_moving() Returns Wrong Type

**Problem:** System crashes with "Cannot copy-convert (list) to C++"

**Cause:** `is_moving()` returns single boolean instead of list

**Solution:**
```python
# WRONG ❌
def is_moving(self, axis=None) -> bool:
    return False

# CORRECT ✓
def is_moving(self, axis=None) -> list[bool]:
    return [False, False, False]  # One boolean per axis
```

### 2. Probe Returns Wrong Data Format

**Problem:** Scan fails with "Invalid data format"

**Cause:** `scan_read_measurement()` returns wrong type

**Solution:**
```python
# For VNA-style measurements, return dict of complex arrays
def scan_read_measurement(self, scan_index, scan_location):
    results = {}
    for channel_name in self.get_channel_names():
        # Query data for this channel
        data = self._query_channel_data(channel_name)

        # Convert to complex numpy array
        results[channel_name] = np.array(data, dtype=complex)

    return results  # Must be dict with channel names as keys
```

### 3. Settings Not Persisting

**Problem:** Settings reset when plugin re-instantiated

**Cause:** Settings caching happens automatically, but values must be properly typed

**Solution:**
```python
# Ensure settings use correct types
self.frequency = PluginSettingFloat("Frequency", 5.0)  # Not string!
self.num_points = PluginSettingInteger("Points", 100)   # Not float!
```

### 4. Connection Timeout Issues

**Problem:** Connection hangs or times out

**Solutions:**
```python
# Set appropriate timeouts
self.instrument.timeout = 10000  # 10 seconds for VISA

# For serial, add read timeout
self.serial_port.timeout = 2.0

# For sockets
self.sock.settimeout(5.0)

# Query with timeout check
try:
    response = self.instrument.query("*IDN?")
except pyvisa.VisaIOError:
    raise TimeoutError("Instrument not responding")
```

### 5. Data Array Length Mismatch

**Problem:** "Array length does not match frequency points"

**Cause:** Measurement data length ≠ X-axis length

**Solution:**
```python
def scan_read_measurement(self, scan_index, scan_location):
    # Get expected length
    expected_length = len(self.get_xaxis_coords())

    # Read data
    data = self._read_from_instrument()

    # Verify length
    if len(data) != expected_length:
        raise ValueError(f"Data length {len(data)} does not match expected {expected_length}")

    return data
```

### 6. Motion Commands Not Executing

**Problem:** Movement commands sent but axes don't move

**Possible causes:**
- Controller not enabled
- Velocities/accelerations not set
- Axes not homed
- Wrong command format

**Solution:**
```python
def connect(self):
    # Initialize controller properly
    self.serial_port.write(b"ENABLE\n")  # Enable motors

    # Set motion parameters
    self.set_velocity({0: 50, 1: 50, 2: 50})
    self.set_acceleration({0: 100, 1: 100, 2: 100})

    # Home if required
    # self.home([0, 1, 2])
```

---

## Quick Reference Templates

### Minimal Probe Plugin Template

```python
from scanner.probe_controller import ProbePlugin
from scanner.plugin_setting import PluginSettingString
import numpy as np


class MinimalProbe(ProbePlugin):
    def __init__(self):
        super().__init__()
        self.address = PluginSettingString("Address", "TCPIP0::192.168.1.100::inst0::INSTR")
        self.add_setting_pre_connect(self.address)

    def connect(self):
        # TODO: Open connection
        pass

    def disconnect(self):
        # TODO: Close connection
        pass

    def get_xaxis_coords(self):
        # TODO: Return measurement points (e.g., frequencies)
        return tuple(range(100))

    def get_xaxis_units(self):
        return "Hz"

    def get_yaxis_units(self):
        return "V"

    def get_channel_names(self):
        return ("Channel1",)

    def scan_begin(self):
        pass

    def scan_trigger_and_wait(self, scan_index, scan_location):
        return None

    def scan_read_measurement(self, scan_index, scan_location):
        # TODO: Read and return measurement data
        results = {}
        for channel in self.get_channel_names():
            results[channel] = np.zeros(len(self.get_xaxis_coords()), dtype=complex)
        return results

    def scan_end(self):
        pass
```

### Minimal Motion Controller Template

```python
from scanner.motion_controller import MotionControllerPlugin
from scanner.plugin_setting import PluginSettingString


class MinimalMotion(MotionControllerPlugin):
    def __init__(self):
        super().__init__()
        self.port = PluginSettingString("Port", "COM3")
        self.add_setting_pre_connect(self.port)

    def connect(self):
        # TODO: Open connection
        pass

    def disconnect(self):
        # TODO: Close connection
        pass

    def get_axis_display_names(self):
        return ("X", "Y", "Z")

    def get_axis_units(self):
        return ("mm", "mm", "mm")

    def set_velocity(self, velocities):
        # TODO: Set velocity
        pass

    def set_acceleration(self, accels):
        # TODO: Set acceleration
        pass

    def move_relative(self, move_dist):
        # TODO: Move relative
        return None

    def move_absolute(self, move_pos):
        # TODO: Move absolute
        return None

    def home(self, axes):
        # TODO: Home axes
        return {0: 0.0, 1: 0.0, 2: 0.0}

    def get_current_positions(self):
        # TODO: Query positions
        return (0.0, 0.0, 0.0)

    def is_moving(self, axis=None):
        # CRITICAL: Return list of booleans!
        return [False, False, False]

    def get_endstop_minimums(self):
        return (0.0, 0.0, 0.0)

    def get_endstop_maximums(self):
        return (300.0, 300.0, 300.0)

    def set_config(self, amps, idle_p, idle_time):
        pass
```

---

## Summary Checklist

### Before Deploying Your Plugin

- [ ] Inherits from correct base class (`ProbePlugin` or `MotionControllerPlugin`)
- [ ] All abstract methods implemented
- [ ] Uses VISA, socket, or serial for connections (as appropriate)
- [ ] **Motion controllers:** `is_moving()` returns list of booleans
- [ ] **Probes:** `scan_read_measurement()` returns dict of complex arrays
- [ ] Settings use correct types (String, Integer, Float)
- [ ] Pre-connect vs post-connect settings properly categorized
- [ ] Error handling for connection failures
- [ ] Standalone test code (`if __name__ == "__main__"`)
- [ ] Tested with real hardware
- [ ] Tested in Scan Controller GUI
- [ ] Documentation comments for complex logic

---

## Getting Help

If you encounter issues:

1. Check this manual's troubleshooting section
2. Review example plugins in `scanner/Plugins/`
3. Run standalone test to isolate the problem
4. Add debug print statements
5. Check instrument documentation for command syntax
6. Consult with lab members who have written plugins

---

**Document Version:** 1.0
**Last Updated:** January 2026
**Maintained by:** Scan Controller Development Team
