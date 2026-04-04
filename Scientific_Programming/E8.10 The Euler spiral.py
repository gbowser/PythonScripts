import matplotlib.pyplot as plt
import numpy as np
from scipy.special import fresnel

t = np.linspace(-10, 10, 1000)
plt.plot(*fresnel(t), c="k")
plt.show()
