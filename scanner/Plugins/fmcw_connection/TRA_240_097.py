## labview interface class for sd-may40 radar board
import scanner.Plugins.fcwm_connection.radarControl as rc
import scanner.Plugins.fcwm_connection.daqControl as dc
import numpy as np
import nidaqmx.system
from nidaqmx.constants import (AcquisitionType, Edge, TriggerType)
from nidaqmx.stream_readers import AnalogMultiChannelReader

class TRA_240_097:
    """Class for TRA_240-097 based FMCW radar. 
    To be used with NI USB-6363 to trigger sweep and collect IFI and IFQ differential outputs. 
    Refer to README.md for setup instructions."""
    def __init__(self):
        self.dev = None
        #default radar parameters
        self.ftDevName = "TRA-240-097"
        self.MAX_FREQ_GHZ = 220
        self.MIN_FREQ_GHZ = 269.5
        self.sweeptime_ms = 1
        self.nFreq = 201

        # daq parameters
        self.daqSN = 31719907
        self.channels  = ["/ai2", "/ai3"]
        self.trigSrc = "/PFI8"
        self.sampleRate = 1e6
        self.daqMaxSampleRate = 2e6
        return
    
    def initialize(self, kwargs):
        self.dev = rc.getFTDevByDesc("TRA-240-097")
        rc.initFtdiSPI(self.dev)
        rc.setGPIOH(self.dev, 0x3D)
        print(kwargs)
        if kwargs:
            self.sampleRate = int(round(1/(int(kwargs['sweepTime_ms'])*1e-3/int(kwargs['nFreqPoints']))))
            if(self.sampleRate > self.daqMaxSampleRate):
                raise ValueError(f"Requested Sample Rate {self.sampleRate} is too high")
            self.fVec = rc.writePll(self.dev, **kwargs)
        else:
            rc.initPll(self.dev, radarFreqGHz=self.MAX_FREQ_GHZ)
        self.daqName = dc.getDAQDeviceName(self.daqSN)
        return

    def measure(self, kwargs):
        data = []
        nAvgs = 1
        for i in range(nAvgs):
            data.append(dc.readNIDaq(self.daqName, self.sampleRate, int(kwargs['nFreqPoints']), self.trigSrc, *self.channels))
        data = np.mean(data, 0)
        return data

    def close(self, kwargs):
        self.dev.close()
        return

    def get_frequency_vector_GHz(self, kwargs):
        '''Return array of frequencies that will measured (GHz)'''
        f = np.linspace(float(kwargs["startFreqGHz"]), float(kwargs["stopFreqGHz"]), int(kwargs["nFreqPoints"]))
        return f.tolist()

    def get_channel_names(self, kwargs):
        '''Return list of strings for the channel names. Can be left blank'''
        channels = ["ch1"] 
        return channels
    
    @staticmethod
    def get_parameters_list():
        '''Define the parameters that will be used in your program'''
        return ["nFreqPoints","startFreqGHz", "stopFreqGHz", 'sweepTime_ms']
    

    
