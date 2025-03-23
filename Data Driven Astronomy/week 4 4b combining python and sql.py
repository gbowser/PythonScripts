import numpy as np


def query(f_name):
    data = np.loadtxt(f_name, delimiter=",", usecols=(0, 2))
    print(data)
    print("\n")
    print(data[:, 1])

    filtered_data = data[data[:, 1] > 1, :]
    filtered_data2 = data[data[:, 1] > 1]

    print(filtered_data)
    print("\n")
    print(filtered_data2)
    print("\n")

    print(np.argsort(filtered_data[:, 1]))
    print("\n")
    sorted_data = filtered_data[np.argsort(filtered_data[:, 1]), :]

    return sorted_data


print(query("stars1.csv"))
