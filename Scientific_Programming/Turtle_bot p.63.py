# eg2-turtle.py

commands = "FFFFFLFFFLFFFFRRRFXFFFFFFS"

# Current location, current facing direction.
x, y = 0, 0
dx, dy = 1, 0

# Keep track of the turtle's location in the list of tuples, locs.
locs = [(0, 0)]

for cmd in commands:
    if cmd == "S":
        # Stop command.
        break

    if cmd == "F":
        # Move forward in the current direction.
        x += dx
        y += dy
        if (x, y) in locs:
            print("Path crosses itself at: ({}, {})".format(x, y))
        locs.append((x, y))
        continue

    if cmd == "L":
        # Turn to the left (counterclockwise).
        # L => (dx, dy): (1,0) -> (0,1) -> (-1,0) -> (0,-1) -> (1,0)
        dx, dy = -dy, dx
        continue

    if cmd == "R":
        # Turn to the right (clockwise).
        # R => (dx, dy): (1,0) -> (0,-1) -> (-1,0) -> (0,1) -> (1,0)
        dx, dy = dy, -dx
        continue

    # If we’re here it's because we don't recognize the command: warn.
    print("Unknown command:", cmd)

else:
    # We exhausted the commands without encountering an S for STOP.
    print("Instructions ended without a STOP")

# Plot a path of asterisks.

# First find the total range of x and y values encountered.
x_vals, y_vals = zip(*locs)

xmin, xmax = min(x_vals), max(x_vals)
ymin, ymax = min(y_vals), max(y_vals)

# The grid size needed for the plot is (nx, ny).
nx = xmax - xmin + 1
ny = ymax - ymin + 1

# Reverse the y-axis so that it decreases "down" the screen.
for iy in reversed(range(ny)):
    for ix in range(nx):
        if (ix + xmin, iy + ymin) in locs:
            print("*", end="")
        else:
            print(" ", end="")
    print()
