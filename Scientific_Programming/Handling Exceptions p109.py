try:
    x = int(input("Enter a number: "))
    result = 10 / x
    print("Result:", result)
except ZeroDivisionError:
    print("Error: You cannot divide by zero.")
# code continues here without interruption
except NameError:
    print("Error: NameError occurred.")
# more statements can be added here