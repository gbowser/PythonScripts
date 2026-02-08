# Write your calculate_mean function here.from numpy import mean

import pathlib

import numpy as np

path = pathlib.Path("Data Driven Astronomy/data1.csv")
print(pathlib.Path(__file__).parent.resolve())


def calculate_mean(numlist):
    return np.mean(numlist)


# You can use this to test your function.
# Any code inside this `if` statement will be ignored by the automarker.

# Run your `calculate_mean` function with examples:
mean = calculate_mean([1, 2.2, 0.3, 3.4, 7.9])
print(mean)
#
# Write your calc_stats function here.

fluxes = np.array([23.3, 42.1, 2.0, -3.2, 55.6])
m = np.mean(fluxes)
print(m)
print(np.size(fluxes))  # length of array
print(np.std(fluxes))  # standard deviation


# Run your `calc_stats` function with examples:

data = []
for line in open(path):
    data.append(line.strip().split(","))

print(data)

data = []
for line in open(path):
    data.append(line.strip().split(","))
data = np.asarray(data, float)
print(data)
print("\n\n Now try using loadtxt function")
# 1b-Week 1
data = np.loadtxt(path, delimiter=",")
print(path)
print(data)

print("\n\n\n Now try problem")


def calc_stats(file_in):
    data = np.loadtxt(file_in, delimiter=",")
    mean = np.round(np.mean(data), 2)
    median = np.round(np.median(data), 2)
    return mean, median


# You can use this to test your function.
# Any code inside this `if` statement will be ignored by the automarker.

# Run your `calc_stats` function with examples:
path = pathlib.Path("Data Driven Astronomy/data2.csv")
mean = calc_stats(path)
print(mean)
