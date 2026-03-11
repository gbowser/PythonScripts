import matplotlib.pyplot as plt
import random
data=[]
for i in range(5000):
    data.append(random.normalvariate(0, 1))
plt.hist(data, bins=20, edgecolor='black')
plt.show()
