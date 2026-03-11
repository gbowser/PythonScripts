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


# ---------- Grid in Galactic plane ----------
x = np.linspace(-9, 9, 220)  # kpc
y = np.linspace(-9, 9, 220)  # kpc


X, Y = np.meshgrid(x, y)
R = np.sqrt(X**2 + Y**2)

# Height above the plane where we evaluate "vertical" potential
z_above = 1.0  # kpc

# Vertical potential relative to the midplane at same R
Phi_vert = phi_total(R, z_above) - phi_total(R, 0.0)  # (km/s)^2

# ---------- Plot ----------
fig = plt.figure(figsize=(10, 7))
ax = fig.add_subplot(111, projection="3d")
ax.set_xlim(-9, 9)
ax.set_ylim(-9, 9)

surf = ax.plot_surface(X, Y, Phi_vert, cmap="viridis", linewidth=0, antialiased=True)

ax.set_xlabel("x [kpc]")
ax.set_ylabel("y [kpc]")
ax.set_zlabel(r"$\Delta\Phi_z(R, z=1\,\mathrm{kpc})\;[(\mathrm{km}/\mathrm{s})^2]$")
ax.set_title("3D Map of Vertical Gravitational Potential Above the Milky Way")
fig.colorbar(surf, ax=ax, shrink=0.65, pad=0.1, label=r"$(\mathrm{km}/\mathrm{s})^2$")
plt.tight_layout()
plt.show()
