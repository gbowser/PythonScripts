# euclid algorithm for finding the greatest common divisor of two numbers
a, b = 1071,462
while b:
    a, b = b, a % b 
print(a)
