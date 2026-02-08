import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FuncAnimation, PillowWriter

# Simulation parameters
np.random.seed(42)
N = 100
R = 10
mass_range = (0.1, 5.0)
steps = 100
dt = 0.1
epsilon = 0.5


def random_positions(n, radius):
    phi = np.random.uniform(0, 2 * np.pi, n)
    costheta = np.random.uniform(-1, 1, n)
    u = np.random.uniform(0, 1, n)
    theta = np.arccos(costheta)
    r = radius * u ** (1 / 3)
    x = r * np.sin(theta) * np.cos(phi)
    y = r * np.sin(theta) * np.sin(phi)
    return np.vstack((x, y)).T


masses = np.random.uniform(*mass_range, N)
positions = random_positions(N, R)
velocities = np.random.randn(N, 2) * 0.1
position_history = []


def update_positions(pos, vel, masses):
    new_vel = vel.copy()
    for i in range(N):
        acc = np.zeros(2)
        for j in range(N):
            if i != j:
                r_vec = pos[j] - pos[i]
                dist = np.linalg.norm(r_vec) + epsilon
                acc += masses[j] * r_vec / dist**3
        new_vel[i] += acc * dt
    new_pos = pos + new_vel * dt
    return new_pos, new_vel


for _ in range(steps):
    positions, velocities = update_positions(positions, velocities, masses)
    position_history.append(positions.copy())

fig, ax = plt.subplots(figsize=(6, 6))
sc = ax.scatter([], [], s=[], c=[], cmap="viridis")
ax.set_xlim(-15, 15)
ax.set_ylim(-15, 15)
ax.set_title("Mass Segregation in an Open Cluster")


def animate(i):
    pos = position_history[i]
    sc.set_offsets(pos)
    sc.set_sizes(10 * masses)
    sc.set_array(masses)
    return (sc,)


ani = FuncAnimation(fig, animate, frames=steps, interval=50, blit=True)
plt.close()

# Export as GIF
gif_path = "D://Dropbox/Public Documents/UCLAN/AA3050 Dissertation/Kinematics/mass_segregation_simulation.gif"
ani.save(gif_path, writer=PillowWriter(fps=20))

print(f"Animation saved as {gif_path}")
