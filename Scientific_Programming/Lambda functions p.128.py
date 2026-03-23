#supports functional programming, but also has a lot of syntactic sugar 
# to make it more readable and easier to write

#lambda functions are anonymous functions that can be defined 
# in a single line of code  

#lambda functions are often used as arguments to 
# higher-order functions, such as map, filter, and reduce
# for example, to square a list of numbers using map and a lambda function:
numbers = [1, 2, 3, 4, 5]   
squared = list(map(lambda x: x**2, numbers))
print(f"numbers={numbers}")
print(f"squared={squared}")

g=lambda x: x**2-3*x+2
print(f"lambda function returns {g(4.1):.2f}")

h=lambda x,y: x**2+2*x*y+y**2
print(f"lambda function returns {h(2., 3.):.2f}")

flist= [lambda x: 1, lambda x: x, lambda x: x**2, lambda x  : x**3]
print(f"flist[0](2)={flist[0](2)}")# returns 1
print(f"flist[1](2)={flist[1](2)}")# returns 2
print(f"flist[2](2)={flist[2](2)}")# returns 4
print(f"flist[3](2)={flist[3](2)}")# returns 8

print(
    f"sorted list: "
    f"{sorted('Nobody expects the Spanish Inquisition'.split(), key=lambda s: s.lower())}"
)

#The with statement is a context manager that allows you to manage resources, such as files,
# in a way that ensures that they are properly cleaned up after use.
with open("MobyDick.txt", "r", encoding="utf-8") as f:
    lines = f.readlines()
print("First 10 lines:")
for line in lines[:10]:
    print(line, end="")
print(f"lines is a list or something else? {type(lines)}")

