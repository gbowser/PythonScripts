import matplotlib.pyplot as plt
import numpy as np

# plate size, mm
w = h = 10.0
# intervals in x-, y- directions, mm
dx = dy = 0.1
# Thermal diffusivity of steel, mm2.s-1
D = 4.0

Tcool, Thot = 300, 700

nx, ny = int(w / dx), int(h / dy)

dx2, dy2 = dx * dx, dy * dy
dt = dx2 * dy2 / (2 * D * (dx2 + dy2))

u0 = Tcool * np.ones((nx, ny))
u = u0.copy()

# Initial conditions - circle of radius r centred at (cx,cy) (mm)
r, cx, cy = 2, 5, 5
r2 = r**2
for i in range(nx):
    for j in range(ny):
        p2 = (i * dx - cx) ** 2 + (j * dy - cy) ** 2
        if p2 < r2:
            u0[i, j] = Thot


def do_timestep(u0, u):
    # Propagate with forward-difference in time, central-difference in space.
    u[1:-1, 1:-1] = u0[1:-1, 1:-1] + D * dt * (
        (u0[2:, 1:-1] - 2 * u0[1:-1, 1:-1] + u0[:-2, 1:-1]) / dx2
        + (u0[1:-1, 2:] - 2 * u0[1:-1, 1:-1] + u0[1:-1, :-2]) / dy2
    )

    u0 = u.copy()
    return u0, u


# Number of timesteps.
nsteps = 101
# Output 4 figures at these timesteps.
mfig = [0, 10, 50, 100]
fignum = 0
fig, axes = plt.subplots(nrows=2, ncols=2)
for m in range(nsteps):
    u0, u = do_timestep(u0, u)
    if m in mfig:
        print(m, fignum)
        ax = axes[fignum // 2, fignum % 2]
        im = ax.imshow(
            u.copy(),
            cmap="hot",
            vmin=Tcool,
            vmax=Thot,
            interpolation="bilinear",
        )
        ax.set_axis_off()
        ax.set_title("{:.1f} ms".format(m * dt * 1000))
        fignum += 1
fig.subplots_adjust(right=0.85)
cbar_ax = fig.add_axes([0.9, 0.15, 0.03, 0.7])
cbar_ax.set_xlabel("$T$ / K", labelpad=20)
fig.colorbar(im, cax=cbar_ax)
plt.show()
