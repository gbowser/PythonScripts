import numpy as np
import matplotlib.pyplot as plt

# -----------------------------
# Physical constants (cgs units)
# -----------------------------
k_B  = 1.380649e-16      # Boltzmann constant [erg K^-1]
h    = 6.62607015e-27    # Planck constant [erg s]

# -----------------------------
# Plasma parameters
# -----------------------------
T = 1.0e8  # temperature [K]

# Frequency grid (Hz)
nu = np.logspace(16, 20, 500)

# -----------------------------
# Optically thin thermal bremsstrahlung emissivity
# WITHOUT Gaunt factor:
# j_nu ∝ exp(-h nu / kT)
# -----------------------------
j_nu = np.exp(-h * nu / (k_B * T))

# Characteristic frequency where h nu = kT
nu_T = k_B * T / h

# -----------------------------
# Plot
# -----------------------------
plt.figure(figsize=(7, 5))
plt.loglog(nu, j_nu)

plt.xlabel("Frequency ν (Hz)")
plt.ylabel("Bremsstrahlung emissivity jν (arb. units)")
plt.title("Optically Thin Thermal Bremsstrahlung at T = 10⁸ K\n(no Gaunt factor)")

# Mark ν where hν = kT
plt.axvline(nu_T, linestyle="--")
plt.text(nu_T * 1.1, j_nu[nu > nu_T][0], "hν = kT", rotation=90, va="bottom")

plt.grid(True, which="both")
plt.tight_layout()
plt.show()
