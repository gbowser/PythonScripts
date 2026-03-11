import numpy

s, a = "hello", [4, 10, 2]
print(s, sep="-")  # should return hello-
print(*s, sep="-")  # h-e-l-l-o
print(a)  # should return [4, 10, 2]
print(*a, sep="-")  # should return 4-10-2

print(f" range of unpacked a --> {range(*a)}")  # should return range(4, 10, 2)
print(f"type of range(*a): {type(range(*a))}")


print(
    f"\n list of range of unpacked a --> {list(range(*a))}"
)  # should return [4, 6, 8]
print(f"\n type of list of range(*a): {type(list(range(*a)))}")

# problem 2.4.2
P = [4, 5, 0, 2]
dPx = []
for i, c in enumerate(P):
    dPx.append(i * c)
print(f"dPx is {dPx}")  # should return [0,5,0,6]
#
# Question 2.4.3 page 56
scores = [87, 50, 65, 50, 10, 3, 56, 32, 32]
rank_by_score = {s: i for i, s in enumerate(sorted(set(scores), reverse=True), 1)}
ranks = [rank_by_score[s] for s in scores]
score_rank_pairs = list(zip(scores, ranks))
print(f"score-rank pairs: {score_rank_pairs}")
print(f"ranks: {ranks}")
#
# Question 2.4.4 page 56
my_pi = 0.0
for i in range(0, 20):
    my_pi += ((-1) ** i) / ((2 * i + 1) * 3.0**i)
my_pi *= numpy.sqrt(12)
print(f"my_pi is {my_pi}")
#
# Question 2.4.5  Iterable sequence
# for what iterable seqeunces x does the expession any(x) and not all (x) return True?
# The expression any(x) returns True if at least one element of x is truthy (i.e., evaluates to True in a boolean context).
# The expression any(x) and not all(x) returns True when:
# 1. x contains at least one truthy value (any(x) is True)
# 2. x contains at least one falsy value (not all(x) is True)
# This happens for any iterable that is non-empty and contains both truthy and falsy values.
# Example: [0, 1, 2] - any([0, 1, 2]) is True because 1 and 2 are truthy
#         not all([0, 1, 2]) is True because 0 is falsy
# So [0, 1, 2] satisfies the condition.
# Another example: [False, True] - any([False, True]) is True because True is truthy
#         not all([False, True]) is True because False is falsy
# So [False, True] also satisfies the condition.

# Question 2.4.6 page 56

my_sequence = [(1, "Albert"), (2, "Brian"), (3, "Calvin")]
print(f"my_sequence is {my_sequence}")
ids, names = zip(*my_sequence)
print("my_sequence unpacked ids:", *ids)
print("my_sequence unpacked names:", *names)
print(f"my_sequence re-packed is {list(zip(ids, names))}")

# Demonstrate why zip(*z) is the inverse of z = zip(a, b)
a = [10, 20, 30]
b = ["x", "y", "z"]
z = list(zip(a, b))
print(f"z = list(zip(a, b)) -> {z}")
a_back, b_back = zip(*z)
print(f"a_back, b_back = zip(*z) -> {a_back}, {b_back}")
print(f"Recovered originals? {list(a_back) == a and list(b_back) == b}")

# question 2.4.7 page 56
months = [
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
]
sun = [44.7, 65.4, 101.7, 148.3, 170.8, 171.3, 153.9, 138.5, 106.6, 63.1, 44.7, 34.4]

for s, m in sorted(zip(sun, months), reverse=True):
    print(f"{m}: {s}")


# Problems 2.4.1 page 56
# given an array of numbers , calculate an array of the same length p in wihch p[i] is the product of all the numbers in a EXCEPT a[i]
# so for example if the input is [1,2,3] then the output should be [6,3,2]
def product_except_self(a):
    n = len(a)
    p = [1] * n
    print(f"initial p: {p}")

    left = 1
    for i in range(n):
        p[i] = left
        left *= a[i]

    right = 1
    for i in range(n - 1, -1, -1):
        p[i] *= right
        right *= a[i]

    return p


my_array = [1, 2, 3, 4, 5]
print(f"product_except_self({my_array}) = {product_except_self(my_array)}")
