import matplotlib.pyplot as plt
import numpy as np

# Physical size of the square metal plate, in millimetres.
plate_width = plate_height = 10.0
# Distance between neighbouring grid points in the x and y directions.
grid_spacing_x = grid_spacing_y = 0.1
# Thermal diffusivity of steel, in mm^2 s^-1.
thermal_diffusivity = 4.0

# Background and hot-spot temperatures, in kelvin.
cool_temperature, hot_temperature = 300, 700

# Number of grid points used to represent the plate.
num_points_x = int(plate_width / grid_spacing_x)
num_points_y = int(plate_height / grid_spacing_y)

# Precompute repeated terms used in the diffusion update.
grid_spacing_x_squared = grid_spacing_x * grid_spacing_x
grid_spacing_y_squared = grid_spacing_y * grid_spacing_y
# Choose a stable time step for the explicit finite-difference scheme.
time_step = grid_spacing_x_squared * grid_spacing_y_squared / (
    2
    * thermal_diffusivity
    * (grid_spacing_x_squared + grid_spacing_y_squared)
)

# current_temperature stores the current temperature field;
# next_temperature stores the updated one.
current_temperature = cool_temperature * np.ones((num_points_x, num_points_y))
next_temperature = current_temperature.copy()

# Initial condition: a hot circular patch centred on the plate.
hot_radius = 2
hot_centre_x, hot_centre_y = 5, 5
hot_radius_squared = hot_radius**2
for x_index in range(num_points_x):
    for y_index in range(num_points_y):
        # Squared distance from this grid point to the circle centre.
        distance_squared = (
            (x_index * grid_spacing_x - hot_centre_x) ** 2
            + (y_index * grid_spacing_y - hot_centre_y) ** 2
        )
        if distance_squared < hot_radius_squared:
            current_temperature[x_index, y_index] = hot_temperature


def do_timestep(current_temperature, next_temperature):
    # Advance the 2D diffusion equation by one time step.
    # The interior points are updated from their current value and the
    # temperature of their four nearest neighbours.
    next_temperature[1:-1, 1:-1] = current_temperature[1:-1, 1:-1] + (
        thermal_diffusivity
        * time_step
        * (
            (
                current_temperature[2:, 1:-1]
                - 2 * current_temperature[1:-1, 1:-1]
                + current_temperature[:-2, 1:-1]
            )
            / grid_spacing_x_squared
            + (
                current_temperature[1:-1, 2:]
                - 2 * current_temperature[1:-1, 1:-1]
                + current_temperature[1:-1, :-2]
            )
            / grid_spacing_y_squared
        )
    )

    # Copy the newly computed temperatures so they become the current state
    # for the next iteration.
    current_temperature = next_temperature.copy()
    return current_temperature, next_temperature


# Total number of time steps to simulate.
num_time_steps = 101
# Plot snapshots of the temperature field at these selected steps.
plot_steps = [0, 10, 50, 100]
plot_number = 0
fig, axes = plt.subplots(nrows=2, ncols=2)
for step_number in range(num_time_steps):
    current_temperature, next_temperature = do_timestep(
        current_temperature, next_temperature
    )
    if step_number in plot_steps:
        # Place each snapshot into the next panel of the 2x2 figure.
        ax = axes[plot_number // 2, plot_number % 2]
        im = ax.imshow(
            next_temperature.copy(),
            cmap="hot",
            vmin=cool_temperature,
            vmax=hot_temperature,
            interpolation="bilinear",
        )
        ax.set_axis_off()
        # Convert the simulated time from seconds to milliseconds.
        ax.set_title("{:.1f} ms".format(step_number * time_step * 1000))
        plot_number += 1

# Add a single colour bar to explain how colour maps to temperature.
fig.subplots_adjust(right=0.85)
cbar_ax = fig.add_axes([0.9, 0.15, 0.03, 0.7])
cbar_ax.set_xlabel("$T$ / K", labelpad=20)
fig.colorbar(im, cax=cbar_ax)
plt.show()
