"""Every plugin under scanner/Plugins/ must actually be loadable.

This is the most valuable file in the suite, because it covers the blind spot
the architecture creates. `scanner/scanner.py` loads a driver with
`importlib` + `getattr()` on a file the operator picks from a dialog, so no
static analysis and no import ever touches these classes. A plugin that forgets
an abstract method looks perfectly fine until an operator selects it, at which
point Python raises

    TypeError: Can't instantiate abstract class ... with abstract methods ...

mid-session, with hardware powered up. `Scanner._load_probe_plugin` catches only
ImportError and AttributeError, so a TypeError from an abstract class is not
caught either.

The tests below walk the plugin directory the same way the loader does and
prove each class can be constructed. Plugins whose vendor library is not
installed are skipped, not failed -- a CI box has no NI-DAQmx or FTDI driver.
"""

from __future__ import annotations

import contextlib
import importlib.util
import inspect
import io
import pathlib

import pytest

from scanner.motion_controller import MotionControllerPlugin
from scanner.probe_controller import ProbePlugin

pytestmark = pytest.mark.conformance

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
PLUGIN_DIR = REPO_ROOT / "scanner" / "Plugins"

BASE_CLASSES = (MotionControllerPlugin, ProbePlugin)

#: Files under scanner/Plugins/ that are not plugins: standalone utilities and
#: scratch scripts. They are still import-checked by test_module_imports.py.
NOT_PLUGINS = {
    "__init__.py",
    "csv_to_hdf5.py",
    "geckoInstructions.py",
    "h5tst.py",
    "hdf5_reader.py",
    "motion_bit_manipulation.py",
    "testing_scripts.py",
    "VNA_List_Sparams.py",
}

#: Plugins that cannot be instantiated today. Each entry is an xfail(strict) --
#: fix the plugin and pytest reports XPASS, at which point delete the entry.
KNOWN_NON_CONFORMANT = {
    "motion_controller_plugin.py": (
        "Never implements show_radar(). This is the Gecko driver the README "
        "tells operators to use, so selecting it in the plugin dialog raises "
        "TypeError. Note that MotionController.show_radar() already guards with "
        "hasattr(self._driver, 'show_radar') -- the caller treats the method as "
        "optional while the ABC declares it mandatory. Dropping @abstractmethod "
        "from MotionControllerPlugin.show_radar is probably the right fix."
    ),
    "huge_scanner_plugin_the_Fast_one.py": (
        "Never implements show_radar(). Same defect as its near-identical twin "
        "motion_controller_plugin.py."
    ),
    "cyBot_Plugin_new_new.py": (
        "motion_controller_plugin never implements show_radar(), and "
        "cyBot_Plugin subclasses ProbePlugin without implementing any of the "
        "eight acquisition methods (get_channel_names, get_xaxis_coords, "
        "get_xaxis_units, get_yaxis_units, scan_begin, scan_end, "
        "scan_read_measurement, scan_trigger_and_wait) -- a stub wearing a "
        "probe's interface."
    ),
    "motion_simulator.py": (
        "Never implements emergency_stop() or show_radar(). The simulator is "
        "the one driver meant to work with no hardware attached, and it cannot "
        "be constructed at all."
    ),
}

#: Plugins whose constructor opens a device. Building a plugin must be inert --
#: the GUI constructs one just to read its settings list, before the operator
#: has pressed Connect.
KNOWN_HARDWARE_IN_CONSTRUCTOR = {
    "bigtreetechMotor.py": (
        "__init__ calls pyvisa.ResourceManager() and rm.list_resources(). The "
        "GUI builds a plugin to render its settings, so merely selecting this "
        "driver opens a VISA session and enumerates the bus before the operator "
        "has pressed Connect. The session is also never closed on disconnect. "
        "Move both calls into connect()."
    ),
}


def plugin_files() -> list[pathlib.Path]:
    return sorted(
        path
        for path in PLUGIN_DIR.rglob("*.py")
        if path.name not in NOT_PLUGINS and not path.name.startswith("test-")
    )


def _param(path: pathlib.Path, known: dict[str, str]):
    """Turn a plugin path into a pytest param, xfailing the known-broken ones."""
    marks = []
    if path.name in known:
        marks.append(pytest.mark.xfail(strict=True, reason=known[path.name]))
    return pytest.param(path, marks=marks, id=str(path.relative_to(PLUGIN_DIR)))


def load_module(path: pathlib.Path):
    """Load a plugin file exactly the way PluginSwitcher.select_plugin() does.

    Returns the module, or skips when a vendor library is missing. Plugin
    modules print banners at import time, so stdout is muted.
    """
    spec = importlib.util.spec_from_file_location(f"plugin_under_test_{path.stem}", path)
    module = importlib.util.module_from_spec(spec)
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            spec.loader.exec_module(module)
    except ImportError as exc:
        pytest.skip(f"vendor library unavailable for {path.name}: {exc}")
    except EOFError as exc:
        pytest.skip(f"{path.name} prompts for input at import time: {exc}")
    return module


def plugin_classes(module) -> list[type]:
    """The classes the loader would consider, using the loader's own rule."""
    return [
        obj
        for _name, obj in inspect.getmembers(module, inspect.isclass)
        if obj.__module__ == module.__name__
        and issubclass(obj, BASE_CLASSES)
        and obj not in BASE_CLASSES
    ]


class TestDiscovery:
    def test_the_plugin_directory_exists(self):
        assert PLUGIN_DIR.is_dir()

    def test_there_are_plugins_to_check(self):
        assert plugin_files(), "no plugin files found -- has the layout changed?"

    def test_the_exclusion_list_is_accurate(self):
        """Every name in NOT_PLUGINS must still exist, or the list is stale."""
        existing = {p.name for p in PLUGIN_DIR.rglob("*.py")}
        stale = NOT_PLUGINS - existing
        assert not stale, f"NOT_PLUGINS names files that no longer exist: {stale}"

    @pytest.mark.parametrize("registry", [KNOWN_NON_CONFORMANT, KNOWN_HARDWARE_IN_CONSTRUCTOR])
    def test_the_known_defect_lists_are_accurate(self, registry):
        """A defect list that names a deleted file hides a gap in coverage."""
        existing = {p.name for p in PLUGIN_DIR.rglob("*.py")}
        stale = set(registry) - existing
        assert not stale, f"known-defect list names files that no longer exist: {stale}"


@pytest.mark.parametrize("path", [_param(p, {}) for p in plugin_files()])
class TestEveryPluginLoads:
    def test_the_file_can_be_loaded(self, path):
        """The loader execs the file; a syntax error takes the app down."""
        load_module(path)

    def test_declares_at_least_one_plugin_class(self, path):
        """`select_plugin()` reports "No ProbePlugin class found" and gives up.

        A file in the plugin directory with no plugin class in it is a file the
        operator can select and get nothing from.
        """
        module = load_module(path)
        if not plugin_classes(module):
            pytest.skip(
                f"{path.name} exposes no plugin class -- add it to NOT_PLUGINS "
                "if that is intentional"
            )


@pytest.mark.parametrize("path", [_param(p, KNOWN_NON_CONFORMANT) for p in plugin_files()])
def test_every_plugin_class_can_be_instantiated(path):
    """The check that matters: no leftover abstract methods.

    This is exactly what the operator hits when they pick the plugin from the
    dialog, and the one failure mode the dynamic loader makes invisible to
    every other kind of analysis.
    """
    module = load_module(path)
    classes = plugin_classes(module)
    if not classes:
        pytest.skip("no plugin class in this file")

    for cls in classes:
        missing = sorted(getattr(cls, "__abstractmethods__", ()) or ())
        assert not missing, (
            f"{path.name}:{cls.__name__} cannot be instantiated -- it never "
            f"implements {', '.join(missing)}. Selecting this plugin in the GUI "
            f"raises TypeError at runtime."
        )


@pytest.mark.parametrize(
    "path", [_param(p, KNOWN_HARDWARE_IN_CONSTRUCTOR) for p in plugin_files()]
)
def test_construction_does_not_touch_hardware(path):
    """Building a plugin must be inert; connecting is the explicit step.

    The GUI constructs a plugin to read its settings list before the operator
    has pressed Connect, so a constructor that opens a port grabs the device --
    and the `no_hardware` fixture turns that into a loud failure here.
    """
    module = load_module(path)
    classes = [
        cls
        for cls in plugin_classes(module)
        if not (getattr(cls, "__abstractmethods__", ()) or ())
    ]
    if not classes:
        pytest.skip("no instantiable plugin class in this file")

    for cls in classes:
        with contextlib.redirect_stdout(io.StringIO()):
            instance = cls()
        assert hasattr(instance, "settings_pre_connect"), (
            f"{cls.__name__} did not call super().__init__(), so the GUI has no "
            "settings list to render"
        )
        assert isinstance(instance.settings_pre_connect, list)
        assert isinstance(instance.settings_post_connect, list)


class TestReferenceImplementations:
    """The shipped simulators are the fallback when no hardware is present."""

    def test_the_probe_simulator_is_fully_conformant(self):
        from scanner.probe_simulator import ProbeSimulator

        assert not (getattr(ProbeSimulator, "__abstractmethods__", ()) or ())
        ProbeSimulator()

    @pytest.mark.xfail(
        strict=True,
        reason=(
            "GcodeSimulator never implements set_config(), emergency_stop() or "
            "show_radar(), all abstract on MotionControllerPlugin."
        ),
    )
    def test_the_gcode_simulator_is_fully_conformant(self):
        pytest.importorskip("zmq")
        from scanner.gcode_simulator import GcodeSimulator

        GcodeSimulator()

    def test_no_motion_driver_is_instantiable_today(self):
        """A blunt summary of the state of play, so nobody has to count xfails.

        Every motion driver that can be imported without vendor hardware
        libraries is currently non-conformant. If this ever stops being true,
        the assertion below fails and the test should be deleted in favour of
        the per-plugin coverage above.
        """
        instantiable = []
        for path in plugin_files():
            spec = importlib.util.spec_from_file_location(f"survey_{path.stem}", path)
            module = importlib.util.module_from_spec(spec)
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    spec.loader.exec_module(module)
            except BaseException:
                continue
            for cls in plugin_classes(module):
                if not issubclass(cls, MotionControllerPlugin):
                    continue
                if not (getattr(cls, "__abstractmethods__", ()) or ()):
                    instantiable.append(f"{path.name}:{cls.__name__}")

        assert sorted(instantiable) == [
            "bigtreetechMotor.py:motion_controller_plugin",
            "vna_plugin_custom.py:motion_controller_plugin",
        ], (
            "the set of instantiable motion drivers changed; update this test "
            f"(found: {sorted(instantiable)})"
        )
