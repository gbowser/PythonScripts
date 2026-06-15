import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401
from datetime import datetime
import os

# ============================================================
# Output / saving
# ============================================================
SAVE_MP4 = True

timestamp = datetime.now().strftime("%y%m%d_%H%M%S")
MP4_NAME = rf"D:\Dropbox\Public Documents\UCLAN\B.Sc. DL Astronomy\AA3057 Collaborative Investigation\PSS Outputs\Animations\mw_tilted_3d_trails_{timestamp}.mp4"
os.makedirs(os.path.dirname(MP4_NAME), exist_ok=True)

# ============================================================
# Controls
# ============================================================
SEED = 7
N_STARS = 8

# Toy Galaxy parameters (kpc-like units)
V0 = 1.0
RMIN, RMAX = 6.0, 10.0

# Radial oscillations: κ / Ω
RADIAL_OSC_PER_AZ_ORBIT = 4.0

# Radial epicycle amplitudes (kpc)
A_R_MEAN = 1.0      # ~1 kpc
A_R_STD  = 0.3      # ~300 pc
A_R_MIN  = 0.05

EPICYCLE_FADEIN_S = 1.0  # smooth transition duration

# Vertical oscillations
ZAMP_MEAN = 0.35
ZAMP_SIG  = 0.15
ZAMP_MIN  = 0.05
VERT_SCALE = 0.25

NU0 = 3.2
ALPHA = 1.8
VZ_KICK = 1.0

# Animation timing (model units)
FPS = 30
DT = 1 / FPS
T_STAGE1 = 6.0
STAGE2_DURATION = 10.0
T_STAGE2 = T_STAGE1 + STAGE2_DURATION
T_TOTAL = T_STAGE2 + 10.0

# Viewing angle
VIEW_ELEV_DEG = 20
VIEW_AZIM_DEG = 35

# Trails
TRAIL_SECONDS = 3.0
TRAIL_LEN = int(TRAIL_SECONDS * FPS)

# ============================================================
# Physical time scaling (Myr)
# ============================================================
R0 = 8.0
T_ORBIT_MYR_AT_R0 = 220.0
T_orbit_model_R0 = 2 * np.pi * R0 / V0
MYR_PER_MODEL_TIME = T_ORBIT_MYR_AT_R0 / T_orbit_model_R0

# ============================================================
# Helper functions
# ============================================================
def omega_flat(R):
    return V0 / R

def nu_anharm(A):
    return NU0 / (1.0 + ALPHA * A * A)

def smoothstep01(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3 - 2 * x)

# ============================================================
# Initial conditions
# ============================================================
rng = np.random.default_rng(SEED)

Rg = rng.uniform(RMIN, RMAX, N_STARS)
phi0 = np.linspace(0, 2 * np.pi, N_STARS, endpoint=False)

Omega = omega_flat(Rg)
kappa = RADIAL_OSC_PER_AZ_ORBIT * Omega

# Radial epicycles
aR = np.clip(rng.normal(A_R_MEAN, A_R_STD, N_STARS), A_R_MIN, None)

# Phase so that dR(T_STAGE1) = 0
psi_at_start = rng.choice([0.5 * np.pi, 1.5 * np.pi], size=N_STARS)
psi0 = psi_at_start - kappa * T_STAGE1

# Vertical
A = np.clip(rng.normal(ZAMP_MEAN, ZAMP_SIG, N_STARS), ZAMP_MIN, 0.9) * VERT_SCALE
nu = nu_anharm(A)
theta0 = rng.uniform(0, 2 * np.pi, N_STARS)
kick_sign = rng.choice([-1, 1], size=N_STARS)

# ============================================================
# Dynamics
# ============================================================
def positions(t, stage):
    phi_g = phi0 + Omega * t
    xg = Rg * np.cos(phi_g)
    yg = Rg * np.sin(phi_g)

    if stage == 1:
        return xg, yg, np.zeros_like(Rg)

    tau2 = max(0.0, t - T_STAGE1)
    ramp2 = smoothstep01(tau2 / EPICYCLE_FADEIN_S)

    phase = kappa * t + psi0
    dR = ramp2 * aR * np.cos(phase)
    dphi = ramp2 * (2 * Omega / kappa) * (aR / Rg) * np.sin(phase)

    R = Rg + dR
    phi = phi_g + dphi

    x = R * np.cos(phi)
    y = R * np.sin(phi)

    if stage == 2:
        return x, y, np.zeros_like(Rg)

    t3 = max(0.0, t - T_STAGE2)
    vert_phase = nu * t3 + theta0
    z = A * np.cos(vert_phase)

    ramp3 = 1.0 - np.exp(-t3 / 0.3)
    z += 0.08 * ramp3 * VZ_KICK * kick_sign * np.sin(vert_phase)

    return x, y, z

# ============================================================
# Figure
# ============================================================
plt.rcParams["figure.dpi"] = 120
fig = plt.figure(figsize=(9.5, 7))
ax = fig.add_subplot(111, projection="3d")
ax.view_init(elev=VIEW_ELEV_DEG, azim=VIEW_AZIM_DEG)

lim_xy = RMAX + 2.5
z_lim = max(0.5, float(np.max(A) * 2.5))

ax.set_xlim(-lim_xy, lim_xy)
ax.set_ylim(-lim_xy, lim_xy)
ax.set_zlim(-z_lim, z_lim)

ax.set_xlabel("x (kpc)")
ax.set_ylabel("y (kpc)")
ax.set_zlabel("z (kpc)")
ax.set_title("Milky Way toy orbits (time in Myr)")

# Guide rings
theta = np.linspace(0, 2*np.pi, 400)
for rr in np.linspace(RMIN, RMAX, 5):
    ax.plot(rr*np.cos(theta), rr*np.sin(theta), 0*theta, lw=0.7, alpha=0.25)

sc = ax.scatter([], [], [], s=90, alpha=0.95)

trail_lines = []
for _ in range(N_STARS):
    ln, = ax.plot([], [], [], linestyle=":", lw=1.3, alpha=0.85)
    trail_lines.append(ln)

time_text = ax.text2D(0.02, 0.95, "", transform=ax.transAxes)
stage_text = ax.text2D(0.02, 0.90, "", transform=ax.transAxes)

trail_x = np.full((N_STARS, TRAIL_LEN), np.nan)
trail_y = np.full((N_STARS, TRAIL_LEN), np.nan)
trail_z = np.full((N_STARS, TRAIL_LEN), np.nan)
trail_ptr = 0

# ============================================================
# Animation
# ============================================================
frames = int(T_TOTAL * FPS)

def clear_trails():
    for ln in trail_lines:
        ln.set_data([], [])
        ln.set_3d_properties([])
    trail_x[:] = np.nan
    trail_y[:] = np.nan
    trail_z[:] = np.nan

def init():
    sc._offsets3d = ([], [], [])
    clear_trails()
    return sc, *trail_lines, time_text, stage_text

def update(i):
    global trail_ptr
    t = i * DT
    t_myr = t * MYR_PER_MODEL_TIME

    if t < T_STAGE1:
        stage = 1
        label = "Stage 1: circular guiding centres"
    elif t < T_STAGE2:
        stage = 2
        label = f"Stage 2: epicycles (κ/Ω = {RADIAL_OSC_PER_AZ_ORBIT:g})"
    else:
        stage = 3
        label = "Stage 3: vertical oscillations"

    x, y, z = positions(t, stage)
    sc._offsets3d = (x, y, z)

    trail_x[:, trail_ptr] = x
    trail_y[:, trail_ptr] = y
    trail_z[:, trail_ptr] = z
    trail_ptr = (trail_ptr + 1) % TRAIL_LEN

    idx = (np.arange(TRAIL_LEN) + trail_ptr) % TRAIL_LEN
    for s in range(N_STARS):
        trail_lines[s].set_data(trail_x[s, idx], trail_y[s, idx])
        trail_lines[s].set_3d_properties(trail_z[s, idx])

    if i == frames - 1:
        clear_trails()

    time_text.set_text(f"t = {t_myr:6.1f} Myr")
    stage_text.set_text(label)

    return sc, *trail_lines, time_text, stage_text

anim = FuncAnimation(fig, update, frames=frames, init_func=init,
                     blit=False, interval=1000/FPS)

plt.show()

if SAVE_MP4:
    anim.save(MP4_NAME, fps=FPS, dpi=160)
    print(f"Saved: {MP4_NAME}")
