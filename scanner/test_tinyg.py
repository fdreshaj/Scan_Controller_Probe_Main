        
import serial
from serial.tools import list_ports
import time




candidates = list(list_ports.comports())
if not candidates:
    raise ConnectionError("No serial ports found on system")

print(f"\nAttempting to connect to TinyG across {len(candidates)} serial port(s)...")
print("Found the following serial ports:")
for p in candidates:
    print(f"  - {p.device}  ({p.description})")

confirmed_port: serial.Serial | None = None
fallback_port:  serial.Serial | None = None
fallback_name:  str | None = None

for port_info in candidates:
    port = port_info.device
    print(f"\n  Trying {port}...")
    try:
        ser = serial.Serial(
            port=port,
            baudrate=115200,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=0.1,
            write_timeout=2.0,
        )
    except (serial.SerialException, OSError) as e:
        print(f"  ✗ Could not open {port}: {e}")
        continue

    if fallback_port is None:
        fallback_port = ser
        fallback_name = port

    time.sleep(0.05)
    ser.reset_input_buffer()
    ser.write(b"M115\n")
    time.sleep(0.05)
    raw = ser.read(ser.in_waiting or 512)
    response = raw.decode("utf-8", errors="replace")
    print(f"  M115 response: {response[:80].strip()!r}")

    if "tinyg" in response.lower() or "firmware" in response.lower():
        print(f"  ✓ TinyG identity confirmed on {port}")
        confirmed_port = ser
        if fallback_port is not ser:
            fallback_port.close()
        break
    else:
        print(f"  ✗ No TinyG identity (keeping as fallback)")

if confirmed_port is not None:
    serial_port = confirmed_port
    resource_name = confirmed_port.port
elif fallback_port is not None:
    print(f"\n  No TinyG identity on any port — using fallback: {fallback_name}")
    serial_port = fallback_port
    resource_name = fallback_name
else:
    raise ConnectionError(
        "Could not open any serial port. "
        "Check USB connection and driver installation."
    )

print(f"\n✓ Connected to TinyG on {resource_name}")