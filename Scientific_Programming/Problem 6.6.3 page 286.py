import numpy as np
import matplotlib.pyplot as plt

# Number of bacteria
n_bacteria = 10

# Number of time steps
n_steps = 200

# Step size
step_size = 0.05

# Attractant at the origin
attractant = np.array([0.0, 0.0])

# Initial positions evenly spaced around the unit circle
angles = np.linspace(0, 2 * np.pi, n_bacteria, endpoint=False)
positions = np.column_stack((np.cos(angles), np.sin(angles)))

# Initial directions chosen randomly
directions = np.random.uniform(0, 2 * np.pi, n_bacteria)

# Probabilities:
# If moving toward attractant: more likely to continue
p_continue_toward = 0.8
p_continue_away = 0.3

# Store trajectories
trajectories_x = np.zeros((n_steps + 1, n_bacteria))
trajectories_y = np.zeros((n_steps + 1, n_bacteria))
trajectories_x[0] = positions[:, 0]
trajectories_y[0] = positions[:, 1]

for t in range(1, n_steps + 1):
    for i in range(n_bacteria):
        # Current direction of motion
        v = np.array([np.cos(directions[i]), np.sin(directions[i])])

        # Vector toward attractant
        to_attr = attractant - positions[i]

        # Decide whether bacterium is moving toward or away
        moving_toward = np.dot(v, to_attr) > 0

        # Choose probability of continuing in same direction
        if moving_toward:
            p_continue = p_continue_toward
        else:
            p_continue = p_continue_away

        # Either continue or tumble
        if np.random.rand() >= p_continue:
            directions[i] = np.random.uniform(0, 2 * np.pi)

        # Update position
        positions[i, 0] += step_size * np.cos(directions[i])
        positions[i, 1] += step_size * np.sin(directions[i])

    trajectories_x[t] = positions[:, 0]
    trajectories_y[t] = positions[:, 1]

# Plot trajectories
plt.figure(figsize=(7, 7))

for i in range(n_bacteria):
    plt.plot(trajectories_x[:, i], trajectories_y[:, i], lw=1)
    plt.plot(trajectories_x[0, i], trajectories_y[0, i], 'go', markersize=5)   # start
    plt.plot(trajectories_x[-1, i], trajectories_y[-1, i], 'ro', markersize=5) # end

# Plot unit circle
theta = np.linspace(0, 2 * np.pi, 400)
plt.plot(np.cos(theta), np.sin(theta), 'k--', label='Initial unit circle')

# Plot attractant
plt.plot(0, 0, 'b*', markersize=12, label='Attractant')

plt.xlabel('x')
plt.ylabel('y')
plt.title('Simple chemotaxis model')
plt.axis('equal')
plt.grid(True)
plt.legend()
plt.show()