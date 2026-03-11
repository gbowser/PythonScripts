# Basic plotting p.89
import matplotlib.pyplot as plt
import numpy as np

n = 1000
xmin, xmax = -2.0 * np.pi, 2.0 * np.pi

x = np.linspace(xmin, xmax, n)
y1 = np.sin(x) ** 2
y2 = np.cos(x) ** 2
plt.plot(x, y1)
plt.plot(x, y2)
plt.show()



#example E3.2
#to plot sinc(x) = sin(x)/x
x=np.linspace(-20, 20, 1001)
y=np.sin(x)/x
plt.plot(x, y)  
plt.title('sinc(x)')
plt.xlabel('x')
plt.ylabel('sinc(x)')
plt.grid()
plt.show()
