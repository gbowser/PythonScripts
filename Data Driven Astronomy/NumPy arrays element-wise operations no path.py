# Write your mean_datasets function here

import numpy as np


def mean_datasets(mylist):
    arraycount = len(mylist)
    if arraycount > 0:
        sum_array = np.loadtxt(mylist[0], delimiter=",")
        for i in range(1, arraycount):
            sum_array = sum_array + np.loadtxt(mylist[i], delimiter=",")

    return np.round(sum_array / 3, 1)


print(mean_datasets(["data4.csv", "data5.csv", "data6.csv"]))
