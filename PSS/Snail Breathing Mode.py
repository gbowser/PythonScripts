import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, FFMpegWriter
from io import BytesIO
from PIL import Image

# --------------------------------------------------
# Parameters
# --------------------------------------------------"
video_file = "D://Dropbox/Public Documents/UCLAN/AA3057 Collaborative Investigation/GB Section/pendulum_20251127.mp4"
stack_image_file = "D://Dropbox/Public Documents/UCLAN/AA3057 Collaborative Investigation/GB Section/pendulum_snapshots_stack.png"

g = 9.81
N = 80
L0 = 1.0
length_spread = 0.20

A_min = 0.05
A_max = 1.2

dt = 0.05
total_time = 30.0       # 30 seconds of "true" time
fps = 20

beta = 1.0
time_factor = 2.0
slowdown = 0.05         # slows the physics evolution

n_frames = int(total_time / dt)
t_array = np.arange(n_frames) * dt * slowdown
t_max = t_array[-1]      # ≈ 1.4975 seconds

# Actual physical maximum intended:
t_phys_max = total_time * slowdown   # = 1.5 s

# --------------------------------------------------
# Ensemble (pendulums / stars)
# --------------------------------------------------
rng = np.random.default_rng(123)
L = L0 * (1.0 + length_spread * (2*rng.random(N) - 1))
Omega_pend = np.sqrt(g / L)

# Amplitude magnitudes (always positive)
A_mag = np.linspace(A_min, A_max, N)

# Signs: first half negative, second half positive
signs = np.ones(N)
signs[:N//2] = -1.0

# Pendulum amplitudes (signed)
A_pend = A_mag * signs

# Snail radial frequencies still use magnitudes
Omega_snail = Omega_pend * (1.0 + beta * A_mag)

# Z(t) amplitudes for panel 2 (signed → breathing behaviour)
A_time = A_mag * signs

def compute_state(t):
    # Pendulums: initial displacement with zero initial velocity
    phi_pend = Omega_pend * t
    theta = A_pend * np.cos(phi_pend)
    theta_dot = -A_pend * Omega_pend * np.sin(phi_pend)

    # Snail scatter uses magnitudes
    phi_snail = Omega_snail * (t * time_factor)
    Z = A_mag * np.cos(phi_snail)
    Vz = A_mag * np.sin(phi_snail)
    return theta, theta_dot, Z, Vz

# --------------------------------------------------
# Z(t) tracks for panel 2 — breathing mode (signed amplitudes)
# --------------------------------------------------
sample_indices = [0, N//3, 2*N//3, N-1]
n_samples = len(sample_indices)
Z_tracks = np.zeros((n_samples, n_frames))

for j, idx in enumerate(sample_indices):
    Z_tracks[j] = A_time[idx] * np.cos(Omega_snail[idx] * t_array * time_factor)

# --------------------------------------------------
# Figure and axes
# --------------------------------------------------
fig, (ax_pend, ax_time, ax_snail) = plt.subplots(1, 3, figsize=(15, 5))

YTOP = 1.5
YBOTTOM = -1.5

for ax in (ax_pend, ax_snail, ax_time):
    ax.set_ylim(YBOTTOM, YTOP)

TITLE_Y = 1.02
ax_pend.set_title("Pendulums - Varying Lengths (Breathing-like)", y=TITLE_Y)
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
# Linear spiral fit (Archimedean)
# --------------------------------------------------
snail_fit_lin, = ax_snail.plot(
    [], [], linestyle=":", color="dimgray", linewidth=4, alpha=0.7
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
# Linear spiral fit
# --------------------------------------------------
def fit_lin_spiral(Z, Vz, n_samples=400, outer_frac=0.5, extra_turns_inward=1.5):
    phi_unwrap, R_outer = _select_outer(Z, Vz, outer_frac)
    if phi_unwrap is None:
        return np.array([]), np.array([])

    b, a = np.polyfit(phi_unwrap, R_outer, 1)
    a = max(a, -0.5)

    phi_min_data = phi_unwrap.min()
    phi_max_data = phi_unwrap.max()

    phi_min = phi_min_data - extra_turns_inward * 2*np.pi
    phi_max = phi_max_data

    phi_fit = np.linspace(phi_min, phi_max, n_samples)
    R_fit = a + b * phi_fit

    mask_vis = (R_fit > 0.0) & (R_fit < 1.2 * A_max)
    phi_fit = phi_fit[mask_vis]
    R_fit = R_fit[mask_vis]

    Z_fit = R_fit * np.cos(phi_fit)
    Vz_fit = R_fit * np.sin(phi_fit)
    return Z_fit, Vz_fit

# --------------------------------------------------
# Init function
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

    Z_lin, Vz_lin = fit_lin_spiral(Z, Vz)
    snail_fit_lin.set_data(Z_lin, Vz_lin)

    for k in range(n_samples):
        time_lines[k].set_data(t_array[:1], Z_tracks[k, :1])

    time_text.set_text(f"t = {t0:.2f} s")
    return rod_lines + [pivot_bar, scatter, snail_fit_lin, time_text] + time_lines

# --------------------------------------------------
# Update per frame
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

    Z_lin, Vz_lin = fit_lin_spiral(Z, Vz)
    snail_fit_lin.set_data(Z_lin, Vz_lin)

    for k in range(n_samples):
        time_lines[k].set_data(t_array[:frame+1], Z_tracks[k, :frame+1])

    time_text.set_text(f"t = {t:.2f} s")
    return rod_lines + [pivot_bar, scatter, snail_fit_lin, time_text] + time_lines

# --------------------------------------------------
# Create animation file
# --------------------------------------------------
anim = FuncAnimation(fig, update, frames=n_frames,
                     init_func=init, blit=False, interval=1000*dt)

writer = FFMpegWriter(fps=fps, bitrate=1800)
anim.save(video_file, writer=writer)

# --------------------------------------------------
# SNAPSHOTS EVERY 0.5 s — INCLUDING t = 1.5 s
# --------------------------------------------------
def capture_figure():
    buf = BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=150)
    buf.seek(0)
    im = Image.open(buf)
    im.load()
    buf.close()
    return im

# initialise state
init()

# Snapshot times: 0.5, 1.0, 1.5
snapshot_times = np.arange(0.5, t_phys_max + 0.25, 0.5)

images = []
for t_snap in snapshot_times:
    frame = int(np.argmin(np.abs(t_array - t_snap)))
    update(frame)
    images.append(capture_figure())

# Stack vertically
width = max(im.width for im in images)
total_height = sum(im.height for im in images)

stacked = Image.new("RGB", (width, total_height), (255, 255, 255))
y_offset = 0
for im in images:
    stacked.paste(im, (0, y_offset))
    y_offset += im.height

stacked.save(stack_image_file)

plt.show()
