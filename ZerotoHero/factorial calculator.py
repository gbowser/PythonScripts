
def calc_factorial(my_number):
    max_factor = my_number/2
    factor = 1
    while factor <= max_factor:
        if my_number % factor == 0:
            print(factor)
        factor = factor + 1


calc_factorial(5)
