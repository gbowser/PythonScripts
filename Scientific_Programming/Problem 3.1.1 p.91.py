# Basic plotting p.89
import matplotlib.pyplot as plt
import numpy as np

def normalised_gaussian(x, mu, sigma):
    return 1 / (sigma * np.sqrt(2 * np.pi)) * np.exp(-0.5 * ((x - mu) / sigma) ** 2)


n = 1000
xmin, xmax = -20.0, 20.0

x = np.linspace(xmin, xmax, n)
y = np.log(1/np.cos(x) ** 2)

plt.plot(x, y)
plt.show()

#normalised Gassian p.91

x = np.linspace(xmin, xmax, n)
y1=normalised_gaussian(x, 0, 1.0)
y2=normalised_gaussian(x, 0, 1.5)
y3=normalised_gaussian(x, 0, 2.0)
plt.plot(x, y1, label='sigma=1.0')
plt.plot(x, y2, label='sigma=1.5')
plt.plot(x, y3, label='sigma=2.0')
plt.legend(loc='upper left')
plt.show()


