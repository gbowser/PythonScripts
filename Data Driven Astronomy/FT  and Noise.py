#  https://github.com/ska-sa/ARIWS-Cookbook/blob/main/0-Introduction/

import matplotlib.pylab as plt
import numpy as np

counter = 0
frequencies = []
while 1:
    freq = np.random.randn(1)[0]
    if freq > 0 and freq < 0.5:
        frequencies.append(freq)
        counter += 1
    if counter > 8:
        break


def generate_signal(freq, time):
    return np.sin(2 * np.pi * freq * time)


# simulated time series
t = np.arange(1, 250)
s = np.zeros(np.size(t))
plt.figure()
plt.clf()
for freq in frequencies:
    time_series = generate_signal(freq, t)
    s = s + time_series
    plt.subplot(2, 1, 1)
    plt.plot(t, time_series)
    plt.ylabel("Individual signals")
    plt.subplot(2, 1, 2)
    plt.plot(t, s)
    plt.ylabel("Combined signals")
plt.show()


def ft(y):
    return np.fft.fftshift(np.fft.fft(np.fft.fftshift(y)))


def ftfreqs(N, dt):
    return np.fft.fftshift(np.fft.fftfreq(N, dt))


t = np.arange(1, 2500)
delta_t = 1.0

# generate a low amplitude low frequency sinusoidal wave (amplitude = 0.17)
signal = 0.17 * np.sin(2 * np.pi * 0.4 * t)

# remove DC spike
y = signal - np.mean(signal)
Y = ft(y)  # Fourier transform
freqs = ftfreqs(len(y), delta_t)
plt.figure()
plt.clf()
plt.subplot(2, 1, 1)
plt.plot(t[:100], y[:100])
plt.xlabel("Time")
plt.ylabel("Amplitude")
plt.title("y(t)")
plt.subplot(2, 1, 2)
plt.plot(freqs, np.abs(Y), "o-")
plt.xlabel("Frequency")
plt.ylabel("Amplitude")
plt.title("Y(f)")
plt.show()


# generate a white noise signal with amplitude = 1
noise = np.random.rand(np.size(t))

# remove DC spike
z = noise - np.mean(noise)
Z = ft(z)  # Fourier transform
freqs = ftfreqs(len(z), delta_t)
plt.figure()
plt.clf()
plt.subplot(2, 1, 1)
plt.plot(t, z)
plt.xlabel("Time")
plt.ylabel("Amplitude")
plt.title("z(t)")
plt.subplot(2, 1, 2)
plt.plot(freqs, np.abs(Z), "o-")
plt.xlabel("Frequency")
plt.ylabel("Amplitude")
plt.title("Z(f)")
plt.show()


# remove DC spike
y = (signal + noise) - np.mean(signal + noise)
Y = ft(y)  # Fourier transform
freqs = ftfreqs(len(y), delta_t)
plt.figure()
plt.clf()
plt.subplot(2, 1, 1)
plt.plot(t, y)
plt.xlabel("Time")
plt.ylabel("Amplitude")
plt.title("y(t)")
plt.subplot(2, 1, 2)
plt.plot(freqs, np.abs(Y), "o-")
plt.xlabel("Frequency")
plt.ylabel("Amplitude")
plt.title("Y(f)")
plt.show()
