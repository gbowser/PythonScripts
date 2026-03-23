#Example Generator

def count(n):
    i = 0
    while i < n:
        i += 1
        yield i


def triangular_numbers(n):
    i,t=1,0
    while i <= n:
        yield t
        t += i
        i += 1

for j in count(5):
    print(j)


print(f"Triangular numbers up to 5: {list(triangular_numbers(5))}")

def csv_reader(file_name):
    for line in open(file_name, "r", encoding="utf-8"):
        yield line


row_counter = sum(1 for line in csv_reader("dust.csv"))
print(f"Number of rows in dust.csv: {row_counter}")

# Beginner-friendly version without a generator
row_counter_simple = 0
with open("dust.csv", "r", encoding="utf-8") as file:
    for line in file:
        row_counter_simple += 1

print(f"Number of rows in dust.csv with simple loop: {row_counter_simple}")
