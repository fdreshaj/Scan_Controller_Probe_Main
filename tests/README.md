# Test suite

Tests for the SAR Microwave Imager scanner control software.

```
pip install -r requirements-dev.txt
pytest
```

Runs in about four seconds, needs **no hardware**, and needs **Python 3.12+**
(`scanner/scan_file_1.py` uses PEP 701 f-strings, matching the README's
3.12.7). On an older interpreter the affected modules skip rather than error.

---

## The two rules this suite is built on

**1. No test may ever touch a device.**

This software drives a motion gantry and a VNA. The machine running `pytest`
may have both attached, so a stray `serial.Serial("COM3")` during a test run
could home a motor while someone's hand is in the scan volume.

`conftest.py` therefore poisons every hardware entry point — `serial.Serial`,
`pyvisa.ResourceManager`, `socket.socket.connect` — with an autouse fixture. A
test that reaches one fails with `HardwareAccessError` and an explanation
instead of opening the port. tkinter dialogs and `plt.show()` are stubbed too,
so nothing blocks waiting for a click.

That fixture is not just a safety net; it is an assertion in its own right. It
is how `test_construction_does_not_touch_hardware` discovered that
`bigtreetechMotor.__init__` opens a VISA session before the operator has
pressed Connect.

**2. `pytest` at the repo root must not collect the app.**

Three files outside `tests/` match pytest's default discovery pattern and are
not tests at all:

| File | What running it does |
|---|---|
| `test_scanner_gui.py` | the GUI entry point — launches the application |
| `test_scanner_command.py` | connects to hardware and starts a scan |
| `scanner/test_tinyg.py` | opens *every* serial port, probing for a TinyG board |

`pytest.ini` pins `testpaths = tests`, which is what stops that. Don't remove
it — `test_module_imports.py::TestCollectionSafety` will fail if you do.

---

## What's covered, and why these things

The app is a plugin-driven instrument controller, so the suite targets the
failure modes that shape carries rather than chasing line coverage.

| File | Covers | Why it earns its place |
|---|---|---|
| `test_plugin_conformance.py` | every plugin under `scanner/Plugins/` can actually be constructed | **The most valuable file here.** Plugins are loaded by `importlib` + `getattr()` on a file the operator picks from a dialog, so no import and no static analysis ever touches them. A plugin missing an abstract method looks fine until an operator selects it mid-session, with hardware powered up. |
| `test_gecko_instructions.py` | exact 32-bit encodings for the Gecko drive | These words go straight down the serial link. A wrong opcode or a misplaced sign bit doesn't raise — it moves a real gantry to the wrong place. Asserted as literal hex, field by field. |
| `test_motion_controller.py` | connection lifecycle, guard rails, travel limits | The last software layer before a motor turns. Nothing that moves an axis may run while disconnected. |
| `test_probe_controller.py` | VNA lifecycle and scan call ordering | Called once per measurement point, tens of thousands of times per run. Ordering and the disconnected guard are the contract. |
| `test_scan_pattern.py` | raster geometry and serpentine invariants | A pattern that jumps instead of serpentining doubles the runtime of a scan that already takes hours; a matrix with the wrong column count produces a dataset that won't reshape into an image. |
| `test_probe_simulator.py` | the shipped simulator, end to end through the controller | The closest thing to an integration test that runs with nothing attached. |
| `test_plugin_setting.py` | operator input validation | Every number typed into the GUI arrives here as a string and leaves as a velocity or a travel distance. |
| `test_scan_file.py` | file naming, metadata, HDF5 layout round trips | A scan runs for hours. A misnamed or overwritten output file means repeating it. |
| `test_sparam_processing.py` | the FFT / filter / phase maths behind the visualizer | Physics assertions against synthetic data with a known closed-form answer: a reflector injected at 3 ns must come back at 3 ns, a high-pass told to remove antenna coupling must remove it. Wrong DSP draws a confident picture of the wrong thing, which beats a crash for hiding. |
| `test_sparam_visualizer.py` | the visualizer window itself, driven headless | Loads a synthetic scan with a flat coupling term at 0.2 ns and a localised target at 3 ns, then asserts the 3 ns range bin lights up where the target is. Also covers the standalone empty state, the import flow, playback speed, and heatmap upscaling. Runs offscreen — no display, no window. |
| `test_module_imports.py` | every first-party module parses and imports | Cheap and broad. Catches the syntax error, circular import, or deleted-name-with-surviving-reference that a cleanup can introduce. |
| `test_static_hygiene.py` | flake8 F401/F811/F841 gate, duplicate definitions, unreachable code | The ratchet that stops the `Cleaning_day` dead-code removal from silently undoing itself. |

### Markers

```
pytest -m protocol      # exact wire encodings — a wrong bit moves a motor
pytest -m geometry      # scan-pattern maths
pytest -m conformance   # plugins satisfy the ABC the loader assumes
pytest -m contract      # controller lifecycle and guard rails
pytest -m hygiene       # static checks
```

---

## Reading the results

A clean run is currently **604 passed, 46 skipped, 9 xfailed** with every
optional dependency installed.

**Skips are expected.** A test skips when a vendor library isn't installed —
`ftd2xx`, `nidaqmx`, `skrf`, `PySide6`. A CI box has no FTDI driver, and that
shouldn't be a failure. Install the optional extras listed in
`requirements-dev.txt` to widen coverage on a development machine.

**`xfail` means a real bug, pinned.** Every xfail here is `strict=True`, so it
must keep failing. Fix the underlying defect and pytest reports **XPASS**, which
fails the run and tells you to promote the test to an ordinary assertion. The
`reason=` string on each one explains the defect and, where it's clear, the fix.

The nine are:

1. **`motion_simulator` can't be instantiated** — missing `emergency_stop()` and
   `show_radar()`. The one driver meant to work with no hardware attached.
2. **`motion_controller_plugin` can't be instantiated** — missing `show_radar()`.
   This is the Gecko driver the README tells operators to use.
3. **`huge_scanner_plugin_the_Fast_one`** — same, its near-identical twin.
4. **`cyBot_Plugin_new_new`** — missing `show_radar()`; its `cyBot_Plugin`
   implements none of the eight `ProbePlugin` acquisition methods.
5. **`GcodeSimulator`** — missing `set_config()`, `emergency_stop()`,
   `show_radar()`.
6. **`bigtreetechMotor.__init__` opens a VISA session** before Connect, and never
   closes it.
7. **`MotionController.connect()` violates its own ABC** — calls
   `set_velocity()` with no arguments while `MotionControllerPlugin` declares a
   required parameter. Works only because every shipped plugin defaults it to
   `None`.
8. **`move_relative()` is not relative** — it folds in `self._target_positions`,
   which is only ever `[]` because the line that would populate it is commented
   out. The offset passes through unchanged, so a relative move silently becomes
   an absolute one.
9. **`MoveInsn` truncates instead of raising** — an out-of-range distance prints
   a warning and is masked to 24 bits, so a move of `0x1000005` steps becomes a
   move of 5. Every sibling instruction raises `ValueError` here.

Five of those nine (1–5) are one root cause: **`show_radar` is declared
`@abstractmethod` on `MotionControllerPlugin`, but `MotionController.show_radar()`
guards its own call with `hasattr(self._driver, 'show_radar')`.** The caller
treats the method as optional while the interface demands it. Dropping
`@abstractmethod` from that one declaration fixes most of the list.

---

## Adding tests

- **Never** construct a real driver. Use `RecordingMotionPlugin` /
  `RecordingProbePlugin` from `tests/fakes.py`, or the `motion_plugin`,
  `probe_plugin` and `probe_simulator` fixtures.
- **Anything that builds a Qt widget must request the `qapp` fixture.** Qt
  *aborts the process* — it does not raise — when a widget is constructed with
  no `QApplication`, so one careless test takes the whole run down. Several
  plugins build their GUI in `__init__`; `scanner/Plugins/cyBot_Plugin.py` is
  the one that found this.
- The fakes implement their ABCs completely on purpose — they are the reference
  for what a conformant plugin looks like. `test_the_fake_implements_the_whole_abc`
  fails if one drifts.
- Prefer asserting on the *sequence* of driver calls (`plugin.call_names`) over
  a single end state. With hardware, order is the thing that matters.
- When you find a bug you aren't fixing right now, add an
  `xfail(strict=True)` with a `reason=` that explains the defect — not a
  `skip`. A skip is invisible; a strict xfail tells you the moment it's fixed.
