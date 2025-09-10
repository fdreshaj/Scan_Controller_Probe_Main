from TRA_240_097 import TRA_240_097
import matplotlib. pyplot as plt
import numpy as np
import time
myRadar = TRA_240_097()

args = ['201', '220', '269.5', '1', '1e2']

kwargs = dict(zip(myRadar.get_parameters_list(), args))
myRadar.initialize(kwargs)
f = myRadar.get_frequency_vector_GHz(kwargs)

nSweeps = 10
data = []
for i in range(nSweeps):
    ts = time.time()
    data.append(myRadar.measure(kwargs))
    tstop = time.time()
    dt = tstop-ts
    # print(dt)
myRadar.close(kwargs)

sampleRate = int(round(1/( int(kwargs['sweepTime_ms'])*1e-3/int(kwargs['nFreqPoints']))))
Ts = 1/sampleRate
fig, ax = plt.subplots()

for ii in range(nSweeps):
    ax.plot(Ts*1000*np.arange(0, len(data[ii][:])),np.abs(data[ii][:]))
plt.title("{:d} sweeps -  nPoints {:d} - Trigger on Tx Data".format(nSweeps, len(data[ii][:])))  
plt.ylabel("Magnitude of I + j*Q")
plt.xlabel("time (ms) ")
plt.grid()
plt.show()