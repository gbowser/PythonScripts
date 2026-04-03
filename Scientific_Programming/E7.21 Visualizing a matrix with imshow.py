import matplotlib.cm as cm
import matplotlib.pyplot as plt
import numpy as np

# Make an array with ones in the shape of an 'X'
a = np.eye(10, 10)
a += a[::-1, :]

fig, axes = plt.subplots(nrows=1, ncols=2)
ax1, ax2 = axes

# Bilinear interpolation - this will look blurry
ax1.imshow(a, interpolation="bilinear", cmap=cm.Greys_r)

# 'nearest' interpolation - faithful but blocky
ax2.imshow(a, interpolation="nearest", cmap=cm.Greys_r)

plt.show()
