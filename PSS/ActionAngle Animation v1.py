import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from datetime import datetime
from matplotlib.animation import FuncAnimation, FFMpegWriter

# ----------------------------
# Animated 2-panel action-angle schematic
# ----------------------------

# Parameters (schematic, not physically exact)
Rg = 8.0
dR = 1.2
kappa_over_Omega = 1.7
Omega = 1.0
Omega_z = 1.35
duration_seconds = 30
fps = 30
n = duration_seconds * fps

t = np.linspace(0, 12 * np.pi, n)
kappa = kappa_over_Omega * Omega

# Orbit in disc plane
R = Rg + dR * np.cos(kappa * t)
phi = Omega * t + 0.15 * np.sin(kappa * t)
x = R * np.cos(phi)
y = R * np.sin(phi)

# Guiding-radius circle
phi_c = np.linspace(0, 2 * np.pi, 400)
xg = Rg * np.cos(phi_c)
yg = Rg * np.sin(phi_c)

# Vertical phase angle evolution
theta0 = np.deg2rad(20.0)
theta_z = theta0 + Omega_z * t

fig, axs = plt.subplots(1, 2, figsize=(11, 5))
fig.suptitle(
    "Action-angle animation: orbit label (actions) + phase (angles)",
    fontsize=18.0,
)

# ---- Left panel: orbit + guiding radius
axL = axs[0]
axL.set_aspect("equal", "box")
axL.plot(xg, yg, lw=1.5, label="Guiding circle ($R_g$)")
axL.plot(x, y, lw=0.8, alpha=0.25, label="Orbit path")
axL.scatter([Rg], [0], s=40, zorder=5)
axL.annotate(
    "Guiding centre",
    xy=(Rg, 0),
    xytext=(Rg + 0.6, -0.8),
    arrowprops=dict(arrowstyle="->", lw=1),
    fontsize=10,
)
axL.annotate("", xy=(Rg, 0), xytext=(0, 0), arrowprops=dict(arrowstyle="<->", lw=1.2))
axL.text(Rg / 2, 0.25, r"$R_g$", ha="center", fontsize=12)

trail_line, = axL.plot([], [], lw=1.8, color="C1", label="Star track (animated)")
star_point, = axL.plot([], [], "o", color="C3", ms=6, zorder=7)
dR_line, = axL.plot([], [], lw=1.4, color="C2")
dR_text = axL.text(0, 0, r"$\Delta R$", fontsize=10, ha="left", va="bottom")

time_text = axL.text(0.02, 0.05, "", transform=axL.transAxes, fontsize=10)

axL.set_title("Orbit in the disc plane", fontsize=15.0)
axL.set_xlabel("x")
axL.set_ylabel("y")
axL.legend(loc="lower left", fontsize=9)
axL.set_xlim(-10.5, 10.5)
axL.set_ylim(-10.5, 10.5)
axL.grid(True, alpha=0.3)

# ---- Right panel: theta_z phase clock
axR = axs[1]
axR.set_aspect("equal", "box")
axR.plot(np.cos(phi_c), np.sin(phi_c), lw=1.5)
axR.scatter([0], [0], s=30)
axR.plot([0, 1], [0, 0], lw=1.0)
axR.text(1.05, 0.0, r"$\theta_z=0$", va="center", fontsize=10)

theta_line, = axR.plot([], [], lw=2.2, color="C3")
theta_tip, = axR.plot([], [], "o", color="C3", ms=5)
arc_line, = axR.plot([], [], lw=2.0, color="C0")
theta_label = axR.text(0, 0, r"$\theta_z$", fontsize=13, ha="center", va="center")
theta_val_text = axR.text(0.02, 0.06, "", transform=axR.transAxes, fontsize=10)

axR.set_title(r"Vertical phase as an angle: $\theta_z$", fontsize=15.0)
axR.set_xticks([])
axR.set_yticks([])
axR.set_xlim(-1.25, 1.25)
axR.set_ylim(-1.25, 1.25)
axR.grid(False)

plt.tight_layout()


def init():
    trail_line.set_data([], [])
    star_point.set_data([], [])
    dR_line.set_data([], [])
    dR_text.set_position((0, 0))
    time_text.set_text("")
    theta_line.set_data([], [])
    theta_tip.set_data([], [])
    arc_line.set_data([], [])
    theta_label.set_position((0, 0))
    theta_val_text.set_text("")
    return (
        trail_line,
        star_point,
        dR_line,
        dR_text,
        time_text,
        theta_line,
        theta_tip,
        arc_line,
        theta_label,
        theta_val_text,
    )


def update(i):
    trail_line.set_data(x[: i + 1], y[: i + 1])
    xi, yi = x[i], y[i]
    star_point.set_data([xi], [yi])

    phii = np.arctan2(yi, xi)
    xRi = Rg * np.cos(phii)
    yRi = Rg * np.sin(phii)
    dR_line.set_data([xRi, xi], [yRi, yi])
    dR_text.set_position(((xRi + xi) / 2, (yRi + yi) / 2))
    time_text.set_text(f"t = {t[i]:.2f}")

    th = theta_z[i]
    ct, st = np.cos(th), np.sin(th)
    theta_line.set_data([0, ct], [0, st])
    theta_tip.set_data([ct], [st])
    theta_label.set_position((0.58 * ct, 0.58 * st))

    a = np.linspace(0, th, 90)
    arc_line.set_data(0.25 * np.cos(a), 0.25 * np.sin(a))
    theta_val_text.set_text(rf"$\theta_z$ = {np.rad2deg(th) % 360:5.1f}$^\circ$")

    return (
        trail_line,
        star_point,
        dR_line,
        dR_text,
        time_text,
        theta_line,
        theta_tip,
        arc_line,
        theta_label,
        theta_val_text,
    )


anim = FuncAnimation(
    fig,
    update,
    frames=n,
    init_func=init,
    interval=1000 / fps,
    blit=False,
    repeat=False,
)

# Auto-export MP4 with timestamped filename
output_dir = Path(
    r"D:\Dropbox\Public Documents\UCLAN\B.Sc. DL Astronomy\AA3057 Collaborative Investigation\PSS Outputs\Animations"
)
output_dir.mkdir(parents=True, exist_ok=True)
timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
output_path = output_dir / f"ActionAngle_Animation_{timestamp}.mp4"

writer = FFMpegWriter(fps=fps, bitrate=2400)
anim.save(str(output_path), writer=writer)
print(f"Saved MP4 to: {output_path}")

plt.show()
