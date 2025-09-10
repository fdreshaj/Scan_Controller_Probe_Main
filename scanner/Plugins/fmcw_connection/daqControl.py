import nidaqmx
import nidaqmx.system
from nidaqmx.constants import (AcquisitionType, Edge, TriggerType, TerminalConfiguration)
from nidaqmx.stream_readers import AnalogMultiChannelReader
import numpy as np

def getDAQDeviceName(DAQ_SN:int):
    system = nidaqmx.system.System.local()
    devName = None
    for device in system.devices:
        system = nidaqmx.system.System.local()
        if device.dev_serial_num == DAQ_SN:
            devName = device.name 
            return device.name
    if devName is None: 
        raise(Exception(f"NI DAQ Not Found! Check if NI USB-6363 SN:{DAQ_SN} is connected"))


def readNIDaq(devName:str, sampleRate: int, samplesPerCh: int, trigSrc:str, *channels):
    """Reads DAQ with trigger"""
    multiChannelStr = ", ".join([devName + channel for channel in channels])

    with nidaqmx.Task() as read_task, nidaqmx.Task() as trigger_task:
        # setup trigger
        trigChan = devName + trigSrc
        trigger_task.do_channels.add_do_chan(trigChan)

        read_task.ai_channels.add_ai_voltage_chan(multiChannelStr, terminal_config=TerminalConfiguration.DIFF)
        read_task.timing.cfg_samp_clk_timing(rate = sampleRate,
            active_edge=Edge.RISING, sample_mode=AcquisitionType.FINITE, samps_per_chan= int(samplesPerCh))

        # setup read task
        read_task.triggers.start_trigger.trig_type = TriggerType.DIGITAL_EDGE
        read_task.triggers.start_trigger.dig_edge_edge = Edge.RISING
        read_task.triggers.start_trigger.retriggerable = False
        read_task.triggers.start_trigger.dig_edge_src = "/" + trigChan

        #setup data
        reader = AnalogMultiChannelReader(read_task.in_stream)

        # initialize empty np array
        data_array = np.zeros((len(channels) ,int(samplesPerCh)), dtype=np.float64)
        
        # read data
        read_task.start()
        trigger_task.write(True)
        reader.read_many_sample(data_array, number_of_samples_per_channel=int(samplesPerCh))
        read_task.stop()
        s11 = data_array[0, :] - 1j * data_array[1, :]
    return s11
