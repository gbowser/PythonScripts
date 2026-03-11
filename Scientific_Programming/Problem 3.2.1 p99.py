import matplotlib.pyplot as plt
import numpy as np

# Constants
k1 = 300.0          # s^-1
k2 = 100.0          # s^-1
A0 = 2.0            # mol dm^-3

# Time array
t = np.linspace(0, 0.02, 1000)   # seconds

# Concentration equations
A = A0 * np.exp(-(k1 + k2) * t)
B = (k1 / (k1 + k2)) * A0 * (1 - np.exp(-(k1 + k2) * t))
C = (k2 / (k1 + k2)) * A0 * (1 - np.exp(-(k1 + k2) * t))

# Plot
plt.figure(figsize=(8, 5))
plt.plot(t, A, label='[A]', linewidth=2)
plt.plot(t, B, label='[B]', linewidth=2)
plt.plot(t, C, label='[C]', linewidth=2)

plt.xlabel('Time / s', fontsize=12)
plt.ylabel(r'Concentration / mol dm$^{-3}$', fontsize=12)
plt.title('Concentrations of A, B and C vs Time')
plt.legend()
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.show()
