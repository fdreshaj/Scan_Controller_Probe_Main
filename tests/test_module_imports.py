"""Every first-party module must import cleanly.

Cheap, broad, and worth more than it looks in a codebase this dynamic. An
import failure means a syntax error, a circular import, or a name that was
deleted while a reference survived -- exactly the class of mistake a dead-code
cleanup can introduce. The suite would rather find it here than when an
operator opens the plugin dialog mid-experiment.

Modules whose vendor library is absent are skipped, not failed.
"""

from __future__ import annotations

import ast
import contextlib
import importlib.util
import io
import pathlib
import sys

import pytest

pytestmark = pytest.mark.hygiene

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

#: Files that use syntax newer than the oldest interpreter someone might run the
#: suite on. The README pins Python 3.12.7, so this is a courtesy: on 3.11 these
#: skip with an explanation rather than reporting a baffling SyntaxError.
PY312_ONLY_FILES = {
    "scanner/scan_file_1.py": "PEP 701 nested f-strings",
}


def skip_if_too_new_for_this_interpreter(path: pathlib.Path) -> None:
    relative = str(path.relative_to(REPO_ROOT)).replace("\\", "/")
    if relative in PY312_ONLY_FILES and sys.version_info < (3, 12):
        pytest.skip(
            f"{relative} uses {PY312_ONLY_FILES[relative]} and needs Python "
            f"3.12+; this interpreter is {sys.version_info.major}."
            f"{sys.version_info.minor}. The project targets 3.12.7."
        )


#: Directories that are not first-party source.
EXCLUDED_DIRS = {".git", "Scanner App V1", "tests", "build", "dist", "__pycache__"}

#: Modules that run something on import instead of just defining things, so
#: importing them under test would block or do work. Each is a latent bug -- the
#: fix is an `if __name__ == "__main__":` guard -- and each is asserted below.
SIDE_EFFECT_MODULES = {
    "scanner/Plugins/motion_bit_manipulation.py": "calls input() at module scope",
    "scanner/Plugins/h5tst.py": "opens a file-picker dialog at module scope",
    "convert_to_hdf5.py": "writes scantester.hdf5 into the working directory",
    "test_scanner_command.py": "connects to hardware and starts a scan",
    "scanner/test_tinyg.py": (
        "opens every serial port on the machine at module scope, probing each "
        "one for a TinyG board"
    ),
}


def source_files() -> list[pathlib.Path]:
    files = []
    for path in REPO_ROOT.rglob("*.py"):
        if any(part in EXCLUDED_DIRS for part in path.relative_to(REPO_ROOT).parts):
            continue
        files.append(path)
    return sorted(files)


def importable_files() -> list[pathlib.Path]:
    return [
        p
        for p in source_files()
        if str(p.relative_to(REPO_ROOT)).replace("\\", "/") not in SIDE_EFFECT_MODULES
    ]


def ids(paths):
    return [str(p.relative_to(REPO_ROOT)).replace("\\", "/") for p in paths]


class TestSyntax:
    @pytest.mark.parametrize("path", source_files(), ids=ids(source_files()))
    def test_the_file_parses(self, path):
        """Parsing needs no imports, so this covers every file unconditionally.

        Note it also parses the side-effect modules, which the import test has
        to skip.
        """
        skip_if_too_new_for_this_interpreter(path)
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as exc:
            pytest.fail(f"{path.relative_to(REPO_ROOT)} does not parse: {exc}")


class TestImports:
    @pytest.mark.parametrize("path", importable_files(), ids=ids(importable_files()))
    def test_the_module_imports(self, path):
        skip_if_too_new_for_this_interpreter(path)
        spec = importlib.util.spec_from_file_location(
            f"import_check_{path.stem}_{abs(hash(str(path)))}", path
        )
        module = importlib.util.module_from_spec(spec)
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                spec.loader.exec_module(module)
        except ImportError as exc:
            pytest.skip(f"third-party dependency unavailable: {exc}")
        except NameError as exc:
            pytest.fail(
                f"{path.relative_to(REPO_ROOT)} references a name that does not "
                f"exist -- this is what a bad cleanup looks like: {exc}"
            )


class TestSideEffectModules:
    """The modules that do work at import time, pinned so the list stays honest."""

    @pytest.mark.parametrize("relative_path", sorted(SIDE_EFFECT_MODULES))
    def test_the_module_still_exists(self, relative_path):
        assert (REPO_ROOT / relative_path).is_file(), (
            "SIDE_EFFECT_MODULES names a file that no longer exists; if it was "
            "deleted, drop the entry so the import test picks up its replacement"
        )

    @pytest.mark.parametrize("relative_path", sorted(SIDE_EFFECT_MODULES))
    def test_the_module_still_lacks_a_main_guard(self, relative_path):
        """When someone adds the guard, this fails -- remove the entry then.

        A module that only defines things on import is safe to import, and
        should rejoin the import test above.
        """
        tree = ast.parse((REPO_ROOT / relative_path).read_text(encoding="utf-8"))
        has_guard = any(
            isinstance(node, ast.If)
            and isinstance(node.test, ast.Compare)
            and isinstance(node.test.left, ast.Name)
            and node.test.left.id == "__name__"
            for node in tree.body
        )
        assert not has_guard, (
            f"{relative_path} now has an `if __name__ == '__main__':` guard. "
            "Remove it from SIDE_EFFECT_MODULES so it gets import-tested."
        )


class TestCollectionSafety:
    """pytest must never import the repo's own `test_*.py` scripts.

    Three files outside `tests/` match pytest's default discovery pattern:
    `test_scanner_gui.py` (the GUI entry point), `test_scanner_command.py`
    (a hardware smoke script) and `scanner/test_tinyg.py` (which opens every
    serial port on the machine looking for a TinyG board). They are named for
    "testing the scanner", not for pytest. Collecting them would launch the app
    or start probing hardware.

    `pytest.ini` pins `testpaths = tests`, which is what keeps that from
    happening. These tests make sure the guard stays in place.
    """

    DECOY_SCRIPTS = [
        "test_scanner_gui.py",
        "test_scanner_command.py",
        "scanner/test_tinyg.py",
    ]

    def test_pytest_ini_restricts_collection_to_the_tests_directory(self):
        config = (REPO_ROOT / "pytest.ini").read_text(encoding="utf-8")
        assert "testpaths = tests" in config, (
            "pytest.ini no longer pins testpaths. Without it, `pytest` at the "
            "repo root collects the decoy scripts and touches real hardware."
        )

    @pytest.mark.parametrize("relative_path", DECOY_SCRIPTS)
    def test_the_decoy_scripts_live_outside_the_tests_directory(self, relative_path):
        path = REPO_ROOT / relative_path
        if not path.is_file():
            pytest.skip(f"{relative_path} no longer exists")
        assert "tests" not in path.relative_to(REPO_ROOT).parts


class TestCoreModulesHaveNoOptionalDependencies:
    """The scanner core must import with nothing but the standard library.

    If a hardware or GUI library creeps into these, the whole test suite (and
    any headless analysis script) stops working on a machine without a VNA.
    """

    @pytest.mark.parametrize(
        "module_name",
        [
            "scanner.plugin_setting",
            "scanner.probe_controller",
            "scanner.motion_controller",
            "scanner.scan_file_controller",
            "scanner.scan_pattern_controller",
            "scanner.probe_simulator",
        ],
    )
    def test_imports_without_optional_dependencies(self, module_name):
        importlib.import_module(module_name)
