import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from pathlib import Path

# =========================================================
# Physical constants
# =========================================================
PC_PER_KPC = 1000.0
KM_S_PER_PC_PER_GYR = 0.001022712   # 1 pc/Gyr = 0.001022712 km/s

# =========================================================
# Vertical frequency model Ωz(R) [Gyr^-1]
# =========================================================
R0 = 8.2       # kpc (Sun)
Rd = 2.6       # kpc (disc scale length)
Omega0 = 70.0  # Gyr^-1 (disc contribution at R0)
Omega_halo = 30.0  # Gyr^-1 (halo contribution)

def Omega_z_R(R):
    """Vertical angular frequency at radius R [Gyr^-1]."""
    Omega_disk = Omega0 * np.exp(-(R - R0) / (2.0 * Rd))
    return np.sqrt(Omega_disk**2 + Omega_halo**2)

# =========================================================
# Snail (z, vz) model with anharmonicity
# =========================================================
A0_pc = 400.0
alpha = 0.12
wraps = 4

def Omega_z_RA(R, A_pc):
    """Amplitude- and radius-dependent vertical frequency [Gyr^-1]."""
    return Omega_z_R(R) * (1.0 - alpha * (A_pc / A0_pc)**2)

def snail_points(t_Gyr, R=R0, n_points=800):
    """Generate (z [pc], vz [km/s]) for the phase-space snail at time t_Gyr."""
    A_pc = np.linspace(50.0, 400.0, n_points)
    OmegaA = Omega_z_RA(R, A_pc)
    OA_min, OA_max = OmegaA.min(), OmegaA.max()
    theta = 2*np.pi*wraps * t_Gyr * (OmegaA - OA_min) / max(OA_max - OA_min, 1e-9)
    z_pc = A_pc * np.cos(theta)
    vz_kms = (A_pc * OmegaA) * KM_S_PER_PC_PER_GYR * (-np.sin(theta))
    return z_pc, vz_kms

# =========================================================
# Vertical oscillations vs radius
# =========================================================
def z_of_R_t(R_kpc, t_Gyr, A_pc=200.0, phase=0.0, decay=0.0):
    Om = Omega_z_R(R_kpc)
    z = A_pc * np.sin(Om * t_Gyr + phase)
    if decay > 0:
        z *= np.exp(-decay * t_Gyr)
    return z

# =========================================================
# Animation parameters
# =========================================================
frames = 100
fps = 10
t_end = 1.0
t_vals = np.linspace(0.0, t_end, frames)

n_stars = 6
R_list = np.linspace(7.0, 9.0, n_stars)
A_list = np.linspace(150.0, 300.0, n_stars)
phi_list = np.linspace(0.0, np.pi, n_stars)
decay = 0.0

# Precompute faint tracks
time_track = np.linspace(0, t_end, 600)
tracks = [z_of_R_t(R_list[i], time_track, A_pc=A_list[i], phase=phi_list[i], decay=decay)
           for i in range(n_stars)]

# =========================================================
# Figure setup
# =========================================================
fig, axes = plt.subplots(1, 3, figsize=(16, 5))
plt.subplots_adjust(wspace=0.35)
ax1, ax2, ax3 = axes

# Left: (z, vz)
snail_ln, = ax1.plot([], [], 'k-', lw=1.0)
ax1.set_xlim(-420, 420)
ax1.set_ylim(-30, 30)
ax1.set_xlabel("z (pc)")
ax1.set_ylabel("v$_z$ (km s$^{-1}$)")
ax1.set_title("Phase-space snail (z, v$_z$)")
ax1.grid(True, linestyle='--', alpha=0.6)

# Middle: (θz, Ωz)
theta_line, = ax2.plot([], [], 'k-', lw=1.0)
pt, = ax2.plot([], [], 'ro', ms=6)
ax2.set_xlim(0, 2*np.pi)
Omega_center = Omega_z_R(R0)
ax2.set_ylim(Omega_center - 20, Omega_center + 20)
ax2.set_xlabel(r"$\theta_z$ (radians)")
ax2.set_ylabel(r"$\Omega_z$ (Gyr$^{-1}$)")
ax2.set_title("Frequency–Angle (θ_z, Ω_z)")
ax2.set_xticks([0, 0.5*np.pi, np.pi, 1.5*np.pi, 2*np.pi])
ax2.set_xticklabels(["0", "0.5π", "π", "1.5π", "2π"])
ax2.grid(True, linestyle='--', alpha=0.6)

# Right: z vs R (vertical oscillations)
for R in R_list:
    ax3.plot([R, R], [-420, 420], color='lightgray', lw=0.5, zorder=0)

colors = plt.cm.plasma(np.linspace(0, 1, n_stars))
for i, R in enumerate(R_list):
    ax3.plot(np.full_like(time_track, R), tracks[i], color='lightgray', lw=0.8, zorder=0)

pts = [ax3.plot([], [], marker='o', linestyle='None', color=colors[i],
                markersize=6, zorder=3)[0] for i in range(n_stars)]

ax3.set_xlim(R_list.min()-0.2, R_list.max()+0.2)
ax3.set_ylim(-420, 420)
ax3.set_xlabel("Galactocentric radius R (kpc)")
ax3.set_ylabel("z (pc)")
ax3.set_title("Vertical oscillations vs radius")
ax3.grid(True, linestyle='--', alpha=0.6)

time_text = fig.text(0.5, 0.05, '', ha='center', fontsize=12)

# =========================================================
# Animation functions
# =========================================================
def init():
    snail_ln.set_data([], [])
    theta_line.set_data([], [])
    pt.set_data([], [])
    for p in pts:
        p.set_data([], [])
    time_text.set_text('')
    return [snail_ln, theta_line, pt, *pts, time_text]

def update(frame):
    t = t_vals[frame]
    # Left: snail
    z_pc, vz_kms = snail_points(t, R=R0)
    snail_ln.set_data(z_pc, vz_kms)

    # Middle: linear Ω–θ relation
    theta = np.linspace(0, 2*np.pi, 600)
    slope = 8.0 * t / (2*np.pi)
    Omega_line = Omega_center + slope * (theta - np.pi) * (2*np.pi)
    theta_line.set_data(theta, Omega_line)
    theta_pt = 2*np.pi * (t % 1.0)
    Omega_pt = Omega_center + slope * (theta_pt - np.pi) * (2*np.pi)
    pt.set_data(theta_pt, Omega_pt)

    # Right: oscillating stars
    for i, p in enumerate(pts):
        z_now = z_of_R_t(R_list[i], t, A_pc=A_list[i], phase=phi_list[i], decay=decay)
        p.set_data(R_list[i], z_now)

    time_text.set_text(f"t = {t:.2f} Gyr")
    return [snail_ln, theta_line, pt, *pts, time_text]

ani = animation.FuncAnimation(fig, update, frames=frames, init_func=init, blit=True)

# =========================================================
# Save as GIF using Pillow
# =========================================================
output_dir = Path(
    r"D:\Dropbox\Public Documents\UCLAN\B.Sc. DL Astronomy\AA3057 Collaborative Investigation\PSS Outputs\Animations"
)
output_dir.mkdir(parents=True, exist_ok=True)
output_file = output_dir / "Gaia_snail_threepanel_physical_units_grids.gif"
ani.save(output_file, writer="pillow", fps=fps)
plt.close(fig)
print(f"Saved: {output_file}")
