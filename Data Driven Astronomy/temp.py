# Write your calculate_mean function here.from numpy import mean

import numpy as np


def calculate_mean(numlist):
    return np.mean(numlist)


# You can use this to test your function.
# Any code inside this `if` statement will be ignored by the automarker.

# Run your `calculate_mean` function with examples:
mean = calculate_mean([1, 2.2, 0.3, 3.4, 7.9])
print(mean)
#
# Write your calc_stats function here.

import numpy as np
fluxes = np.array([23.3, 42.1, 2.0, -3.2, 55.6])
m = np.mean(fluxes)
print(m)
print(np.size(fluxes)) # length of array
print(np.std(fluxes))  # standard deviation



# Run your `calc_stats` function with examples:

data = []
for line in open('data.csv'):
    data.append(line.strip().split(','))

print(data)

data = []
for line in open('data.csv'):
    data.append(line.strip().split(','))

data = np.asarray(data, float)
print(data)