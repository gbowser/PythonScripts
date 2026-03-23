# Rule 30 cellular automaton
# 80 cells wide, starting with a single "on" cell in the center
# Uses "*" for on and " " for off

width = 80
rows = 40

# Start with all cells off
cells = [0] * width

# Turn on the center cell
cells[width // 2] = 1

for _ in range(rows):
    # Print current row
    line = ""
    for cell in cells:
        if cell == 1:
            line += "*"
        else:
            line += " "
    print(line)

    # Compute next generation
    new_cells = [0] * width

    for i in range(width):
        left = cells[i - 1] if i > 0 else 0
        center = cells[i]
        right = cells[i + 1] if i < width - 1 else 0

        # Rule 30:
        # 111 -> 0
        # 110 -> 0
        # 101 -> 0
        # 100 -> 1
        # 011 -> 1
        # 010 -> 1
        # 001 -> 1
        # 000 -> 0

        pattern = (left, center, right)

        if pattern in [(1, 0, 0), (0, 1, 1), (0, 1, 0), (0, 0, 1)]:
            new_cells[i] = 1
        else:
            new_cells[i] = 0

    cells = new_cells

#### altnerate implementation using bit manipulation for the rule application
print("\nAlternate implementation using bit manipulation for the rule application:\n")

width = 80
rows = 40

cells = [0] * width
cells[width // 2] = 1

for _ in range(rows):
    print("".join("*" if c else " " for c in cells))

    new_cells = [0] * width
    for i in range(width):
        left = cells[i - 1] if i > 0 else 0
        center = cells[i]
        right = cells[i + 1] if i < width - 1 else 0

        # Convert neighborhood to a 3-bit number
        n = 4 * left + 2 * center + right

        # Rule 30 in binary is 00011110
        # Bit test gives the next state
        new_cells[i] = (30 >> n) & 1

    cells = new_cells