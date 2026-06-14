#basic plotting
import matplotlib.pyplot as plt
import random
import numpy as np
from datetime import datetime

output_dir = "C://Users/gordo/Documents/GitHub/PythonScripts/Scientific_Programming"
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
output_file = f"{output_dir}/Images_{timestamp}.png"

ax=[1,2,3,4,5]
ay=[1,4,9,16,25]

plt.plot(ax,ay) 
plt.xlabel('x-axis')
plt.ylabel('y-axis')    
plt.title('Plot of y = x^2')
plt.show()

ax,ay=[],[]
for i in range(100):
    ax.append(random.uniform(0,10))
    ay.append(random.uniform(0,10))
plt.plot(ax,ay, 'o')  # 'o' for circle markers
plt.xlabel('x-axis')
plt.ylabel('y-axis')
plt.title('Scatter Plot of Random Points')
plt.show()

n=1000
xmin, xmax = -2*np.pi, 2*np.pi
x = np.linspace(xmin, xmax, n)
y = np.sin(x)**2
plt.plot(x, y)
plt.xlabel('x-axis')    
plt.ylabel('y-axis')
plt.title('Plot of y = sin^2(x)')
plt.show()
plt.savefig(output_file)
