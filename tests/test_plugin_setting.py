"""PluginSetting is the validation layer between operator typing and hardware.

Every number an operator types into the GUI arrives here as a string. If a
malformed or out-of-range value gets through, it becomes a velocity or a travel
distance on a real gantry, so these tests are about the boundaries.
"""

import pytest

from scanner.plugin_setting import (
    PluginSettingFloat,
    PluginSettingInteger,
    PluginSettingString,
)

pytestmark = pytest.mark.contract


class TestPluginSettingString:
    def test_roundtrips_a_plain_value(self):
        s = PluginSettingString("File Name: ", "scan_001")
        assert s.value == "scan_001"
        assert s.get_value_as_string() == "scan_001"

        s.set_value_from_string("scan_002")
        assert s.value == "scan_002"

    def test_unrestricted_setting_accepts_anything(self):
        s = PluginSettingString("Notes", "", select_options=["a", "b"])
        s.set_value_from_string("something else entirely")
        assert s.value == "something else entirely"

    def test_restricted_setting_rejects_values_outside_its_options(self):
        s = PluginSettingString(
            "Pattern Type", "YX", select_options=["YX", "XY"], restrict_selections=True
        )
        with pytest.raises(ValueError):
            s.set_value_from_string("ZZ")
        assert s.value == "YX", "a rejected value must not corrupt the setting"

    def test_restricted_setting_accepts_a_listed_option(self):
        s = PluginSettingString(
            "Pattern Type", "YX", select_options=["YX", "XY"], restrict_selections=True
        )
        s.set_value_from_string("XY")
        assert s.value == "XY"

    def test_hints_expose_the_selection_options(self):
        s = PluginSettingString("Scanner Type", "Big Scanner",
                                select_options=["Big Scanner", "Small Scanner"])
        assert s.get_hints() == ("Big Scanner", "Small Scanner")

    def test_options_are_copied_not_aliased(self):
        """A caller's list must not be able to widen the setting after the fact."""
        options = ["YX"]
        s = PluginSettingString("Pattern", "YX", select_options=options,
                                restrict_selections=True)
        options.append("XY")
        with pytest.raises(ValueError):
            s.set_value_from_string("XY")

    def test_two_instances_do_not_share_options(self):
        """Guards the mutable default argument `select_options=[]`.

        `PluginSettingString.__init__` declares `select_options: list[str] = []`.
        That default list is created once at import time and shared by every
        instance built without explicit options, so if it were ever mutated in
        place the leak would reach every setting in the app. `list(...)` in the
        constructor currently prevents that -- this test keeps it that way.
        """
        a = PluginSettingString("A", "x")
        b = PluginSettingString("B", "y")
        a.selection_options.append("polluted")
        assert b.selection_options == []


class TestPluginSettingInteger:
    def test_parses_a_string(self):
        s = PluginSettingInteger("Points", 10)
        s.set_value_from_string("42")
        assert s.value == 42
        assert s.get_value_as_string() == "42"

    def test_rejects_a_non_numeric_string(self):
        s = PluginSettingInteger("Points", 10)
        with pytest.raises(ValueError):
            s.set_value_from_string("ten")
        assert s.value == 10

    @pytest.mark.parametrize("bad", ["3.7", "", " ", "0x10", "1e3"])
    def test_rejects_values_that_are_not_plain_integers(self, bad):
        s = PluginSettingInteger("Points", 10)
        with pytest.raises(ValueError):
            s.set_value_from_string(bad)

    def test_enforces_the_minimum(self):
        s = PluginSettingInteger("Channels", 2, value_min=1)
        with pytest.raises(ValueError):
            s.set_value_from_string("0")
        assert s.value == 2

    def test_enforces_the_maximum(self):
        s = PluginSettingInteger("Channels", 2, value_max=4)
        with pytest.raises(ValueError):
            s.set_value_from_string("5")

    def test_accepts_the_exact_bounds(self):
        s = PluginSettingInteger("Channels", 2, value_min=1, value_max=4)
        s.set_value_from_string("1")
        assert s.value == 1
        s.set_value_from_string("4")
        assert s.value == 4

    def test_inverted_bounds_are_rejected_at_construction(self):
        with pytest.raises(ValueError):
            PluginSettingInteger("Bad", 0, value_min=10, value_max=1)

    def test_a_default_outside_its_own_bounds_is_rejected(self):
        with pytest.raises(ValueError):
            PluginSettingInteger("Points", 0, value_min=1)


class TestPluginSettingFloat:
    def test_parses_a_string(self):
        s = PluginSettingFloat("Step Size(mm): ", 2.0)
        s.set_value_from_string("0.5")
        assert s.value == pytest.approx(0.5)

    def test_rejects_a_non_numeric_string(self):
        s = PluginSettingFloat("Step Size(mm): ", 2.0)
        with pytest.raises(ValueError):
            s.set_value_from_string("half a mm")
        assert s.value == pytest.approx(2.0)

    def test_enforces_bounds(self):
        s = PluginSettingFloat("Measurement Time (s)", 0.5, value_min=0.0)
        with pytest.raises(ValueError):
            s.set_value_from_string("-0.1")

    def test_accepts_scientific_notation(self):
        s = PluginSettingFloat("Frequency (Hz)", 1e9)
        s.set_value_from_string("2.4e9")
        assert s.value == pytest.approx(2.4e9)

    @pytest.mark.parametrize("hazard", ["inf", "-inf"])
    def test_infinities_are_caught_by_the_bounds(self, hazard):
        s = PluginSettingFloat("Step Size(mm): ", 2.0, value_min=0.0, value_max=100.0)
        with pytest.raises(ValueError):
            s.set_value_from_string(hazard)
        assert s.value == pytest.approx(2.0)

    def test_nan_slips_through_the_bounds_check(self):
        """Documents a real gap rather than asserting the behaviour is right.

        Every comparison against NaN is False, so `nan < value_min` and
        `nan > value_max` are both False and the bounds check waves it through.
        A NaN step size or velocity therefore reaches the motion driver intact,
        and nothing downstream rejects it either.

        If the setter is ever tightened with a `math.isfinite` check, this test
        will fail -- that is the point. Invert it to a `pytest.raises` then.
        """
        s = PluginSettingFloat("Step Size(mm): ", 2.0, value_min=0.0, value_max=100.0)
        s.set_value_from_string("nan")
        assert s.value != s.value, "NaN reached the setting unchallenged"

    def test_nan_is_also_unbounded_when_no_limits_are_set(self):
        s = PluginSettingFloat("Rotation Angle CC deg: ", 0.0)
        s.set_value_from_string("nan")
        assert s.value != s.value


class TestRepr:
    def test_repr_names_the_label_and_value(self):
        """The GUI and the console log both lean on this."""
        s = PluginSettingFloat("Step Size(mm): ", 2.0)
        text = repr(s)
        assert "PluginSettingFloat" in text
        assert "Step Size(mm): " in text
        assert "2.0" in text
