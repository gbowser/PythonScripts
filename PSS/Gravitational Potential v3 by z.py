import matplotlib.pyplot as plt
import numpy as np

# ---------- Milky Way-like potential model ----------
# Units:
# distance = kpc, mass = Msun, potential = (km/s)^2
G = 4.30091e-6  # kpc (km/s)^2 Msun^-1

# Disk (Miyamoto-Nagai)
M_d = 6.0e10
a_d = 6.5
b_d = 0.26

# Bulge (Hernquist)
M_b = 5.0e9
c_b = 0.7

# Halo (spherical logarithmic)
v_h = 180.0  # km/s
d_h = 12.0  # kpc


def phi_disk(R, z):
    return -G * M_d / np.sqrt(R**2 + (a_d + np.sqrt(z**2 + b_d**2)) ** 2)


def phi_bulge(r):
    return -G * M_b / (r + c_b)


def phi_halo(r):
    return 0.5 * v_h**2 * np.log(r**2 + d_h**2)


def phi_total(R, z):
    r = np.sqrt(R**2 + z**2)
    return phi_disk(R, z) + phi_bulge(r) + phi_halo(r)


# ---------- Radius grid and z slices ----------
R = np.linspace(0, 15, 500)  # kpc
z_levels = [0.00, 0.25, 0.50, 0.75, 1.00]  # kpc

# ---------- Plot all z levels on one 2D graph ----------
plt.figure(figsize=(9, 6))

for z in z_levels:
    phi = phi_total(R, z) / 1000.0  # thousands of (km/s)^2
    plt.plot(R, phi, linewidth=2, label=f"z = {z:.2f} kpc")

plt.xlabel("Radius R [kpc]")
plt.ylabel(r"Potential $\Phi(R, z)$ [$10^3\,(\mathrm{km}/\mathrm{s})^2$]")
plt.title("Milky Way Gravitational Potential vs Radius at Different Heights")
plt.grid(True, alpha=0.3)
plt.legend()
plt.tight_layout()
plt.show()
