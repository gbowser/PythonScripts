import numpy as np
import matplotlib.pyplot as plt

# -----------------------------
# Physical constants (cgs units)
# -----------------------------
k_B  = 1.380649e-16      # Boltzmann constant [erg K^-1]
h    = 6.62607015e-27    # Planck constant [erg s]
m_e  = 9.10938356e-28    # electron mass [g]
e_cgs = 4.80320427e-10   # electron charge [esu]

# -----------------------------
# Plasma parameters
# -----------------------------
T = 1.0e8  # temperature [K]

# Frequency grid (Hz)
nu = np.logspace(16, 20, 500)

# -----------------------------
# Gaunt factor (Rybicki & Lightman–style approximation)
# g_ff ~ (sqrt(3)/pi) * ln[ ( (2kT)^(3/2) ) / (pi e^2 m_e^(1/2) nu ) ]
# -----------------------------
def gaunt_ff(nu, T):
    argument = ( (2.0 * k_B * T)**1.5 ) / (np.pi * e_cgs**2 * np.sqrt(m_e) * nu)
    return np.sqrt(3.0) / np.pi * np.log(argument)

g_ff = gaunt_ff(nu, T)

# -----------------------------
# Optically thin thermal bremsstrahlung emissivity (up to a constant factor)
# j_nu ∝ g_ff * exp(-h nu / kT)
# -----------------------------
j_nu = g_ff * np.exp(-h * nu / (k_B * T))

# Characteristic frequency where h nu = kT
nu_T = k_B * T / h

# -----------------------------
# Plot
# -----------------------------
plt.figure(figsize=(7, 5))
plt.loglog(nu, j_nu)

plt.xlabel("Frequency ν (Hz)")
plt.ylabel("Bremsstrahlung emissivity jν (arb. units)")
plt.title("Optically Thin Thermal Bremsstrahlung at T = 10⁸ K\nwith Free–Free Gaunt Factor")

# Mark ν where hν = kT (rough location of exponential cutoff scale)
plt.axvline(nu_T, linestyle="--")
plt.text(nu_T * 1.1, j_nu[nu > nu_T][0], "hν = kT", rotation=90, va="bottom")

plt.grid(True, which="both")
plt.tight_layout()
plt.show()
