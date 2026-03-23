import math

x = y = z = 1
print(f"x={x:d}, y={y:d}, z={z:d}")

(a, b, c) = (1, 2, 3)
print(f"a={a:d}, b={b:d}, c={c:d}")
print(f"abc is a tuple or list or something else? {type((a, b, c))}")
a, b, c = (1, (2, 3), "four")
print(f"a={a:d}, b={b}, c={c}")
print(f"abc is a tuple or list or something else? {type((a, b, c))}")

print(f"a is a tuple or list or something else? {type((a))}")
print(f"b is a tuple or list or something else? {type((b))}")
print(f"c is a tuple or list or something else? {type((c))}")

for x in range(-3, 3, 1):
    y = math.sin(x) / x if x else 1.0
    print(f"x={x:d}, y={y:.3f}")

print("\nNow with try-except:\n")

for x in range(-3, 3, 1):
    try:
        y = math.sin(x) / x if x else 1.0
    except ZeroDivisionError:
        y = 1.0
    print(f"x={x:d}, y={y:.3f}")

# now List Comprehension
print("\nNow with List Comprehension:\n")
xlist = [1, 2, 3, 4, 5, 6]
x2list = [x**2 for x in xlist]
print(f"xlist={xlist}")
print(f"x2list={x2list}")

x2list = []
for x in xlist:
    x2list.append(x**2)
print(f"x2list={x2list}")

# now including a condition
x2list = [x**2 for x in xlist if x % 2 == 0]
print(f"x2list for even numbers={x2list}")

# now square for evens and cube for odds
x23list = [x**2 if x % 2 == 0 else x**3 for x in xlist]
print(f"x23list for even sq'd and odd cubed numbers={x23list}")

# now flattening a list of lists
vlist = [[1, 2], [3, 4], [5, 6]]
flatlist = [v for sublist in vlist for v in sublist]

# the above is equivalent to:
flatlist = []
for sublist in vlist:
    for v in sublist:
        flatlist.append(v)



print(f"vlist={vlist}")
print(f"flatlist={flatlist}")
