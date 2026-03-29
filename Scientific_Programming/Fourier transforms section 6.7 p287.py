import numpy as np
import matplotlib.pyplot as plt

A1,A2 = 2,1
freq1, freq2 = 10,50
fsamp=500
t=np.arange(0,1,1/fsamp)
n=len(t)
f=A1*np.sin(2*np.pi*freq1*t)+A2*np.sin(2*np.pi*freq2*t)
f+=0.2*np.random.randn(n)  #add noise
plt.plot(t,f)
plt.title('Noisy signal')
plt.xlabel('Time (s)')
plt.ylabel('Amplitude')
plt.show()


# Compute Fourier transform
F = np.fft.fft(f)

# Compute frequencies corresponding to Fourier coefficients
freqs = np.fft.fftfreq(n, d=1/fsamp)

# Plot magnitude of Fourier coefficients
plt.figure(figsize=(10, 5))
plt.plot(freqs[:n//2], np.abs(F)[:n//2])
plt.title('Magnitude of Fourier coefficients')
plt.xlabel('Frequency (Hz)')
plt.ylabel('Magnitude')
plt.xlim(0, 100)
plt.grid()
plt.show()


