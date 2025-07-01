###############
#  Extracted this code from https://github.com/USCRPL/GeckoMoped/blob/master/geckomoped/assemble.py 
# 
# 
###############

class AddressMark(object):
    """Base class for all things which can end up with an address in the object code,
    including breakpoints and all types of instruction.

    Note that the address may be unresolved, in which case get_addr() will return None.
    For the purpose of binary code generation, source text-related functionalities
    (like 'tab' and 'mark') are removed.
    """
    def __init__(self, line, category=None): # Removed 'tab'
        self.addr = None
        self.line = line
        # self.mark = None # Mark-related attributes are removed
        # Removed tab-specific mark creation
        # if isinstance(category, str):
        #     tbuf = tab.buf()
        #     self.mark = tbuf.create_source_mark(None, category, tbuf.get_iter_at_line(self.line))
        #     self.mark.set_visible(False)

    # Removed methods that depend on 'tab' or 'mark'
    # def get_mark(self): ...
    # def get_tab(self): ...
    # def get_tbuf(self): ...
    # def get_iter(self): ...
    # def get_line(self): ...
    # def get_line_text(self): ...
    # def delete_mark(self): ...
    # def __del__(self): ...

    def get_addr(self):
        return self.addr

    def set_addr(self, addr):
        self.addr = addr


class Insn(AddressMark):
    def __init__(self, line): # Removed 'tab'
        """Abstract Base Class for all instructions.

        Note that several insns can be created from one source line when the
        comma separator is used for multiple axes.
        """
        super(Insn, self).__init__(line) # Removed 'tab'
        self.insn = 0xFFFFFFFF      # Actual object code (32-bit int).  Default to -1 to help
                                    # catch bugs.

    def get_binary(self):
        return self.insn

    def set_branch_field(self, value):
        self.insn &= 0xFFFF0000
        self.insn |= value & 0xFFFF

    def get_branch_field(self):
        return self.insn & 0xFFFF

    def set_lower_16(self, value):
        self.insn &= 0xFFFF0000
        self.insn |= value & 0xFFFF

    def set_lower_24(self, value):
        self.insn &= 0xFF000000
        self.insn |= value & 0xFFFFFF

    def set_lower_24_sign_mag(self, value):
        sign = 1
        if value < 0:
            sign = 0    # Yeah wierd: 0 sign for negative.
            value = -value
        self.insn &= 0xFF000000
        self.insn |= value & 0x7FFFFF
        self.insn |= sign << 23

    def set_lower_24_swapped(self, value):
        # Used in VELOCITY, ACCELERATION: shifted so that LSB is in command data field
        self.insn &= 0xFF000000
        self.insn |= (value & 0xFF) << 16
        self.insn |= value >> 8 & 0xFFFF

    def set_lower_24_swapped_sign_mag(self, value):
        # Used in SPEED CONTROL: shifted so that LSB is in command data field, sign magnitude
        # with sign bit in LSW[15]
        self.insn &= 0xFF000000
        sign = 0
        if value < 0:
            sign = 1
            value = -value
        self.insn |= (value & 0xFF) << 16
        self.insn |= value >> 8 & 0x7FFF
        self.insn |= sign << 15

    def set_upper_2(self, value):
        self.insn &= 0x3FFFFFFF
        self.insn |= (value & 0x3) << 30

    def set_upper_8(self, value):
        self.insn &= 0x00FFFFFF
        self.insn |= (value & 0xFF) << 24

    def get_upper_8(self):
        return self.insn >> 24 & 0xFF

    def set_command_data(self, value):
        self.insn &= 0xFF00FFFF
        self.insn |= (value & 0xFF) << 16

    def get_command_data(self):
        return self.insn >> 16 & 0xFF

    def set_opcode_6(self, value):
        self.insn &= 0xC0FFFFFF
        self.insn |= (value & 0x3F) << 24

    def set_opcode(self, value):    # standard 5-bit opcode
        self.insn &= 0xE0FFFFFF
        self.insn |= (value & 0x1F) << 24

    def set_sub_command(self, value):    # standard 3-bit sub-command
        self.insn &= 0x1FFFFFFF
        self.insn |= (value & 0x7) << 29

    def set_chain(self, chain):     # standard chain bit
        self.insn &= 0xDFFFFFFF
        self.insn |= (int(bool(chain)) & 0x1) << 29

    def get_chain(self):
        return (self.insn & 0x20000000) != 0

    def is_unresolved_branch(self):
        # Base class default is non-control-flow
        return False

    def is_chained(self):
        """Return whether this insn chains to the next.  Currently, this
        is only possible for MOVE, HOME or JOG."""
        return False

    def is_end_of_block(self):
        """Return whether this is an end-of-block branch i.e. the following
        instruction cannot execute unless it is labelled and somewhere else jumps to it.
        Currently, just unconditional GOTO, and RETURN"""
        return False

    def get_branch(self):
        """Return branch address.  Default None for all except GOTO, IF or CALL."""
        return None

    def is_nextable(self):
        """Return whether this instruction makes sense for the "step next" command.
        This applies to CALL, IF and GOTO with loop count."""
        return False

    def is_fast(self):
        """Return whether this insn is fast running i.e. a single query short
        will be sufficient to update local status.  Most insns are fast except
        for MOVE, HOME, JOG, SPEED CONTROL, WAIT."""
        return True

    def is_instant(self):
        """Return whether this insn is_fast() AND the next instruction address can be determined statically.
        If so, then a round-trip time to retrieve status/PC can be avoided.
        Return value is a (bool, int) tuple.  bool is True if instant, and int value (if True)
        is the next address.  The next address may only be valid after labels are resolved.
        Insns do not store their own address, so in the common case of returning 'addr+1', the
        int value is set to -1.
        """
        return False, 0

    def is_pos_valid(self):
        """Return whether reported position (from query long) is valid during execution of
        this instruction.  True except for HOME and SPEED CONTROL.
        """
        return True

    def is_vel_valid(self):
        """Return whether reported velocity (from query long) is valid during execution of
        this instruction.  Currently, always true.
        """
        return True

    def is_reset_offset(self):
        """Return whether this insn resets the device offset so that it should read as '0'
        from the current device position.  Currently, only the RESPOS insn does this.
        If returns True, then there must be a get_reset_offset() method which returns the
        device position which is reported to the user as '0'.
        """
        return False;


class AxisInsn(Insn):
    """ABC for all axis-specific instructions i.e. the opcode starts with X,Y,Z or W.
    """
    def __init__(self, line, axis): # Removed 'tab'
        """axis parameter is 0,1,2,3 for X,Y,Z,W respectively"""
        super(AxisInsn, self).__init__(line) # Removed 'tab'
        self.axis = axis
        self.set_upper_2(axis)

    def is_chained(self):
        return self.get_chain()
class AxisInsn(Insn):
    def __init__(self, line, axis):
        super(AxisInsn, self).__init__(line)
        self.axis = axis
        self.set_upper_2(axis)

    def is_chained(self):
        return self.get_chain()


class HomeInsn(AxisInsn):
    def __init__(self, line, axis, chain):
        super(HomeInsn, self).__init__(line, axis)
        self.set_chain(chain)
        self.set_opcode(0x02)
        self.set_lower_24(0)
    def is_fast(self):
        return False
    def is_pos_valid(self):
        return False

class MoveInsn(AxisInsn):
    """Move instructions.
    axis [+|-]n [, ...]
    Note that several of these can be chained on one line (comma) but this class instance
    is created for one at a time.
    """
    def __init__(self, line, axis, relative, n, chain): # Removed 'tab'
        """relative is 0 for absolute, 1 or -1 for relative (specifying sign)."""
        super(MoveInsn, self).__init__(line, axis) # Removed 'tab'
        self.set_chain(chain)
        self.set_opcode(0x01 if relative else 0x00)
        if relative:
            n *= relative
            self.set_lower_24_sign_mag(n)
        else:
            self.set_lower_24(n)
        if relative and (n < -0x7FFFFF or n > 0x7FFFFF) or \
           not relative and (n < 0 or n > 0xFFFFFF):
            # If CodeError is a dependency, you might need to define a dummy one
            # for this standalone script, or remove the error checking if not needed.
            # raise CodeError(self, "%s amount %d out of range for axis %d" % \
            #     ("Relative move" if relative else "Move", n, axis))
            print(f"Warning: {('Relative move' if relative else 'Move')} amount {n} out of range for axis {axis}")
    def is_fast(self):
        return False
    
class ConfigureInsn(AxisInsn):
    """Configure instructions.
    axis CONFIGURE i AMPS, IDLE AT p% AFTER s SECONDS
    i is float in range 0..7.0
    p is int in range 0..99
    s is float in range 0..25.5
    """
    def __init__(self, line, axis, i, p, s): # Removed 'tab'
        super(ConfigureInsn, self).__init__(line, axis) # Removed 'tab'
        if i < 0. or i > 7.:
            raise ValueError("Current %f out of range [0..7.0]" % i) # Changed CodeError to ValueError
        if p < 0. or p > 99.:
            raise ValueError("Percent idle current %f out of range [0..99.0]" % p) # Changed CodeError to ValueError
        if s < 0. or s > 25.5:
            raise ValueError("Time to idle %f out of range [0..25.5]" % s) # Changed CodeError to ValueError
        i = int(i*10)
        s = int(s*10)
        p = int(p)
        self.set_opcode_6(0x0E)
        self.set_command_data(i)
        self.set_lower_16(p<<8 | s)
    def is_instant(self):
        return True, -1

class ClockwiseLimitInsn(AxisInsn):
    """Clockwise Limit instructions.
    axis LIMIT CW n
    """
    def __init__(self, line, axis, n): # Removed 'tab'
        super(ClockwiseLimitInsn, self).__init__(line, axis) # Removed 'tab'
        self.set_opcode_6(0x0F)
        self.set_lower_24(n)
        if n < 0 or n > 0xFFFFFF:
            raise ValueError("Clockwise limit %d out of range" % n) # Changed CodeError to ValueError
    def is_instant(self):
        return True, -1

class CompareInsn(AxisInsn):
    """Compare instructions.
    axis COMPARE VALUE n
    """
    def __init__(self, line, axis, n): # Removed 'tab'
        super(CompareInsn, self).__init__(line, axis) # Removed 'tab'
        self.set_opcode_6(0x14)
        self.set_lower_24(n)
        if n < 0 or n > 0xFFFFFF:
            raise ValueError("Compare value %d out of range" % n) # Changed CodeError to ValueError
    def is_instant(self):
        return True, -1

class AccelerationInsn(AxisInsn):
    """Accel instructions.
    axis ACCELERATION n
    """
    def __init__(self, line, axis, n): # Removed 'tab'
        super(AccelerationInsn, self).__init__(line, axis) # Removed 'tab'
        self.set_opcode_6(0x0C)
        if n < 0 or n > 0xFFFF:
            raise ValueError("Acceleration %f out of range" % float(n)) # Changed CodeError to ValueError
        self.set_lower_24_swapped(int(n)*256)
    def is_instant(self):
        return True, -1

class VelocityInsn(AxisInsn):
    """Velocity instructions.
    axis VELOCITY n
    """
    def __init__(self, line, axis, n): # Removed 'tab'
        super(VelocityInsn, self).__init__(line, axis) # Removed 'tab'
        self.set_opcode_6(0x07)
        if n < 0 or n > 0xFFFF:
            raise ValueError("Velocity %f out of range" % float(n)) # Changed CodeError to ValueError
        self.set_lower_24_swapped(int(n)*256)
    def is_instant(self):
        return True, -1

class PositionAdjustInsn(AxisInsn):
    """PositionAdjust instructions.
    axis POSITION ADJUST n
    """
    def __init__(self, line, axis, n): # Removed 'tab'
        super(PositionAdjustInsn, self).__init__(line, axis) # Removed 'tab'
        self.set_opcode_6(0x10)
        self.set_command_data(0)
        self.set_lower_16(n)
        if n < -0x8000 or n > 0x7FFF:
            raise ValueError("Position adjust %d out of range" % n) # Changed CodeError to ValueError

class SpeedControlInsn(AxisInsn):
    """SpeedControl instructions.
    axis SPEED CONTROL n
    """
    def __init__(self, line, axis, n): # Removed 'tab'
        super(SpeedControlInsn, self).__init__(line, axis) # Removed 'tab'
        self.set_opcode_6(0x0D)
        if n < -0x800000 or n > 0x7FFFFF:
            raise ValueError("Speed control %f out of range" % float(n)) # Changed CodeError to ValueError
        self.set_lower_24_swapped_sign_mag(int(n)*256)
    def is_fast(self):
        return False
    def is_pos_valid(self):
        return False

class OutInsn(AxisInsn):
    """Out instructions.
    axis OUTn state
    n is 1,2,3
    state is OutInsn.{OFF|ON|BR|RS|ERR}
    """
    OFF = 0
    ON = 1
    BR = 2
    RS = 3
    ERR = 4
    def __init__(self, line, axis, n, state): # Removed 'tab'
        super(OutInsn, self).__init__(line, axis) # Removed 'tab'
        self.set_opcode_6(0x06)
        self.set_command_data((n&3)<<4 | state&0x0F)
        self.set_lower_16(0)
        if n not in [1,2,3]:
            raise ValueError("Output number %d out of range [1,2,3]" % n) # Changed CodeError to ValueError
        if state not in [0,1,2,3,4]:
            raise ValueError("State %d out of range [OFF,ON,BR,RS,ERR]" % state) # Changed CodeError to ValueError
        
        
# motion_insn = MoveInsn(line=0,axis=0,relative=0,n=10,chain=False)
# print(f"motioninsn {motion_insn.get_binary():#010x}")


# home_insn = HomeInsn(line=0, axis=0, chain=True)
# print(f"HomeInsn (HOME X, chained): {home_insn.get_binary():#010x}")

# # ConfigureInsn: X CONFIGURE 5.0 AMPS, IDLE AT 50% AFTER 10.0 SECONDS
# configure_insn = ConfigureInsn(line=0, axis=1, i=1.5, p=15, s=1.5)
# print(f"ConfigureInsn (X CONFIGURE 5.0 AMPS, IDLE AT 50% AFTER 10.0 SECONDS): {configure_insn.get_binary():#010x}")

# # ClockwiseLimitInsn: X LIMIT CW 1000
# clockwise_limit_insn = ClockwiseLimitInsn(line=0, axis=0, n=1000)
# print(f"ClockwiseLimitInsn (X LIMIT CW 1000): {clockwise_limit_insn.get_binary():#010x}")

# # CompareInsn: X COMPARE VALUE 500
# compare_insn = CompareInsn(line=0, axis=0, n=500)
# print(f"CompareInsn (X COMPARE VALUE 500): {compare_insn.get_binary():#010x}")

# # AccelerationInsn: X ACCELERATION 256
# acceleration_insn = AccelerationInsn(line=0, axis=0, n=256)
# print(f"AccelerationInsn (X ACCELERATION 256): {acceleration_insn.get_binary():#010x}")

# # VelocityInsn: X VELOCITY 1000
# velocity_insn = VelocityInsn(line=0, axis=0, n=1000)
# print(f"VelocityInsn (X VELOCITY 1000): {velocity_insn.get_binary():#010x}")

# # PositionAdjustInsn: X POSITION ADJUST 1234
# position_adjust_insn = PositionAdjustInsn(line=0, axis=0, n=1234)
# print(f"PositionAdjustInsn (X POSITION ADJUST 1234): {position_adjust_insn.get_binary():#010x}")

# # SpeedControlInsn: X SPEED CONTROL 100000
# speed_control_insn = SpeedControlInsn(line=0, axis=0, n=100000)
# print(f"SpeedControlInsn (X SPEED CONTROL 100000): {speed_control_insn.get_binary():#010x}")

# # OutInsn: X OUT1 ON
# out_insn = OutInsn(line=0, axis=0, n=1, state=OutInsn.ON)
# print(f"OutInsn (X OUT1 ON): {out_insn.get_binary():#010x}")