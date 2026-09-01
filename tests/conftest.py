"""Shared fixtures and safety rails for the SAR scanner test suite.

The single most important thing this file does is make it *impossible* for a
test run to touch real hardware. This project drives a motion gantry and a VNA;
a stray `serial.Serial("COM3")` during `pytest` could home a motor with an
operator's hand in the scan volume. Every hardware entry point is therefore
poisoned by an autouse fixture -- if a test reaches one, it fails loudly with an
explanation instead of opening the port.

The suite also runs headless: tkinter dialogs and matplotlib windows are stubbed
so nothing blocks waiting for a click.
"""

from __future__ import annotations

import os
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

# Qt must never try to reach a display. Set before anything imports PySide6.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


# --------------------------------------------------------------------------
# Qt
# --------------------------------------------------------------------------

@pytest.fixture(scope="session")
def qapp():
    """The one QApplication for the session, or None if PySide6 is absent.

    Anything that constructs a QWidget needs this. Qt *aborts the process* --
    not raises -- when a widget is built with no QApplication, so a test that
    touches Qt without requesting this fixture takes the whole run down with
    it. Several plugins build their GUI in `__init__`, so this is not a
    theoretical concern: `scanner/Plugins/cyBot_Plugin.py` does exactly that.

    Session-scoped because Qt permits only one QApplication per process.
    """
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:
        return None
    return QApplication.instance() or QApplication([])


# --------------------------------------------------------------------------
# Hardware lockout
# --------------------------------------------------------------------------

class HardwareAccessError(RuntimeError):
    """Raised when a test tries to open a real device."""


def _forbid(what: str):
    """Build a stand-in that explodes on construction but is otherwise a class.

    It has to be a *class*, not a function. Modules in this project write
    runtime-evaluated annotations like

        confirmed_port: serial.Serial | None = None

    at module scope, and `function | None` raises TypeError while
    `SomeClass | None` is a perfectly good union. A function stub would break
    the import it is supposed to be protecting.
    """

    class _Blocked:
        def __init__(self, *args, **kwargs):
            raise HardwareAccessError(
                f"A test tried to open {what} with args={args!r} kwargs={kwargs!r}.\n"
                "Tests must never touch real hardware -- this machine may have a "
                "gantry attached. Use the fakes in tests/fakes.py instead."
            )

    _Blocked.__name__ = f"Blocked{what.title().replace(' ', '')}"
    return _Blocked


@pytest.fixture(autouse=True)
def no_hardware(monkeypatch):
    """Poison every hardware entry point for the duration of each test.

    Applied to the libraries that are actually installed; missing ones are
    skipped, because a library that is not importable cannot open a device.
    """
    try:
        import serial
        monkeypatch.setattr(serial, "Serial", _forbid("a serial port"), raising=False)
    except ImportError:
        pass

    try:
        import pyvisa
        monkeypatch.setattr(
            pyvisa, "ResourceManager", _forbid("a VISA resource"), raising=False
        )
    except ImportError:
        pass

    try:
        import socket
        monkeypatch.setattr(
            socket.socket, "connect", _forbid("a network socket"), raising=False
        )
    except ImportError:
        pass


# --------------------------------------------------------------------------
# Headless GUI
# --------------------------------------------------------------------------

@pytest.fixture(autouse=True, scope="session")
def _headless_matplotlib():
    """Force the non-interactive backend before any module imports pyplot."""
    try:
        import matplotlib
        matplotlib.use("Agg", force=True)
    except ImportError:
        pass


@pytest.fixture(autouse=True)
def no_blocking_dialogs(monkeypatch):
    """Stub the tkinter and pyplot calls that would block on a human.

    `ScanPattern.connect()` pops a "Time EST" messagebox, and several plot
    helpers call `plt.show()`. Under test both become no-ops so the suite can
    run unattended and in CI.
    """
    try:
        import tkinter
        from tkinter import messagebox

        monkeypatch.setattr(messagebox, "showinfo", lambda *a, **k: "ok", raising=False)
        monkeypatch.setattr(messagebox, "showerror", lambda *a, **k: "ok", raising=False)
        monkeypatch.setattr(messagebox, "showwarning", lambda *a, **k: "ok", raising=False)
        monkeypatch.setattr(messagebox, "askyesno", lambda *a, **k: False, raising=False)

        class _StubTk:
            """Stands in for a Tk root: accepts anything, does nothing."""

            def __init__(self, *a, **k):
                pass

            def __getattr__(self, _name):
                return lambda *a, **k: None

        monkeypatch.setattr(tkinter, "Tk", _StubTk, raising=False)
    except ImportError:
        pass

    try:
        import matplotlib.pyplot as plt
        monkeypatch.setattr(plt, "show", lambda *a, **k: None, raising=False)
    except ImportError:
        pass


# --------------------------------------------------------------------------
# Convenience fixtures
# --------------------------------------------------------------------------

@pytest.fixture
def motion_plugin():
    """A fully conformant, call-recording stand-in for a motion driver."""
    from tests.fakes import RecordingMotionPlugin
    return RecordingMotionPlugin()


@pytest.fixture
def probe_plugin():
    """A fully conformant, call-recording stand-in for a VNA / probe driver."""
    from tests.fakes import RecordingProbePlugin
    return RecordingProbePlugin()


@pytest.fixture
def probe_simulator():
    """The shipped ProbeSimulator, with its sleeps turned off."""
    from scanner.probe_simulator import ProbeSimulator

    sim = ProbeSimulator()
    sim.measure_time.value = 0.0
    sim.init_time.value = 0.0
    return sim
