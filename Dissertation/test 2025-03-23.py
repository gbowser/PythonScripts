import random
import string

# Define possible characters
letters = string.ascii_letters  # a-z + A-Z
symbols = '!@#$%^&*()-_=+[]{}|;:,.<>?/'
numbers = string.digits        # 0-9

# Ask user for input
num_letters = int(input("How many letters would you like in your password? "))
num_symbols = int(input("How many symbols would you like? "))
num_numbers = int(input("How many numbers would you like? "))

# Generate random characters
password_letters = random.choices(letters, k=num_letters)
password_symbols = random.choices(symbols, k=num_symbols)
password_numbers = random.choices(numbers, k=num_numbers)

# Combine and shuffle
password_list = password_letters + password_symbols + password_numbers
random.shuffle(password_list)

# Create final password
password = ''.join(password_list)
print("Your generated password is:", password)