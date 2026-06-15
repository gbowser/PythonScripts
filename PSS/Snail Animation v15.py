from io import BytesIO

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FFMpegWriter, FuncAnimation
from PIL import Image

# --------------------------------------------------
# Parameters
# --------------------------------------------------
video_file = "D://Dropbox/Public Documents/UCLAN/B.Sc. DL Astronomy/AA3057 Collaborative Investigation/PSS Outputs/Animations/pendulum_20251127.mp4"
stack_image_file = "D://Dropbox/Public Documents/UCLAN/B.Sc. DL Astronomy/AA3057 Collaborative Investigation/PSS Outputs/Animations/pendulum_snapshots_stack.png"

g = 9.81
N = 80
L0 = 1.0
length_spread = 0.20

A_min = 0.05
A_max = 1.2

dt = 0.05
total_time = 30.0

fps = 40

beta = 1.0
time_factor = 2.0
slowdown = 0.05

n_frames = int(total_time / dt)
t_array = np.arange(n_frames) * dt * slowdown
t_max = t_array[-1]
t_phys_max = total_time * slowdown

# --------------------------------------------------
# Ensemble
# --------------------------------------------------
rng = np.random.default_rng(123)
L = L0 * (1.0 + length_spread * (2 * rng.random(N) - 1))
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
# θ(t) tracks
# --------------------------------------------------
sample_indices = [0, N // 3, 2 * N // 3, N - 1]
n_samples = len(sample_indices)

theta_tracks_deg = np.zeros((n_samples, n_frames))
for j, idx in enumerate(sample_indices):
    theta_tracks_deg[j] = np.degrees(
        A[idx] * np.sin(Omega_pend[idx] * t_array)
    )

# --------------------------------------------------
# Figure and axes
# --------------------------------------------------
fig, (ax_pend, ax_time, ax_snail) = plt.subplots(1, 3, figsize=(15, 5))

# --- MOVE Y-LABELS CLOSER (ONLY CHANGE) ---
for ax in (ax_time, ax_snail):
    ax.yaxis.labelpad = -10

YTOP = 1.5
YBOTTOM = -1.5

for ax in (ax_pend, ax_snail, ax_time):
    ax.set_ylim(YBOTTOM, YTOP)

TITLE_Y = 1.02
ax_pend.set_title("Pendulums - Varying Lengths", y=TITLE_Y)
ax_snail.set_title(r"Phase space: $\theta$ vs $V_{\theta}$", y=TITLE_Y)
ax_time.set_title(r"$\theta(t)$ for sample pendulums", y=TITLE_Y)

ax_snail.set_xlabel(r"$\theta$ (deg)")
ax_snail.set_ylabel(r"$V_{\theta}$ (deg/s)")
ax_snail.grid(True)

theta_max_deg = np.degrees(A_max)
ax_snail.set_xlim(-1.1 * theta_max_deg, 1.1 * theta_max_deg)
ax_snail.set_ylim(-1.1 * theta_max_deg, 1.1 * theta_max_deg)

ax_time.set_xlabel("t (s)")
ax_time.set_ylabel(r"$\theta(t)$ (deg)")
ax_time.set_xlim(0, t_max)
ax_time.set_ylim(-1.1 * theta_max_deg, 1.1 * theta_max_deg)
ax_time.grid(True)

# --------------------------------------------------
# Pendulum panel
# --------------------------------------------------
ax_pend.axis("off")

x_pivots = np.linspace(-1.5, 1.5, N)
y_pivot = 0.9 * YTOP

available_height = y_pivot - (YBOTTOM + 0.05 * (YTOP - YBOTTOM))
L_disp = available_height * (L / L.max())

swing = L_disp.max() * 1.1
xmin = x_pivots.min() - swing
xmax = x_pivots.max() + swing
ax_pend.set_xlim(xmin, xmax)

freq_norm = (Omega_pend - Omega_pend.min()) / (Omega_pend.max() - Omega_pend.min())
pend_colors = plt.cm.plasma(freq_norm)

rod_lines = []
for i in range(N):
    (line,) = ax_pend.plot([], [], lw=1.5, color=pend_colors[i])
    rod_lines.append(line)

(pivot_bar,) = ax_pend.plot([xmin, xmax], [y_pivot, y_pivot], lw=3)

scatter = ax_snail.scatter([], [], s=30, alpha=0.8)
scatter.set_facecolors(plt.cm.plasma(np.linspace(0, 1, N)))
scatter.set_edgecolors("none")

(snail_fit_lin,) = ax_snail.plot([], [], linestyle=":", linewidth=4, alpha=0.7)
time_text = ax_snail.text(0.03, 0.97, "", transform=ax_snail.transAxes)

time_lines = []
for j, idx in enumerate(sample_indices):
    (line,) = ax_time.plot([], [], label=f"pendulum {idx}")
    time_lines.append(line)
ax_time.legend()

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

    scatter.set_offsets(
        np.column_stack((np.degrees(Z), np.degrees(Vz)))
    )

    for k in range(n_samples):
        time_lines[k].set_data(t_array[:1], theta_tracks_deg[k, :1])

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

    scatter.set_offsets(
        np.column_stack((np.degrees(Z), np.degrees(Vz)))
    )

    for k in range(n_samples):
        time_lines[k].set_data(
            t_array[: frame + 1], theta_tracks_deg[k, : frame + 1]
        )

    time_text.set_text(f"t = {t:.2f} s")
    return rod_lines + [pivot_bar, scatter, snail_fit_lin, time_text] + time_lines


# --------------------------------------------------
# Animate
# --------------------------------------------------
anim = FuncAnimation(
    fig,
    update,
    frames=n_frames,
    init_func=init,
    blit=False,
    interval=1000 * dt / 2,
)

writer = FFMpegWriter(fps=fps, bitrate=1800)
anim.save(video_file, writer=writer)

plt.show()
