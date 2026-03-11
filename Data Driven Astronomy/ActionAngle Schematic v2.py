import numpy as np
import matplotlib.pyplot as plt

# ----------------------------
# Simple 2-panel action–angle schematic
# ----------------------------

# Parameters (schematic, not physically exact)
Rg = 8.0          # guiding radius (arbitrary units)
dR = 1.2          # radial epicycle amplitude
kappa_over_Omega = 1.7  # choose a ratio to make a rosette-like curve
n = 2000

t = np.linspace(0, 12*np.pi, n)

# "Epicyclic-ish" orbit about guiding centre (schematic)
# Guiding centre moves in azimuth at Omega; radius oscillates at kappa
Omega = 1.0
kappa = kappa_over_Omega * Omega

R = Rg + dR*np.cos(kappa * t)
phi = Omega * t + 0.15*np.sin(kappa * t)  # small phase modulation for visual interest

x = R * np.cos(phi)
y = R * np.sin(phi)

# Circle for guiding radius
phi_c = np.linspace(0, 2*np.pi, 400)
xg = Rg * np.cos(phi_c)
yg = Rg * np.sin(phi_c)

# Choose a point on the orbit to annotate ΔR
idx = int(0.18 * n)
x0, y0 = x[idx], y[idx]
R0 = np.sqrt(x0**2 + y0**2)
phi0 = np.arctan2(y0, x0)

# Point on guiding circle at same azimuth
xR = Rg * np.cos(phi0)
yR = Rg * np.sin(phi0)

# ----------------------------
# Right panel: angle clock for theta_z
# ----------------------------
theta_z = np.deg2rad(110)  # example phase angle

# ----------------------------
# Plot
# ----------------------------
fig, axs = plt.subplots(1, 2, figsize=(11, 5))
fig.suptitle("Action–angle schematic: orbit label (actions) + phase (angles)", fontsize=19.6)

# ---- Left: Orbit and guiding radius
ax = axs[0]
ax.set_aspect("equal", "box")
ax.plot(xg, yg, lw=1.5, label="Guiding circle ($R_g$)")
ax.plot(x, y, lw=1.2, label="Star orbit (schematic)")

# Guiding centre marker at (Rg, 0)
ax.scatter([Rg], [0], s=40, zorder=5)
ax.annotate("Guiding centre", xy=(Rg, 0), xytext=(Rg+0.6, -0.8),
            arrowprops=dict(arrowstyle="->", lw=1), fontsize=10)

# Rg arrow along x-axis
ax.annotate("", xy=(Rg, 0), xytext=(0, 0),
            arrowprops=dict(arrowstyle="<->", lw=1.2))
ax.text(Rg/2, 0.25, r"$R_g$", ha="center", fontsize=12)

# ΔR arrow at a chosen azimuth
ax.scatter([x0], [y0], s=30, zorder=6)
ax.annotate("", xy=(x0, y0), xytext=(xR, yR),
            arrowprops=dict(arrowstyle="<->", lw=1.2))
ax.text((x0+xR)/2, (y0+yR)/2, r"$\Delta R \sim$ epicycle size", fontsize=10,
        ha="left", va="bottom", rotation=np.rad2deg(phi0))

ax.set_title("Orbit in the disc plane", fontsize=16.8)
ax.set_xlabel("x")
ax.set_ylabel("y")
ax.legend(loc="lower left", fontsize=9)
ax.set_xlim(-10.5, 10.5)
ax.set_ylim(-10.5, 10.5)
ax.grid(True, alpha=0.3)

# ---- Right: theta_z phase clock
ax = axs[1]
ax.set_aspect("equal", "box")

# Unit circle
ax.plot(np.cos(phi_c), np.sin(phi_c), lw=1.5)
ax.scatter([0], [0], s=30)

# Reference axis and arrow
ax.plot([0, 1], [0, 0], lw=1.0)
ax.text(1.05, 0.0, r"$\theta_z=0$", va="center", fontsize=10)

# Theta_z arrow
ax.annotate("", xy=(np.cos(theta_z), np.sin(theta_z)), xytext=(0, 0),
            arrowprops=dict(arrowstyle="->", lw=2.0))
ax.text(0.55*np.cos(theta_z), 0.55*np.sin(theta_z),
        r"$\theta_z$", fontsize=13, ha="center", va="center")

# Arc showing theta_z
arc = np.linspace(0, theta_z, 150)
ax.plot(0.25*np.cos(arc), 0.25*np.sin(arc), lw=2.0)

ax.set_title(r"Vertical phase as an angle: $\theta_z$", fontsize=16.8)
ax.set_xticks([])
ax.set_yticks([])
ax.set_xlim(-1.25, 1.25)
ax.set_ylim(-1.25, 1.25)
ax.grid(False)

plt.tight_layout()
plt.show()
