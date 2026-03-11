# double factorial function n!!, the poroduct of positive odd integers up to and including n


def double_factorial(n):
    if n == 0 or n == 1:
        return 1
    elif n < 0 or n % 2 == 0:
        return "n must be a positive odd integer"
    else:
        double_fact = 1
        for i in range(1, n + 1, 2):
            double_fact *= i
        return double_fact


n = int(input("Enter a positive odd integer: "))
print(f"Double factorial of {n} is {double_factorial(n)}")
