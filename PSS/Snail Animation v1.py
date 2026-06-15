import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from pathlib import Path

# =========================================================
# Physical constants / handy conversions
# =========================================================
PC_PER_KPC = 1000.0
# 1 km/s = 1.022712 kpc/Gyr -> 1 pc/Gyr = 0.001022712 km/s
KM_S_PER_PC_PER_GYR = 0.001022712

# =========================================================
# Vertical frequency model Ωz(R) [Gyr^-1]
# =========================================================
R0   = 8.2      # kpc (Sun)
Rd   = 2.6      # kpc (disc scale length)
Omega0 = 70.0   # Gyr^-1 (disc contribution at R0)
Omega_halo = 30.0  # Gyr^-1 (rough halo floor)

def Omega_z_R(R):
    """Vertical angular frequency at radius R [Gyr^-1]."""
    Omega_disk = Omega0 * np.exp(-(R - R0) / (2.0 * Rd))
    return np.sqrt(Omega_disk**2 + Omega_halo**2)

# =========================================================
# Snail (z, vz) model with slight anharmonicity
# =========================================================
A0_pc = 400.0       # normalization for amplitude dependence
alpha = 0.12        # anharmonic coefficient (makes snail wind)
wraps = 4           # target wraps by t_end

def Omega_z_RA(R, A_pc):
    """Amplitude- and radius-dependent vertical frequency [Gyr^-1]."""
    return Omega_z_R(R) * (1.0 - alpha * (A_pc / A0_pc)**2)

def snail_points(t_Gyr, R=R0, n_points=800):
    """
    Generate (z [pc], vz [km/s]) points for the phase-space snail at time t_Gyr,
    sampling a range of vertical amplitudes A.
    """
    A_pc = np.linspace(50.0, 400.0, n_points)  # vertical amplitudes (pc)
    # phase increasing with amplitude -> differential winding (wraps by t_end=1 Gyr)
    # We normalize so the highest amplitude accumulates ~wraps * 2π by t=1 Gyr.
    # Use the amplitude-dependent frequency to set phase:
    OmegaA = Omega_z_RA(R, A_pc)  # Gyr^-1
    # rescale to hit 'wraps' turns at A_max relative to A_min:
    OA_min, OA_max = OmegaA.min(), OmegaA.max()
    # define an effective phase using the relative spread in frequency
    theta = 2*np.pi*wraps * t_Gyr * (OmegaA - OA_min) / max(OA_max - OA_min, 1e-9)

    z_pc  = A_pc * np.cos(theta)
    vz_kms = (A_pc * OmegaA) * KM_S_PER_PC_PER_GYR * (-np.sin(theta))  # vz amplitude = A*Ω; convert to km/s
    return z_pc, vz_kms

# =========================================================
# Right panel: vertical oscillations vs radius
# =========================================================
def z_of_R_t(R_kpc, t_Gyr, A_pc=200.0, phase=0.0, decay=0.0):
    """z(t) [pc] for a given radius, amplitude, phase; optional exponential decay."""
    Om = Omega_z_R(R_kpc)
    z = A_pc * np.sin(Om * t_Gyr + phase)
    if decay > 0:
        z *= np.exp(-decay * t_Gyr)
    return z

# =========================================================
# Animation parameters
# =========================================================
frames = 100       # 10 s at 10 fps
fps    = 10
t_end  = 1.0       # Gyr
t_vals = np.linspace(0.0, t_end, frames)

# Radii to show (right panel)
n_stars = 6
R_list = np.linspace(7.0, 9.0, n_stars)        # kpc
A_list = np.linspace(150.0, 300.0, n_stars)    # pc (different amplitudes)
phi_list = np.linspace(0.0, np.pi, n_stars)    # phases
decay = 0.0                                    # set >0 for light damping (e.g., 0.1)

# Precompute faint tracks over time for the right panel
time_track = np.linspace(0, t_end, 600)
tracks = []
for i in range(n_stars):
    z_track = z_of_R_t(R_list[i], time_track, A_pc=A_list[i], phase=phi_list[i], decay=decay)
    tracks.append(z_track)

# =========================================================
# Figure and axes
# =========================================================
fig, axes = plt.subplots(1, 3, figsize=(16, 5))
plt.subplots_adjust(wspace=0.35)
ax1, ax2, ax3 = axes

# Left: (z, vz)
snail_ln, = ax1.plot([], [], 'k-', lw=1.0)
ax1.set_xlim(-420, 420)          # pc
ax1.set_ylim(-30, 30)            # km/s, typical thin-disc vz amplitude
ax1.set_xlabel("z (pc)")
ax1.set_ylabel("v$_z$ (km s$^{-1}$)")
ax1.set_title("Phase-space snail (z, v$_z$)")

# Middle: (θz, Ωz) ideal linear relation + moving point
theta_line, = ax2.plot([], [], 'k-', lw=1.0)
pt, = ax2.plot([], [], 'ro', ms=6)
ax2.set_xlim(0, 2*np.pi)
# show Ωz around Solar value
Omega_center = Omega_z_R(R0)
ax2.set_ylim(Omega_center - 20, Omega_center + 20)  # ±20 Gyr^-1 window
ax2.set_xlabel(r"$\theta_z$ (radians)")
ax2.set_ylabel(r"$\Omega_z$ (Gyr$^{-1}$)")
ax2.set_title("Frequency–Angle (ideal linear relation)")
ax2.set_xticks([0, 0.5*np.pi, np.pi, 1.5*np.pi, 2*np.pi])
ax2.set_xticklabels(["0", "0.5π", "π", "1.5π", "2π"])

# Right: z vs R with faint tracks + moving dots
# Faint vertical guides at shown radii
for R in R_list:
    ax3.plot([R, R], [-420, 420], color='lightgray', lw=0.5, zorder=0)

colors = plt.cm.plasma(np.linspace(0, 1, n_stars))
# Faint tracks (time history) at each radius
for i, R in enumerate(R_list):
    ax3.plot(np.full_like(time_track, R), tracks[i], color='lightgray', lw=0.8, zorder=0)

pts = [ax3.plot([], [], marker='o', linestyle='None', color=colors[i], markersize=6, zorder=3)[0]
       for i in range(n_stars)]

ax3.set_xlim(R_list.min()-0.2, R_list.max()+0.2)
ax3.set_ylim(-420, 420)  # pc
ax3.set_xlabel("Galactocentric radius R (kpc)")
ax3.set_ylabel("z (pc)")
ax3.set_title("Vertical oscillations vs radius")

# Shared time label
time_text = fig.text(0.5, 0.05, '', ha='center', fontsize=12)

# =========================================================
# Animation init/update
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

    # Left panel: snail (use R0 for the sample)
    z_pc, vz_kms = snail_points(t, R=R0)
    snail_ln.set_data(z_pc, vz_kms)

    # Middle panel: ideal linear Ω–θ relation (slope ∝ t)
    theta = np.linspace(0, 2*np.pi, 600)
    # Line passes through (π, Ω_center) with slope increasing with time
    slope = 8.0 * t / (2*np.pi)   # choose scale so by t=1 Gyr it's clearly tilted
    Omega_line = Omega_center + slope * (theta - np.pi) * (2*np.pi)
    theta_line.set_data(theta, Omega_line)
    # Moving point runs from θ=0→2π over the interval
    theta_pt = 2*np.pi * (t % 1.0)
    Omega_pt = Omega_center + slope * (theta_pt - np.pi) * (2*np.pi)
    pt.set_data(theta_pt, Omega_pt)

    # Right panel: moving dots at fixed radii
    for i, p in enumerate(pts):
        z_now = z_of_R_t(R_list[i], t, A_pc=A_list[i], phase=phi_list[i], decay=decay)
        p.set_data(R_list[i], z_now)

    time_text.set_text(f"t = {t:.2f} Gyr")
    return [snail_ln, theta_line, pt, *pts, time_text]

ani = animation.FuncAnimation(fig, update, frames=frames, init_func=init, blit=True)

# Save (requires ffmpeg)
output_dir = Path(
    r"D:\Dropbox\Public Documents\UCLAN\B.Sc. DL Astronomy\AA3057 Collaborative Investigation\PSS Outputs\Animations"
)
output_dir.mkdir(parents=True, exist_ok=True)
output_file = output_dir / "Gaia_snail_threepanel_physical_units.mp4"
ani.save(output_file, writer="ffmpeg", fps=fps)
plt.close(fig)
print(f"Saved: {output_file}")
