import os

print(f"os.getenv('HOME'): {os.getenv('HOME')}")
print(f"os.getenv('PATH'): {os.getenv('PATH')}")
print(f"os.getenv('USER'): {os.getenv('USER')}")

print(f"os.listdir(path=' . '): {os.listdir()}")

print("\nNow onto Randon Numbers \n\n")
import random

print(f"random.randint(1, 10): {random.randint(1, 10)}")

seq = list(range(1, 11))
random.shuffle(seq)
print(f"shuffled seq: {seq}")


raffle_numbers = range(1, 10000)
winners = random.sample(raffle_numbers, k=5)
print(f"random.sample(raffle_numbers, k=5): {winners}")
