import time
import ftd2xx as ftd
import numpy as np
import inspect

#ADF4159 PLL Constants
SINGLE_SAW_TOOTH = 2

MUXOUTCTL_TRIST = 0x0
MUXOUTCTL_DVDD = 0x1
MUXOUTCTL_DGND = 0x2
MUXOUTCTL_R_DIVIDER_OUTPUT = 0x3
MUXOUTCTL_N_DIVIDER_OUTPUT = 0x4
MUXOUTCTL_DIGITAL_LOCK_DETECT = 0x6
MUXOUTCTL_SERIAL_DATA_OUTPUT = 0x7
MUXOUTCTL_CLK_DIVIDER_OUTPUT = 0xa
MUXOUTCTL_R_DIVIDER_2 = 0xD
MUXOUTCTL_N_DIVIDER_2 = 0xE
MUXOUTCTL_READBACK_TO_MUXOUT = 0xF



# D2xx programmers guide
# https://ftdichip.com/wp-content/uploads/2025/06/D2XX_Programmers_Guide.pdf

# FT232H masks
# name - mask - pin on 232H -   direction - state
SK = 1<<0 #   ADBUS0            out         low
DO = 1<<1 #   ADBUS1            out         low
DI = 1<<2 #   ADBUS2            in          low (don't care for now)
CS = 1<<3 #   ADBUS3            out         high (pll chip select is active low)
GPIOL0 = 1<<4#ADBUS4            out         low     NC
GPIOL1 = 1<<5#ADBUS5            out         low     NC  
GPIOL2 = 1<<6#ADBUS6            out         low     NC
GPIOL3 = 1<<7#ADBUS7            out         low     NC
#                               0xfb        0x00 ----- mpsse cmd -> 0x80, 0x00, 0xfb

GPIOH0 = 1<<0 #ACBUS0           out         high    (DIVEN_3V3A)
GPIOH1 = 1<<1 #ACBUS1           out         low     (INJEN_3V3A)
GPIOH2 = 1<<2 #ACBUS2           out         high    (RCP_3V3A)
GPIOH3 = 1<<3 #ACBUS3           out         high    (RXEN_3V3A)
GPIOH4 = 1<<4 #ACBUS4           out         high    (TXEN_3V3A)
GPIOH5 = 1<<5 #ACBUS5           out         high    (VCOEN_3V3A)
# GPIOH6 = 1<<6 #ACBUS6           out         LOW     (NC)
# GPIOH7 = 1<<7 #ACBUS7           out         LOW     (VBUSDTCT) 

value_byte_low = 0x08
dir_byte_low = 0xFB

value_byte_high = 0x3D
dir_byte_high = 0xFF

## MPSSE opcodes
set_data_bytes_low_b = 0x80 # followed by 0x(Value Byte) 0x(Direction Byte)
set_data_bytes_high_b = 0x82 # followed by 0x(Value Byte) 0x(Direction Byte)
clk_data_out_neg_ve = 0x11 # data changes on negative edge
set_clk_divisor = 0x86

#d2xx constants
FT_BITMODE_MPSSE = 0x02
FT_BITMODE_RESET = 0x00

def set_spi_clock(d, hz):
    """Set SPI clock rate"""
    div = int((60e6 / (hz * 2)) - 1) 
    ft_write(d, (set_clk_divisor, div % 256, div // 256))

def ft_write(d, data):
    """Write integers as byte data"""
    s = str(bytearray(data))
    s = bytes(data)
    return d.write(s)

def ft_read(d, nbytes):
    """Read byte data into list of integers"""
    s = d.read(nbytes)
    return [ord(c) for c in s] if type(s) is str else list(s)


def ft_write_cmd_bytes(d, cmd, data):
    """write MPSSE comand with word -value argument"""
    n = len(data) - 1
    ft_write(d, [cmd, n % 256, n // 256] + list(data))

def bytesToString(data):
    return "b'" + ''.join('\\x{:02x}'.format(byte) for byte in data) + "'"

def getFTDevByDesc(desc: str):
    encDesc = desc.encode("utf-8")
    devs = ftd.listDevices(ftd.defines.OPEN_BY_DESCRIPTION)
    dev = None
    for d in devs:
        if encDesc == d:
            dev = ftd.openEx(encDesc, flags=ftd.defines.OPEN_BY_DESCRIPTION)
    if not dev:
              raise(Exception("FTDI device not found"))
    return dev

def openFTDevByDesc_sn(descriptor:str, sn:int):
    """ Opens device by descripter and SN"""
    devDict = dict(zip(ftd.listDevices(ftd.defines.OPEN_BY_DESCRIPTION), ftd.listDevices()))
    radar = None
    if descriptor.encode() in devDict.keys():
        if int(devDict[descriptor.encode()]) == sn:
            radar = ftd.openEx(devDict[descriptor.encode()])
    if not radar:
        raise(Exception(f"FTDI Device {descriptor} SN:{sn} not found"))
    return radar
        
def initFtdiSPI(device:ftd.FTD2XX, spi_clk_Hz = 1e6):
    """initialize fdti cable for SPI"""
    device.resetDevice()
    device.setUSBParameters(65536, 65536)
    device.setChars(0, 0, 0, 0)
    device.setTimeouts(1000, 1000)
    device.setLatencyTimer(20)
    device.setBitMode(0, FT_BITMODE_RESET)
    device.setBitMode(0x00, FT_BITMODE_MPSSE)
    time.sleep(1/20)
    set_spi_clock(device, spi_clk_Hz)

def setGPIOH(device, value_byte):
    """sets gpio high byte"""
    ft_write(device, (set_data_bytes_high_b, value_byte, dir_byte_high))

def writeRadar(device, *cmds):
    """writes 32 bit command to the radar board pll"""
    for cmd in cmds:
        cmd = list(cmd.to_bytes(4, 'big'))
        ft_write(device, (set_data_bytes_low_b, value_byte_low & ~CS , dir_byte_low))
        ft_write_cmd_bytes(device, clk_data_out_neg_ve, cmd)
        ft_write(device, (set_data_bytes_low_b, value_byte_low, dir_byte_low))

def getFpfd(**kwargs):
   """Get Frequency of PFD"""
   return kwargs.get("refIn", 50e6)*((1 + kwargs.get("refInRefDoubler", False))/(kwargs.get("R_counter", 1) * (1 + kwargs.get("rDivide_2", True))))

def getIntFrac(freqGHz: float, **kwargs):
    """returns INT and FRAC lsb and msb values for register 0 and 1"""
    freqGHz = freqGHz/kwargs.get("extPrescale", 72)
    fpfd = getFpfd(**kwargs)
    INT = int((freqGHz*1e9)/fpfd)
    Fmsb = int(((freqGHz * 1e9/fpfd) - INT) * 2**12)
    Flsb = int(((((freqGHz * 1e9/fpfd) - INT) * 2**12) - Fmsb) * 2**13)
    FRAC = Fmsb * 2**13 + Flsb
    kwargs.setdefault("INT", INT)
    kwargs.setdefault("FRAC", FRAC)
    kwargs.setdefault("Fmsb", Fmsb)
    kwargs.setdefault("Flsb", Flsb)
    return kwargs

def getR0(**kwargs):
    """FRAC/INT Register"""
    R0 = kwargs.get("rampOn", False) << 31 | ((kwargs.get("muxoutCtl", 0x0) & 0xf) << 27) | ((kwargs.get("INT", 0x0000) & 0xfff) << 15) | ((kwargs.get("Fmsb", 0x0000) & 0xffff) << 3)
    return R0

def getR1(**kwargs):
    """LSB FRAC Register"""
    R1 = kwargs.get("phaseAdjust", False) << 28 | ((kwargs.get("Flsb", 0x00000) & 0x1ffff) << 15) | (kwargs.get("phaseValue", 0) & 0x0FFF) << 3 | 0x1 
    return R1

def getR2(**kwargs):
    """R Divider register"""
    ICP_2mA5 = 0x7
    R2 = kwargs.get("CSR_EN", False) << 28 | (kwargs.get("cpCurrent", ICP_2mA5) & 0xf) << 24 | kwargs.get("prescaler", True) << 22
    R2 |= kwargs.get("rDivide_2", True) << 21 | kwargs.get("referenceDoubler", False) << 20 | (kwargs.get("R_Counter", 1) & 0x1f) << 15
    R2 |= (kwargs.get("clk_1_div", 0) & 0xfff) << 3 | 0x2
    return R2

def getR3(**kwargs):
    """Function Register"""
    R3 = (kwargs.get("negBldCurrent", 0) & 0x7) << 22 | kwargs.get("NEG_BLEED_EN", False) << 21 | 0x1 << 17
    R3 |=  kwargs.get("LOL", False) << 16 | kwargs.get("nSel", False) << 15 | kwargs.get("sumDelRst", False) << 14
    R3 |= (kwargs.get("rampMode", SINGLE_SAW_TOOTH) & 0x3) << 10 | kwargs.get("PSK_EN", False) << 9 | kwargs.get("FSK_EN", False) << 8
    R3 |= kwargs.get("LPD", False) << 7 | kwargs.get("PD_Pol", True) << 6 | kwargs.get("PWR_DOWN", False) << 5
    R3 |= kwargs.get("cp3State", False) << 4 | kwargs.get("cntRst", False) << 3 | 0x3
    return R3

def getR4(**kwargs):
    """Clock Register"""
    R4 = kwargs.get("le_sel", False) << 31 | (kwargs.get("modMode", 0x00) & 0x1f) << 26 
    R4|= (kwargs.get("rampStatus", 0x00) & 0x1f) << 21 | (kwargs.get("clkDivMode", 0x0) & 0x3) << 19 
    R4|= (kwargs.get("clk2Div", 0x000) & 0xfff) << 7 | kwargs.get("clkDivSel", False) << 6 | 0x4
    return R4

def getR5(**kwargs):
    """Deviation Register"""
    R5 = kwargs.get("txDataInv", False) << 30 | kwargs.get("txDataRampClk", False) << 29 
    R5 |= kwargs.get("parabolicRamp", False) << 28 | (kwargs.get("interrupt", 0x0) & 0x3) << 26 
    R5 |= kwargs.get("fskRamp", False) << 25 | kwargs.get("dualRamp", False) << 24 
    R5 |= kwargs.get("devSel", False) << 23 | (kwargs.get("devOffset", 0x0) & 0xf) << 19 
    R5 |= (kwargs.get("deviation", 0x0000) & 0xffff) << 3 | 0x5
    return R5

def getR6(**kwargs):
    """Step Register"""
    R6 = kwargs.get("STEP_SEL", False) << 23 | (kwargs.get("STEP_WORD", 0x00000) & 0xfffff) << 3 | 0x6
    return R6

def getR7(**kwargs):
    """Delay Register"""
    R7 = kwargs.get("txDataTrigDel_EN", False) << 23 | kwargs.get("triangleDel", False) << 22 
    R7 |= kwargs.get("singFullTri", False) << 21 | kwargs.get("txDataTrig", False) << 20 
    R7 |= kwargs.get("fastRamp", False) << 19 | kwargs.get("rampDelayFl", False) << 18 
    R7 |= kwargs.get("rampDel", False) << 17 | kwargs.get("delClkSel", False) << 16 | kwargs.get("DEL_START_EN", False) << 15 
    R7 |= (kwargs.get("DELAY_WORD", 0x0000) & 0xfff) << 3 | 0x7
    return R7


def initPll(radar, radarFreqGHz: float, **kwargs):
    """return set of commands for initializing pll to single freq output"""
    # TODO add get default kwargs function to pass to registers
    kwargs.update(getIntFrac(radarFreqGHz))
    writeRadar(radar, *getAllRegs(**kwargs))
    return

def setFreq(radar, radarFreqGHz: float, **kwargs):
    """ update the int + frac values in registers 0 and 1, To be used to after initializing PLL with initPll()"""
    [N, Fmsb, Flsb, kwargs] = getIntFrac(radarFreqGHz)
    r0 = getR0(N, Fmsb, rampOn = False)
    r1 = getR1(Flsb, **kwargs)
    writeRadar(radar, *[r1, r0])

def getPllSweepKwargs(**kwargs):
    kwargs["STEP_WORD"] = int(kwargs["nFreqPoints"])
    kwargs["clkDivMode"] = 0x3
    # calculate dev offset
    Fpfd = getFpfd(**kwargs)
    Fres  = Fpfd/2**25
    Fdev = ((float(kwargs["stopFreqGHz"]) - float(kwargs["startFreqGHz"]))/((kwargs["refIn"]*1e-6/2/1000)*kwargs["extPrescale"]))/(int(kwargs["nFreqPoints"]) - 1)
    
    kwargs["devOffset"] = int(np.ceil(np.log2(Fdev * 2**25)) - 14)
    kwargs["deviation"] = int(Fdev * 2**25 * 2**-kwargs["devOffset"] )

    #calculate Clk_1 and set Clk_2 to 1
    kwargs["clk2Div"] = 1
    Clk_1 = int(float(kwargs["sweepTime_ms"])*1e-3/ int(kwargs["nFreqPoints"]) * Fpfd / kwargs["clk2Div"])
    kwargs["clk_1_div"] = Clk_1

    kwargs["DELAY_WORD"] = int(round(kwargs["rampDelay_us"]* 1e-6/( 1/Fpfd * Clk_1)))
    kwargs["DEL_START_EN"] = True
    kwargs["delClkSel"] = True
    kwargs["rampDel"] = True
    kwargs["txDatrigDel_EN"] = True
    kwargs["txDataTrig"] = True
    kwargs["rampOn"] = True
    return kwargs

def writePll(radar:ftd.FTD2XX, startFreqGHz:float = 220, stopFreqGHz:float = 269.5, nFreqPoints:int = 201, sweepTime_ms:float = 1, rampDelay_us:float = 10, refIn:float = 50e6, extPrescale:int = 72, **kwargs):
    """ generates and writes spi commands to program pll for sweep operation"""
    kwargs.update({"startFreqGHz":startFreqGHz,
                   "stopFreqGHz": stopFreqGHz,
                   "nFreqPoints": nFreqPoints,
                   "sweepTime_ms": sweepTime_ms,
                   "rampDelay_us": rampDelay_us,
                   "extPrescale":extPrescale,
                   "refIn": refIn})
    kwargs.update(getPllSweepKwargs(**kwargs))
    kwargs.update(getIntFrac(float(startFreqGHz)))
    writeRadar(radar,*getAllRegs(**kwargs))
    return

def getAllRegs(**kwargs):
    r0 = getR0(**kwargs)
    r1 = getR1(**kwargs)
    r2 = getR2(**kwargs)
    r3 = getR3(**kwargs)
    r4 = getR4(**kwargs)
    r5 = getR5(**kwargs)
    r6 = getR6(**kwargs)
    r7 = getR7(**kwargs)
    return [r7, r6, r5, r4, r3, r2, r1, r0]