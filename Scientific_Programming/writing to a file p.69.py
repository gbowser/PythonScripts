# how to write to a file

f = open("powers.txt", "w")  # open a file for writing
for i in range(100):
    f.write(f"{i} \t {i**2} \t {i**3}\n")  # write to the file
f.close()  # close the file

squares, cubes = [], []
f = open("powers.txt", "r")  # open the file for reading
for line in f.readlines():
    print(line)
    fields = line.split("\t")
    squares.append(int(fields[1]))
    cubes.append(int(fields[2]))
f.close()  # close the file

print(f"Squares: {squares} \nCubes: {cubes} ")
