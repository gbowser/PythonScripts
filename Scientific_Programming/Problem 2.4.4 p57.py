# Print out 8 rows of Pascal's triangle neatly.

rows = 8
triangle = []

for row_num in range(rows):
    row = [1]
    if triangle:
        previous_row = triangle[-1]
        for i in range(len(previous_row) - 1):
            row.append(previous_row[i] + previous_row[i + 1])
        row.append(1)
    triangle.append(row)

formatted_rows = [" ".join(f"{num}" for num in row) for row in triangle]
width = len(formatted_rows[-1])

for row_text in formatted_rows:
    print(row_text.center(width))

