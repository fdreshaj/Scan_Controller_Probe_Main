import radarControl
import daqControl
from matplotlib import pyplot as plt
import matplotlib.animation as animation
import numpy as np

dev = radarControl.openFTDevByDesc_sn(descriptor="TRA-240-097", sn=2)
radarControl.initFtdiSPI(dev)
radarControl.setGPIOH(dev, 0x3D)
startF = 220
stopF = 269.5
sweeptime_ms = 4
rampDelay_us = 10
nFreq = 501
radarControl.writePll(dev, startF, stopF, nFreq, sweeptime_ms, rampDelay_us, muxoutCtl = 0xf, rampStatus = 0x3)
DAQ_SN = 31719907
daqName = daqControl.getDAQDeviceName(DAQ_SN)
channels  = ["/ai2", "/ai3"]

sampleRate = int(round(1/(sweeptime_ms * 1e-3/nFreq)))
data = daqControl.readNIDaq(daqName, sampleRate, nFreq,"/PFI8", *channels)
t = np.arange(start=0, stop=nFreq, step=1) / sampleRate

# plot IF time domain signal
plt.plot(t , np.abs(data))
plt.show()

# plot freq spectrum to show the beat freq
BW = (stopF-startF) * 1e9
df_min = 1/(sweeptime_ms * 1e-3)
K = BW/(sweeptime_ms*1e-3)
Rmax = 3e8*sampleRate/(2*K)
dR = 3e8/(2*BW)

print(f'sweep time : {sweeptime_ms}[ms]')
print(f'Sweep Slope : {K*1e-6}[MHz/s]')
print(f'ADC sample rate [Sa/s] {sampleRate}')
print(f'max range : {Rmax}[m]') # limited by IF filter cut-off frequency (100MHz) and the ADC sampling rate
print(f'Range Res : {dR}[m]')
print(f'dF Min : {df_min}[Hz]')

Fs = sampleRate
f = Fs/nFreq*np.arange(0, nFreq)
d = 3e8*f/(2*K)

## animate the plots
fig, (ax0, ax1) = plt.subplots(nrows=2)
data = daqControl.readNIDaq(daqName, sampleRate, nFreq,"/PFI8", *channels)
Y = 10 * np.log10(abs(np.fft.fft(data,  n = len(data) * 2)))
yData = Y * np.hanning(len(Y))
line0, = ax0.plot(d, yData[:len(yData)//2])
ax0.set(xlabel='distance [m]', ylabel='|FFT(S)| dB')
tDist = d[np.argmax(yData[:len(yData)//2])]
annotation = ax0.annotate(f'{tDist:.4f}', xy=(tDist, yData[np.argmax(yData)]), xycoords='data',
            xytext=(1.5, -20.5), textcoords='offset points')
line1, line2 = ax1.plot(t, np.real(data), t, np.imag(data))

def animate(i):
    data = daqControl.readNIDaq(daqName, sampleRate, nFreq,"/PFI8", *channels)
    Y = 10 * np.log10(abs(np.fft.fft(data, n = len(data) * 2)))
    yData = Y * np.hanning(len(Y))
    line0.set_ydata(yData[:len(yData)//2])
    tDist = d[np.argmax(yData[:len(yData)//2])]
    annotation.set_text(f'{tDist:.4f}')
    annotation.set_position((tDist, yData[np.argmax(yData)]-30))
    ax1.clear()
    line1, line2 = ax1.plot(t, np.real(data), t, np.imag(data))
    
    return line0,line1, line2, annotation 

ani = animation.FuncAnimation(
    fig, animate, interval=20, blit=True, save_count=50)

plt.show()