import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter, FFMpegWriter

# --------------------------------------------------
# Parameters
# --------------------------------------------------"
video_file = "D://Dropbox/Public Documents/UCLAN/AA3057 Collaborative Investigation/GB Section/pendulum_20251127.mp4"

g = 9.81
N = 80
L0 = 1.0
length_spread = 0.20

A_min = 0.05
A_max = 1.2

dt = 0.05
total_time = 30.0   # 30 seconds simulated time
fps = 20

beta = 1.0
time_factor = 2.0
slowdown = 0.05     # slow evolution

n_frames = int(total_time / dt)
t_array = np.arange(n_frames) * dt * slowdown
t_max = t_array[-1]

# --------------------------------------------------
# Ensemble (pendulums / stars)
# --------------------------------------------------
rng = np.random.default_rng(123)
L = L0 * (1.0 + length_spread * (2*rng.random(N) - 1))
Omega_pend = np.sqrt(g / L)
A = np.linspace(A_min, A_max, N)
Omega_snail = Omega_pend * (1.0 + beta * A)

def compute_state(t):
    phi_pend = Omega_pend * t
    theta = A * np.sin(phi_pend)
    theta_dot = A * Omega_pend * np.cos(phi_pend)

    phi_snail = Omega_snail * (t * time_factor)
    Z = A * np.cos(phi_snail)
    Vz = A * np.sin(phi_snail)
    return theta, theta_dot, Z, Vz

# --------------------------------------------------
# Z(t) tracks
# --------------------------------------------------
sample_indices = [0, N//3, 2*N//3, N-1]
n_samples = len(sample_indices)
Z_tracks = np.zeros((n_samples, n_frames))

for j, idx in enumerate(sample_indices):
    Z_tracks[j] = A[idx] * np.cos(Omega_snail[idx] * t_array * time_factor)

# --------------------------------------------------
# Figure and axes
# --------------------------------------------------
fig, (ax_pend, ax_time, ax_snail) = plt.subplots(1, 3, figsize=(15, 5))

YTOP = 1.5
YBOTTOM = -1.5

for ax in (ax_pend, ax_snail, ax_time):
    ax.set_ylim(YBOTTOM, YTOP)

TITLE_Y = 1.02
ax_pend.set_title("Pendulums - Varying Lengths", y=TITLE_Y)
ax_snail.set_title("Phase-space scatter", y=TITLE_Y)
ax_time.set_title("Z(t) for sample stars", y=TITLE_Y)

ax_snail.set_xlabel("Z")
ax_snail.set_ylabel("Vz")
ax_snail.set_xlim(-1.1*A_max, 1.1*A_max)
ax_snail.grid(True)

ax_time.set_xlabel("t (s)")
ax_time.set_ylabel("Z(t)")
ax_time.set_xlim(0, t_max)
ax_time.grid(True)

# --------------------------------------------------
# Pendulum panel
# --------------------------------------------------
ax_pend.axis("off")

x_pivots = np.linspace(-1.5, 1.5, N)
y_pivot = 0.9 * YTOP

available_height = y_pivot - (YBOTTOM + 0.05*(YTOP - YBOTTOM))
L_disp = available_height * (L / L.max())

swing = L_disp.max() * 1.1
xmin = x_pivots.min() - swing
xmax = x_pivots.max() + swing
ax_pend.set_xlim(xmin, xmax)

freq_norm = (Omega_pend - Omega_pend.min())/(Omega_pend.max() - Omega_pend.min())
pend_colors = plt.cm.plasma(freq_norm)

rod_lines = []
for i in range(N):
    line, = ax_pend.plot([], [], lw=1.5, color=pend_colors[i])
    rod_lines.append(line)

pivot_bar, = ax_pend.plot([xmin, xmax], [y_pivot, y_pivot], lw=3)

scatter = ax_snail.scatter([], [], s=30, alpha=0.8)
scatter.set_facecolors(plt.cm.plasma(np.linspace(0,1,N)))
scatter.set_edgecolors("none")

# --------------------------------------------------
# KEEP: Linear (Archimedean) spiral fit (grey dotted)
# REMOVE: Logarithmic spiral
# --------------------------------------------------
snail_fit_lin, = ax_snail.plot(
    [], [],
    linestyle=":",
    color="dimgray",
    linewidth=4,
    alpha=0.7
)

time_text = ax_snail.text(0.03, 0.97, "", transform=ax_snail.transAxes)

time_lines = []
for j, idx in enumerate(sample_indices):
    line, = ax_time.plot([], [], label=f"star {idx}")
    time_lines.append(line)
ax_time.legend()

# --------------------------------------------------
# Helper: select outer portion of points
# --------------------------------------------------
def _select_outer(Z, Vz, outer_frac):
    phi = np.arctan2(Vz, Z)
    R = np.hypot(Z, Vz)
    R_thresh = np.quantile(R, 1.0 - outer_frac)
    mask = R >= R_thresh
    phi_outer = phi[mask]
    R_outer = R[mask]
    if len(R_outer) < 2:
        return None, None
    phi_unwrap = np.unwrap(phi_outer)
    if np.allclose(phi_unwrap, phi_unwrap[0]):
        return None, None
    return phi_unwrap, R_outer

# --------------------------------------------------
# Linear (Archimedean) spiral fit with inward extension
# --------------------------------------------------
def fit_lin_spiral(Z, Vz, n_samples=400, outer_frac=0.5, extra_turns_inward=1.5):
    phi_unwrap, R_outer = _select_outer(Z, Vz, outer_frac)
    if phi_unwrap is None:
        return np.array([]), np.array([])

    # Least squares: R = a + b * phi
    b, a = np.polyfit(phi_unwrap, R_outer, 1)
    a = max(a, -0.5)

    phi_min_data = phi_unwrap.min()
    phi_max_data = phi_unwrap.max()
    if phi_max_data - phi_min_data < 1e-3:
        return np.array([]), np.array([])

    phi_min = phi_min_data - extra_turns_inward * 2*np.pi
    phi_max = phi_max_data

    phi_fit = np.linspace(phi_min, phi_max, n_samples)
    R_fit = a + b * phi_fit

    R_min_visible = 0.0
    R_max_visible = 1.2 * A_max
    mask_vis = (R_fit > R_min_visible) & (R_fit < R_max_visible)
    if not np.any(mask_vis):
        return np.array([]), np.array([])

    phi_fit = phi_fit[mask_vis]
    R_fit = R_fit[mask_vis]

    Z_fit = R_fit * np.cos(phi_fit)
    Vz_fit = R_fit * np.sin(phi_fit)

    return Z_fit, Vz_fit

# --------------------------------------------------
# Init
# --------------------------------------------------
def init():
    t0 = t_array[0]
    theta, _, Z, Vz = compute_state(t0)

    for i in range(N):
        x0 = x_pivots[i]
        x1 = x0 + L_disp[i] * np.sin(theta[i])
        y1 = y_pivot - L_disp[i] * np.cos(theta[i])
        rod_lines[i].set_data([x0, x1], [y_pivot, y1])

    scatter.set_offsets(np.column_stack((Z, Vz)))

    Z_lin, Vz_lin = fit_lin_spiral(Z, Vz, outer_frac=0.5, extra_turns_inward=1.5)
    snail_fit_lin.set_data(Z_lin, Vz_lin)

    for k in range(n_samples):
        time_lines[k].set_data(t_array[:1], Z_tracks[k, :1])

    time_text.set_text(f"t = {t0:.2f} s")
    return rod_lines + [pivot_bar, scatter, snail_fit_lin, time_text] + time_lines

# --------------------------------------------------
# Update
# --------------------------------------------------
def update(frame):
    t = t_array[frame]
    theta, _, Z, Vz = compute_state(t)

    for i in range(N):
        x0 = x_pivots[i]
        x1 = x0 + L_disp[i] * np.sin(theta[i])
        y1 = y_pivot - L_disp[i] * np.cos(theta[i])
        rod_lines[i].set_data([x0, x1], [y_pivot, y1])

    scatter.set_offsets(np.column_stack((Z, Vz)))

    Z_lin, Vz_lin = fit_lin_spiral(Z, Vz, outer_frac=0.5, extra_turns_inward=1.5)
    snail_fit_lin.set_data(Z_lin, Vz_lin)

    for k in range(n_samples):
        time_lines[k].set_data(t_array[:frame+1], Z_tracks[k, :frame+1])

    time_text.set_text(f"t = {t:.2f} s")
    return rod_lines + [pivot_bar, scatter, snail_fit_lin, time_text] + time_lines

# --------------------------------------------------
# Animate
# --------------------------------------------------
anim = FuncAnimation(
    fig, update, frames=n_frames,
    init_func=init, blit=False, interval=1000*dt
)

# Use ffmpeg writer
writer = FFMpegWriter(fps=fps, bitrate=1800)
anim.save(video_file, writer=writer)
plt.show()