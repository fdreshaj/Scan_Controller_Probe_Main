"""Binary encoding for the Gecko G-series motion controller.

These 32-bit words go straight down the serial link to a motor drive. A wrong
opcode or a misplaced sign bit does not raise an exception -- it moves a real
gantry to the wrong place, possibly through an endstop. So this file asserts on
exact hex values, field by field, rather than on round-trip behaviour.

Field layout (from GeckoMoped's assemble.py, which this module was extracted
from):

    bits 31-30   axis      (X=0, Y=1, Z=2, W=3)
    bit  29      chain     (also the low bit of a 3-bit sub-command)
    bits 28-24   opcode    (6-bit opcodes overlap bit 29)
    bits 23-16   command data
    bits 15-0    payload / branch field
"""

import pytest

import scanner.Plugins.geckoInstructions as gecko

pytestmark = pytest.mark.protocol

AXIS_X, AXIS_Y, AXIS_Z, AXIS_W = 0, 1, 2, 3


def field(word, high, low):
    """Extract bits [high:low] inclusive from a 32-bit instruction word."""
    return (word >> low) & ((1 << (high - low + 1)) - 1)


class TestBitFieldPrimitives:
    """The setters every instruction is built from."""

    @pytest.fixture
    def insn(self):
        return gecko.Insn(line=0)

    def test_a_fresh_instruction_is_the_poison_value(self, insn):
        """0xFFFFFFFF is deliberate: it makes an unset instruction obvious."""
        assert insn.get_binary() == 0xFFFFFFFF

    def test_set_upper_2_writes_the_axis_and_clears_nothing_else(self, insn):
        insn.set_upper_2(AXIS_Z)
        assert field(insn.get_binary(), 31, 30) == AXIS_Z
        assert field(insn.get_binary(), 29, 0) == 0x3FFFFFFF

    def test_set_upper_2_masks_to_two_bits(self, insn):
        insn.set_upper_2(0b111)
        assert field(insn.get_binary(), 31, 30) == 0b11

    def test_set_opcode_writes_five_bits(self, insn):
        insn.set_opcode(0x1F)
        assert field(insn.get_binary(), 28, 24) == 0x1F

    def test_set_opcode_preserves_the_chain_bit(self, insn):
        insn.insn = 0
        insn.set_chain(True)
        insn.set_opcode(0x02)
        assert insn.get_chain() is True
        assert field(insn.get_binary(), 28, 24) == 0x02

    def test_set_opcode_6_overlaps_the_chain_bit(self, insn):
        """A 6-bit opcode occupies bit 29, so it and `chain` are exclusive.

        This is why CONFIGURE, VELOCITY and friends are never chained.
        """
        insn.insn = 0
        insn.set_chain(True)
        insn.set_opcode_6(0x0E)
        assert field(insn.get_binary(), 29, 24) == 0x0E

    def test_chain_bit_roundtrips(self, insn):
        insn.set_chain(True)
        assert insn.get_chain() is True
        insn.set_chain(False)
        assert insn.get_chain() is False

    def test_command_data_roundtrips(self, insn):
        insn.set_command_data(0xAB)
        assert insn.get_command_data() == 0xAB
        assert field(insn.get_binary(), 23, 16) == 0xAB

    def test_lower_16_masks_overflow(self, insn):
        insn.set_lower_16(0x1FFFF)
        assert field(insn.get_binary(), 15, 0) == 0xFFFF

    def test_lower_24_masks_overflow(self, insn):
        insn.set_lower_24(0x1FFFFFF)
        assert field(insn.get_binary(), 23, 0) == 0xFFFFFF

    def test_sign_magnitude_uses_zero_for_negative(self, insn):
        """The drive's convention is inverted from the usual one.

        `set_lower_24_sign_mag` writes sign=0 for a negative value and sign=1
        for positive. Getting this backwards reverses every relative move, so
        it is worth an explicit test.
        """
        insn.set_lower_24_sign_mag(100)
        assert field(insn.get_binary(), 23, 23) == 1, "positive -> sign bit set"
        assert field(insn.get_binary(), 22, 0) == 100

        insn.set_lower_24_sign_mag(-100)
        assert field(insn.get_binary(), 23, 23) == 0, "negative -> sign bit clear"
        assert field(insn.get_binary(), 22, 0) == 100

    def test_swapped_encoding_puts_the_low_byte_in_the_command_field(self, insn):
        """VELOCITY and ACCELERATION ship the LSB up in the command-data byte."""
        insn.insn = 0
        insn.set_lower_24_swapped(0xABCDEF)
        assert field(insn.get_binary(), 23, 16) == 0xEF, "LSB moved up"
        assert field(insn.get_binary(), 15, 0) == 0xABCD, "remainder shifted down"

    def test_swapped_sign_magnitude_puts_the_sign_in_bit_15(self, insn):
        insn.insn = 0
        insn.set_lower_24_swapped_sign_mag(-0x010200)
        assert field(insn.get_binary(), 15, 15) == 1, "negative -> sign bit set"
        insn.insn = 0
        insn.set_lower_24_swapped_sign_mag(0x010200)
        assert field(insn.get_binary(), 15, 15) == 0


class TestInstructionWords:
    """Whole instructions, asserted as exact 32-bit words."""

    def test_home(self):
        assert gecko.HomeInsn(line=0, axis=AXIS_X, chain=False).get_binary() == 0x02000000

    def test_home_on_y_with_chain(self):
        # axis 1 -> 0x40000000, chain -> 0x20000000, opcode 0x02 -> 0x02000000
        assert gecko.HomeInsn(line=0, axis=AXIS_Y, chain=True).get_binary() == 0x62000000

    def test_home_carries_no_payload(self):
        word = gecko.HomeInsn(line=0, axis=AXIS_W, chain=False).get_binary()
        assert field(word, 23, 0) == 0

    def test_absolute_move(self):
        word = gecko.MoveInsn(line=0, axis=AXIS_X, relative=0, n=10, chain=False).get_binary()
        assert word == 0x0000000A
        assert field(word, 28, 24) == 0x00, "absolute move opcode"

    def test_relative_move_is_a_different_opcode(self):
        word = gecko.MoveInsn(line=0, axis=AXIS_X, relative=1, n=10, chain=False).get_binary()
        assert field(word, 28, 24) == 0x01, "relative move opcode"

    def test_negative_relative_move(self):
        # axis 2 -> 0x80000000, opcode 0x01 -> 0x01000000, sign 0 (negative), magnitude 5
        word = gecko.MoveInsn(line=0, axis=AXIS_Z, relative=1, n=-5, chain=False).get_binary()
        assert word == 0x81000005

    def test_positive_and_negative_relative_moves_differ_only_in_the_sign_bit(self):
        pos = gecko.MoveInsn(line=0, axis=AXIS_X, relative=1, n=500, chain=False).get_binary()
        neg = gecko.MoveInsn(line=0, axis=AXIS_X, relative=1, n=-500, chain=False).get_binary()
        assert pos ^ neg == 1 << 23

    def test_configure(self):
        # i=1.5A -> 15 in command data; p=15%, s=1.5s -> 15 -> 0x0F0F payload
        word = gecko.ConfigureInsn(line=0, axis=AXIS_Y, i=1.5, p=15, s=1.5).get_binary()
        assert word == 0x4E0F0F0F
        assert field(word, 29, 24) == 0x0E, "6-bit CONFIGURE opcode"
        assert field(word, 23, 16) == 15, "current in tenths of an amp"
        assert field(word, 15, 8) == 15, "idle percent"
        assert field(word, 7, 0) == 15, "idle timeout in tenths of a second"

    def test_velocity(self):
        word = gecko.VelocityInsn(line=0, axis=AXIS_X, n=1000).get_binary()
        assert word == 0x070003E8
        assert field(word, 29, 24) == 0x07

    def test_acceleration(self):
        word = gecko.AccelerationInsn(line=0, axis=AXIS_X, n=256).get_binary()
        assert word == 0x0C000100
        assert field(word, 29, 24) == 0x0C

    def test_speed_control(self):
        word = gecko.SpeedControlInsn(line=0, axis=AXIS_X, n=1000).get_binary()
        assert word == 0x0D0003E8

    def test_position_adjust(self):
        word = gecko.PositionAdjustInsn(line=0, axis=AXIS_X, n=1234).get_binary()
        assert word == 0x100004D2
        assert field(word, 15, 0) == 1234

    def test_out(self):
        word = gecko.OutInsn(line=0, axis=AXIS_X, n=1, state=gecko.OutInsn.ON).get_binary()
        assert word == 0x06110000

    def test_clockwise_limit_carries_its_value(self):
        word = gecko.ClockwiseLimitInsn(line=0, axis=AXIS_X, n=1000).get_binary()
        assert field(word, 29, 24) == 0x0F
        assert field(word, 23, 0) == 1000

    def test_compare_carries_its_value(self):
        word = gecko.CompareInsn(line=0, axis=AXIS_X, n=500).get_binary()
        assert field(word, 29, 24) == 0x14
        assert field(word, 23, 0) == 500

    @pytest.mark.parametrize("axis", [AXIS_X, AXIS_Y, AXIS_Z, AXIS_W])
    def test_the_axis_lands_in_the_top_two_bits_for_every_instruction(self, axis):
        for word in (
            gecko.HomeInsn(line=0, axis=axis, chain=False).get_binary(),
            gecko.MoveInsn(line=0, axis=axis, relative=0, n=1, chain=False).get_binary(),
            gecko.VelocityInsn(line=0, axis=axis, n=1).get_binary(),
            gecko.AccelerationInsn(line=0, axis=axis, n=1).get_binary(),
        ):
            assert field(word, 31, 30) == axis

    @pytest.mark.parametrize(
        "make",
        [
            pytest.param(lambda a: gecko.HomeInsn(0, a, False), id="home"),
            pytest.param(lambda a: gecko.MoveInsn(0, a, 0, 1, False), id="move"),
            pytest.param(lambda a: gecko.VelocityInsn(0, a, 1), id="velocity"),
            pytest.param(lambda a: gecko.ConfigureInsn(0, a, 1.0, 10, 1.0), id="configure"),
        ],
    )
    def test_every_instruction_fits_in_32_bits(self, make):
        word = make(AXIS_W).get_binary()
        assert 0 <= word <= 0xFFFFFFFF


class TestRangeChecking:
    """Out-of-range values must be refused before they reach the drive."""

    @pytest.mark.parametrize("amps", [-0.1, 7.1, 100.0])
    def test_configure_rejects_out_of_range_current(self, amps):
        with pytest.raises(ValueError):
            gecko.ConfigureInsn(line=0, axis=AXIS_X, i=amps, p=50, s=1.0)

    @pytest.mark.parametrize("percent", [-1, 100, 250])
    def test_configure_rejects_out_of_range_idle_percent(self, percent):
        with pytest.raises(ValueError):
            gecko.ConfigureInsn(line=0, axis=AXIS_X, i=1.0, p=percent, s=1.0)

    @pytest.mark.parametrize("seconds", [-0.1, 25.6, 60.0])
    def test_configure_rejects_out_of_range_idle_timeout(self, seconds):
        with pytest.raises(ValueError):
            gecko.ConfigureInsn(line=0, axis=AXIS_X, i=1.0, p=50, s=seconds)

    def test_configure_accepts_the_exact_bounds(self):
        gecko.ConfigureInsn(line=0, axis=AXIS_X, i=0.0, p=0, s=0.0)
        gecko.ConfigureInsn(line=0, axis=AXIS_X, i=7.0, p=99, s=25.5)

    @pytest.mark.parametrize("n", [-1, 0x10000])
    def test_velocity_rejects_out_of_range(self, n):
        with pytest.raises(ValueError):
            gecko.VelocityInsn(line=0, axis=AXIS_X, n=n)

    @pytest.mark.parametrize("n", [-1, 0x10000])
    def test_acceleration_rejects_out_of_range(self, n):
        with pytest.raises(ValueError):
            gecko.AccelerationInsn(line=0, axis=AXIS_X, n=n)

    @pytest.mark.parametrize("n", [-1, 0x1000000])
    def test_clockwise_limit_rejects_out_of_range(self, n):
        with pytest.raises(ValueError):
            gecko.ClockwiseLimitInsn(line=0, axis=AXIS_X, n=n)

    @pytest.mark.parametrize("n", [-0x8001, 0x8000])
    def test_position_adjust_rejects_out_of_range(self, n):
        with pytest.raises(ValueError):
            gecko.PositionAdjustInsn(line=0, axis=AXIS_X, n=n)

    @pytest.mark.parametrize("out_number", [0, 4, -1])
    def test_out_rejects_an_invalid_output_number(self, out_number):
        with pytest.raises(ValueError):
            gecko.OutInsn(line=0, axis=AXIS_X, n=out_number, state=gecko.OutInsn.ON)

    def test_out_rejects_an_invalid_state(self):
        with pytest.raises(ValueError):
            gecko.OutInsn(line=0, axis=AXIS_X, n=1, state=99)

    @pytest.mark.xfail(
        strict=True,
        reason=(
            "MoveInsn prints a warning for an out-of-range distance instead of "
            "raising, because the original CodeError dependency was dropped when "
            "this file was extracted from GeckoMoped. The value is then masked to "
            "24 bits by set_lower_24, so a move of 0x1000005 steps silently "
            "becomes a move of 5 steps and the gantry ends up somewhere the "
            "software does not believe it to be. Every sibling instruction "
            "(VELOCITY, ACCELERATION, CONFIGURE, ...) raises ValueError here."
        ),
    )
    def test_move_rejects_an_out_of_range_absolute_distance(self):
        with pytest.raises(ValueError):
            gecko.MoveInsn(line=0, axis=AXIS_X, relative=0, n=0x1000005, chain=False)

    def test_move_currently_truncates_instead_of_raising(self):
        """The live counterpart to the xfail above: what actually happens today."""
        word = gecko.MoveInsn(
            line=0, axis=AXIS_X, relative=0, n=0x1000005, chain=False
        ).get_binary()
        assert field(word, 23, 0) == 5, "the high bits were silently discarded"


class TestClassHierarchy:
    def test_every_axis_instruction_derives_from_axisinsn(self):
        """The duplicate AxisInsn definition removed in the dead-code pass meant
        subclasses could have bound to a shadowed base. They must all share one."""
        for cls in (
            gecko.HomeInsn,
            gecko.MoveInsn,
            gecko.ConfigureInsn,
            gecko.ClockwiseLimitInsn,
            gecko.CompareInsn,
            gecko.AccelerationInsn,
            gecko.VelocityInsn,
            gecko.PositionAdjustInsn,
            gecko.SpeedControlInsn,
            gecko.OutInsn,
        ):
            assert issubclass(cls, gecko.AxisInsn), cls.__name__

    def test_axisinsn_is_defined_exactly_once(self):
        """A second `class AxisInsn` would silently orphan half the hierarchy."""
        import ast
        import inspect

        source = inspect.getsource(gecko)
        names = [
            node.name
            for node in ast.walk(ast.parse(source))
            if isinstance(node, ast.ClassDef)
        ]
        assert names.count("AxisInsn") == 1

    def test_the_axis_is_stored_as_an_attribute(self):
        insn = gecko.HomeInsn(line=0, axis=AXIS_Z, chain=False)
        assert insn.axis == AXIS_Z

    def test_address_starts_unresolved(self):
        assert gecko.HomeInsn(line=0, axis=AXIS_X, chain=False).get_addr() is None
