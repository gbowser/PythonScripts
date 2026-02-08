"""
Milky Way toy model animation (single tilted 3D view) with smooth epicycle turn-on and 3s dotted trails

Updates requested:
- N_STARS = 8
- Make stars perform more radial (epicyclic) oscillations per one azimuthal orbit:
    Set kappa/Omega = RADIAL_OSC_PER_AZ_ORBIT  (so "number of radial cycles per azimuthal cycle" increases)

Requires: numpy, matplotlib
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401

# -----------------------------
# Controls
# -----------------------------
SEED = 7
N_STARS = 8  # CHANGED

V0 = 1.0
RMIN, RMAX = 6.0, 10.0

# NEW: radial oscillations per azimuthal orbit
# One azimuthal orbit has period Tphi = 2π/Omega.
# One radial oscillation has period TR = 2π/kappa.
# So number of radial oscillations per azimuthal orbit = kappa/Omega.
RADIAL_OSC_PER_AZ_ORBIT = 4.0  # CHANGED: increase this for "more radial orbits"

# Epicycles: absolute radial amplitude distribution ("kpc-like" units)
A_R_MEAN = 1.0
A_R_STD = 0.3
A_R_MIN = 0.05
EPICYCLE_FADEIN_S = 1.0  # smooth turn-on duration (seconds)

# Vertical oscillations
ZAMP_MEAN = 0.35
ZAMP_SIG = 0.15
ZAMP_MIN = 0.05
VERT_SCALE = 0.25
NU0 = 3.2
ALPHA = 1.8
VZ_KICK = 1.0

# Timing
FPS = 30
DT = 1 / FPS
T_STAGE1 = 6.0
STAGE2_DURATION = 10.0
T_STAGE2 = T_STAGE1 + STAGE2_DURATION
T_TOTAL = T_STAGE2 + 10.0

# View
VIEW_ELEV_DEG = 30
VIEW_AZIM_DEG = 35

# Trails
TRAIL_SECONDS = 3.0
TRAIL_LEN = int(TRAIL_SECONDS * FPS)

SAVE_MP4 = False
MP4_NAME = "mw_tilted_3d_trails_smooth.mp4"


# -----------------------------
# Helpers
# -----------------------------
def omega_flat(R):
    return V0 / R

def nu_anharm(A):
    return NU0 / (1.0 + ALPHA * A * A)

def smoothstep01(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3 - 2 * x)


# -----------------------------
# Initial conditions
# -----------------------------
rng = np.random.default_rng(SEED)

Rg = rng.uniform(RMIN, RMAX, N_STARS)

# Evenly spaced angles around the centre
phi0 = np.linspace(0, 2 * np.pi, N_STARS, endpoint=False)

Omega = omega_flat(Rg)

# CHANGED: choose kappa so there are more radial oscillations per azimuthal orbit
kappa = RADIAL_OSC_PER_AZ_ORBIT * Omega

# Epicycle amplitudes in absolute units
aR = rng.normal(A_R_MEAN, A_R_STD, N_STARS)
aR = np.clip(aR, A_R_MIN, None)

# Re-phase epicycle so radial offset is zero at Stage 2 start (no sudden jump)
psi_at_start = rng.choice([0.5 * np.pi, 1.5 * np.pi], size=N_STARS)  # ensures cos(...) = 0
psi0 = psi_at_start - kappa * T_STAGE1

# Vertical amplitudes and phases
A = np.clip(rng.normal(ZAMP_MEAN, ZAMP_SIG, N_STARS), ZAMP_MIN, 0.9)
A *= VERT_SCALE
nu = nu_anharm(A)
theta0 = rng.uniform(0, 2 * np.pi, N_STARS)

kick_sign = rng.choice([-1.0, 1.0], size=N_STARS, p=[0.5, 0.5])


# -----------------------------
# State evolution
# -----------------------------
def positions(t, stage):
    # Guiding-centre
    phi_g = phi0 + Omega * t
    xg = Rg * np.cos(phi_g)
    yg = Rg * np.sin(phi_g)

    if stage == 1:
        return xg, yg, np.zeros_like(Rg)

    # Smoothly ramp epicycle amplitude from 0 at stage2 start
    tau2 = max(0.0, t - T_STAGE1)
    ramp2 = smoothstep01(tau2 / EPICYCLE_FADEIN_S)

    phase = kappa * t + psi0

    # Epicycle offsets
    dR = ramp2 * aR * np.cos(phase)

    # Keep a visually similar tangential coupling but scale with (Omega/kappa):
    # Larger kappa => smaller angular offset for same aR (reasonable for a tighter epicycle).
    dphi = ramp2 * (2.0 * Omega / kappa) * (aR / Rg) * np.sin(phase)

    R = Rg + dR
    phi = phi_g + dphi

    x = R * np.cos(phi)
    y = R * np.sin(phi)

    if stage == 2:
        return x, y, np.zeros_like(Rg)

    # Vertical turns on at stage3 start
    t3 = max(0.0, t - T_STAGE2)
    vert_phase = nu * t3 + theta0
    z = A * np.cos(vert_phase)

    ramp3 = 1.0 - np.exp(-t3 / 0.3)
    z = z + 0.08 * ramp3 * (VZ_KICK * kick_sign) * np.sin(vert_phase)

    return x, y, z


# -----------------------------
# Figure
# -----------------------------
plt.rcParams["figure.dpi"] = 120
fig = plt.figure(figsize=(9.5, 7.0))
ax = fig.add_subplot(111, projection="3d")
ax.view_init(elev=VIEW_ELEV_DEG, azim=VIEW_AZIM_DEG)

lim_xy = RMAX + 2.5
z_lim = max(0.5, float(np.max(A) * 2.5))

ax.set_xlim(-lim_xy, lim_xy)
ax.set_ylim(-lim_xy, lim_xy)
ax.set_zlim(-z_lim, z_lim)

ax.set_xlabel("x (toy kpc)")
ax.set_ylabel("y (toy kpc)")
ax.set_zlabel("z (toy kpc)")
ax.set_title("Tilted Milky Way toy orbits (more radial oscillations per azimuthal orbit)")

# Guide rings
rings = np.linspace(RMIN, RMAX, 5)
th = np.linspace(0, 2 * np.pi, 400)
for rr in rings:
    ax.plot(rr * np.cos(th), rr * np.sin(th), np.zeros_like(th), lw=0.7, alpha=0.25)

# Stars + trails
sc = ax.scatter([], [], [], s=75, alpha=0.95)

trail_lines = []
for _ in range(N_STARS):
    (ln,) = ax.plot([], [], [], linestyle=":", linewidth=1.2, alpha=0.85)
    trail_lines.append(ln)

time_text = ax.text2D(0.02, 0.95, "", transform=ax.transAxes)
stage_text = ax.text2D(0.02, 0.90, "", transform=ax.transAxes)

trail_x = np.full((N_STARS, TRAIL_LEN), np.nan)
trail_y = np.full((N_STARS, TRAIL_LEN), np.nan)
trail_z = np.full((N_STARS, TRAIL_LEN), np.nan)
trail_ptr = 0


# -----------------------------
# Animation
# -----------------------------
frames = int(T_TOTAL * FPS)

def init():
    sc._offsets3d = (np.array([]), np.array([]), np.array([]))
    for ln in trail_lines:
        ln.set_data([], [])
        ln.set_3d_properties([])
    time_text.set_text("")
    stage_text.set_text("")
    return (sc, *trail_lines, time_text, stage_text)

def update(i):
    global trail_ptr
    t = i * DT

    if t < T_STAGE1:
        stage = 1
        stage_label = "Stage 1: circular guiding-centres"
    elif t < T_STAGE2:
        stage = 2
        stage_label = f"Stage 2: + epicycles (kappa/Omega = {RADIAL_OSC_PER_AZ_ORBIT:g})"
    else:
        stage = 3
        stage_label = "Stage 3: + vertical oscillations"

    x, y, z = positions(t, stage)
    sc._offsets3d = (x, y, z)

    if stage < 3:
        sc.set_array(None)
        sc.set_color("tab:blue")
    else:
        sc.set_array(z)
        sc.set_cmap("coolwarm")
        sc.set_clim(-z_lim, z_lim)

    # Update trails (last 3 seconds)
    trail_x[:, trail_ptr] = x
    trail_y[:, trail_ptr] = y
    trail_z[:, trail_ptr] = z
    trail_ptr = (trail_ptr + 1) % TRAIL_LEN

    idx = (np.arange(TRAIL_LEN) + trail_ptr) % TRAIL_LEN  # oldest -> newest
    for s in range(N_STARS):
        xs = trail_x[s, idx]
        ys = trail_y[s, idx]
        zs = trail_z[s, idx]
        trail_lines[s].set_data(xs, ys)
        trail_lines[s].set_3d_properties(zs)

    time_text.set_text(f"t = {t:5.2f}s")
    stage_text.set_text(stage_label)

    return (sc, *trail_lines, time_text, stage_text)

anim = FuncAnimation(fig, update, frames=frames, init_func=init, blit=False, interval=1000 / FPS)

plt.show()

if SAVE_MP4:
    anim.save(MP4_NAME, fps=FPS, dpi=160)
    print(f"Saved: {MP4_NAME}")
