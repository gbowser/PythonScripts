import numpy as np
import matplotlib.pyplot as plt

# Code produces Figure 3.5

# Time array (seconds)
t = np.linspace(0.0, 0.1, 1000)

# Peak voltages
vp_uk = 230 * np.sqrt(2)
vp_us = 120 * np.sqrt(2)

# Frequencies (Hz)
f_uk = 50
f_us = 60

# AC voltage equations
v_uk = vp_uk * np.sin(2 * np.pi * f_uk * t)
v_us = vp_us * np.sin(2 * np.pi * f_us * t)

# Plot the voltages
plt.plot(t * 1000, v_uk, label='UK')
plt.plot(t * 1000, v_us, label='US')

plt.title('A comparison of AC voltages in the UK and US')
plt.xlabel('Time / ms', fontsize=16)
plt.ylabel('Voltage / V', fontsize=16)
plt.legend()

plt.show()