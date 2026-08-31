"""Scan file configuration and the HDF5 layout the scan writes.

A scan runs for hours. If the output file is misnamed, overwritten, or laid out
differently from what the reader expects, the data is gone and the run has to be
repeated -- so the metadata contract deserves tests even though the writer
itself is entangled with the GUI.

`scanner/scan_file_1.py` uses PEP 701 nested f-strings, so it needs Python 3.12
(matching the README). It skips rather than errors on older interpreters.
"""

import sys

import pytest

pytest.importorskip("tkinter")

if sys.version_info < (3, 12):  # pragma: no cover - environment guard
    pytest.skip(
        "scanner/scan_file_1.py uses PEP 701 f-strings and needs Python 3.12+",
        allow_module_level=True,
    )

from scanner.scan_file_1 import ScanFile  # noqa: E402

pytestmark = pytest.mark.contract


@pytest.fixture
def scan_file():
    return ScanFile()


class TestDefaults:
    def test_defaults_to_hdf5(self, scan_file):
        assert scan_file.file_type.value == "HDF5"

    def test_file_type_is_restricted_to_known_formats(self, scan_file):
        with pytest.raises(ValueError):
            scan_file.file_type.set_value_from_string("parquet")

    def test_both_supported_formats_are_selectable(self, scan_file):
        for fmt in ("Bin", "HDF5"):
            scan_file.file_type.set_value_from_string(fmt)
            assert scan_file.file_type.value == fmt

    def test_the_default_name_is_timestamped(self, scan_file):
        name = scan_file.file_name.value
        assert name.startswith("ScanFile_")
        assert len(name) > len("ScanFile_")

    def test_two_instances_get_different_default_names(self):
        """Two scans started in the same session must not collide.

        The default name carries microseconds precisely so back-to-back runs do
        not overwrite each other.
        """
        assert ScanFile().file_name.value != ScanFile().file_name.value

    def test_the_default_name_has_no_path_separators(self, scan_file):
        """The name is joined onto a directory, so a separator would escape it."""
        name = scan_file.file_name.value
        assert "/" not in name and "\\" not in name

    def test_the_default_name_avoids_characters_windows_rejects(self, scan_file):
        """The operator station runs Windows; these characters are illegal there."""
        name = scan_file.file_name.value
        assert not set(name) & set(':*?"<>|')


class TestMetadataFields:
    def test_every_metadata_field_is_offered_before_connect(self, scan_file):
        """These are written into the file header, so the GUI must collect them
        before the scan starts, not after."""
        labels = [s.display_label for s in scan_file.settings_pre_connect]
        assert labels == [
            "File Type: ",
            "File Name: ",
            " Scan Frequency Band: ",
            " Scan Dimensions: ",
            " Scan Material Description: ",
        ]

    def test_metadata_is_editable(self, scan_file):
        scan_file.file_material_descrip.set_value_from_string("PLA, 40% infill")
        assert scan_file.file_material_descrip.value == "PLA, 40% infill"

    def test_progress_is_not_a_configurable_setting(self, scan_file):
        """`progress` is a live readout, not operator input, so it must not
        appear in either settings list."""
        all_labels = [
            s.display_label
            for s in scan_file.settings_pre_connect + scan_file.settings_post_connect
        ]
        assert "Progress: " not in all_labels

    def test_metadata_accepts_unicode(self, scan_file):
        """Sample descriptions routinely carry units like 'Ø' and 'µm'."""
        scan_file.file_material_descrip.set_value_from_string("Ø25 µm copper")
        assert scan_file.file_material_descrip.value == "Ø25 µm copper"


class TestConnectionLifecycle:
    def test_starts_disconnected(self, scan_file):
        assert scan_file.is_connected() is False

    def test_connect_then_disconnect(self, scan_file):
        scan_file.connect()
        assert scan_file.is_connected() is True
        scan_file.disconnect()
        assert scan_file.is_connected() is False


class TestHdf5Layout:
    """The layout the scan writer produces and the readers expect.

    `Scanner.vna_write_data_bulk` writes one group per point under /Point_Data,
    with a dataset per S-parameter. These tests build the same structure in a
    temp file and prove the shape survives a round trip -- if the layout is ever
    changed, the reader side needs changing with it.
    """

    @pytest.fixture
    def h5py(self):
        return pytest.importorskip("h5py")

    @pytest.fixture
    def np(self):
        return pytest.importorskip("numpy")

    def test_a_point_group_round_trips(self, h5py, np, tmp_path):
        path = tmp_path / "scan.h5"
        sweep = np.linspace(1e9, 11e9, 11)
        trace = np.arange(11, dtype=complex)

        with h5py.File(path, "w") as f:
            f.create_dataset("/Point_Data/[0 0]/S11/data", data=trace)
            f.create_dataset("/Frequencies", data=sweep)

        with h5py.File(path, "r") as f:
            assert np.allclose(f["/Point_Data/[0 0]/S11/data"][:], trace)
            assert np.allclose(f["/Frequencies"][:], sweep)

    def test_complex_s_parameters_survive_the_round_trip(self, h5py, np, tmp_path):
        """S-parameters are complex; a real-only write silently drops phase,
        which destroys any SAR reconstruction built from the file."""
        path = tmp_path / "scan.h5"
        trace = np.array([1 + 2j, 3 - 4j, -5 + 0.5j])

        with h5py.File(path, "w") as f:
            f.create_dataset("/Point_Data/[0 0]/S21/data", data=trace)

        with h5py.File(path, "r") as f:
            read_back = f["/Point_Data/[0 0]/S21/data"][:]

        assert np.iscomplexobj(read_back)
        assert np.allclose(read_back, trace)
        assert np.allclose(np.angle(read_back), np.angle(trace))

    def test_metadata_survives_as_attributes(self, h5py, tmp_path):
        path = tmp_path / "scan.h5"
        with h5py.File(path, "w") as f:
            group = f.create_group("/Point_Data")
            group.attrs["Material"] = "PLA, 40% infill"
            group.attrs["Frequency Band"] = "1-11 GHz"

        with h5py.File(path, "r") as f:
            assert f["/Point_Data"].attrs["Material"] == "PLA, 40% infill"
            assert f["/Point_Data"].attrs["Frequency Band"] == "1-11 GHz"

    def test_one_group_per_point_for_a_whole_raster(self, h5py, np, tmp_path):
        path = tmp_path / "scan.h5"
        points = [(x, y) for y in range(3) for x in range(4)]

        with h5py.File(path, "w") as f:
            for index, (x, y) in enumerate(points):
                f.create_dataset(
                    f"/Point_Data/[{x} {y}]/S11/data",
                    data=np.full(11, index, dtype=complex),
                )

        with h5py.File(path, "r") as f:
            assert len(f["/Point_Data"]) == len(points)
            # Each point kept its own measurement rather than overwriting a peer.
            for index, (x, y) in enumerate(points):
                assert f[f"/Point_Data/[{x} {y}]/S11/data"][0] == index

    def test_writing_the_same_point_twice_is_an_error_not_a_silent_overwrite(
        self, h5py, np, tmp_path
    ):
        """h5py refuses a duplicate name. That is the behaviour the scan loop
        depends on to notice an index collision instead of losing a point."""
        path = tmp_path / "scan.h5"
        with h5py.File(path, "w") as f:
            f.create_dataset("/Point_Data/[0 0]/S11/data", data=np.zeros(3))
            with pytest.raises(ValueError):
                f.create_dataset("/Point_Data/[0 0]/S11/data", data=np.ones(3))
