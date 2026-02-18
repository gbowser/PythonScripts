import math

list2 = [5, 6, 7, "eight", 9.0]
list1 = [1, "two", 3.0, [4, 5, 6], list2]

print(list1)
print(list2)
print(list1[3][2])  # should return 6
print(list1[4][2])  # should return 7
print(list1[4][3][2])  # should return g

list2[3] = "eighty"
print(list2)
list1[4][3] = "ninety"
print(list2)

q1 = [1, 2, 3]
q2 = q1
q1[2] = "oops"
print(q1)
print(q2)

a = 3
q = [1, 2, a]
a = 4
print(q)
print(list1)
print(list1[::-1])

list1.append("ten")
list1.reverse()
print(list1)
list1.remove(1)
print(list1)
list1.pop()
print(list1)
list3 = [3, 5, 1, 7, 4, 8, 3, 9, 2, 6]

list4 = sorted(list3, reverse=True)
print(list4)

list3.sort()
print(list3)

s = "Jan, Feb, Mar, Apr, May, Jun, Jul, Aug, Sep, Oct, Nov, Dec"
print(s.split(", "))

print(list("hello"))  # should return ['h', 'e', 'l', 'l', 'o']

a = [5, 4, 3, 2, 1]
b = a
print(f"b is a  --> {b is a}")
print(f"b == a  --> {b == a}")
# page 50
b = list(a)
print(b)
print(f"b is a  --> {b is a}")
print(f"b == a  --> {b == a}")

a = [1, 0, 0, 2, 3]
print(f" array is {a}")
print(f"any(a) -->  {any(a)}")
print(f"all(a) -->  {all(a)}")

# page 51
a = [3, 4]
print(f"hypotenuse using slices {math.hypot(a[0], a[1])}")
print(f"hypotenuse using unpacking {math.hypot(*a)}")

fruit_list = ["apple", "banana", "cherry", "date", "elderberry"]
for fruit in fruit_list:
    print(f"a fruit in list is {fruit}")
    for i, letter in enumerate(fruit):
        if i % 2 == 1:  # Print every other letter (odd indices)
            print(f"    letter {i}: {letter}")

# page 52
numbers = ["one", "two", "three", "four", "five"]
print(f"\n'{', '.join(reversed(numbers))}'")

a = range(5)
print(f"range(5) --> {a}")
print(f"list(range(5)) --> {list(a)}")

a = range(1, 8, 3)
print(f"range(1,8,3) --> {a}")
print(f"list(range(1,8,3)) --> {list(a)}")

a = range(19, 7, -3)
print(f"range(19,7,-3) --> {a}")
print(f"list(range(19,7,-3)) --> {list(a)}")

# Fibonnaci numbers
n = 10
fib = [1, 1]
for i in range(2, n + 1):
    fib.append(fib[i - 1] + fib[i - 2])
print(fib)

# alternative way to generate Fibonacci numbers
a, b = 1, 1
print(a, b, end="")
for i in range(2, n + 1):
    # the next number is a+b and then a becomes the previous b
    a, b = b, a + b
    print(f" {b}", end="")
print()

mammals = ["dog", "cat", "mouse", "hamster", "rabbit"]
for i, mammal in enumerate(mammals,4):
    print(f"{i}th animal is : {mammal}") 

