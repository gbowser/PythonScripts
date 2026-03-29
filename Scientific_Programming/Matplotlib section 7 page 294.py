import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D

fig=plt.figure()

ax=fig.add_subplot()
x=np.linspace(-2,2,1000)
line_cosh,=ax.plot(x,np.cosh(x),label='cosh')
line_quad,=ax.plot(x,1+x**2/2, label='quadratic')

plt.show()

x=np.linspace(-3,3,1000)
y=x**3+2*x**2-x+1
fig=plt.figure()
ax=fig.add_subplot()
ax.plot(x,y)

ax.set_xlim(-1,2)
ax.set_ylim(bottom=0)
plt.show()

x=np.linspace(-np.pi,np.pi,1000)
line,=plt.plot(x,np.sin(x),label='sin')
line.set_dashes([2,4,8,4,2,4])
plt.show()

# eg7-scatter.py


countries = ['Brazil', 'Madagascar', 'S. Korea', 'United States',
             'Ethiopia', 'Pakistan', 'China', 'Belize']

# Birth rate per 1000 population
birth_rate = [16.4, 33.5, 9.5, 14.2, 38.6, 30.2, 13.5, 23.0]

# Life expectancy at birth, years
life_expectancy = [73.7, 64.3, 81.3, 78.8, 63.0, 66.4, 75.2, 73.7]

# Per person income fixed to US Dollars in 2000
GDP = np.array([4800, 240, 16700, 37700, 230, 670, 2640, 3490])

fig, ax = plt.subplots()

# Some arbitrary colors
colors = np.arange(len(countries))
cmap = plt.cm.viridis
point_colors = cmap(np.linspace(0, 1, len(countries)))

ax.scatter(birth_rate, life_expectancy, c=colors, s=GDP/20, cmap=cmap)

ax.set_xlim(5, 45)
ax.set_ylim(60, 85)
ax.set_xlabel('Birth rate per 1000 population')
ax.set_ylabel('Life expectancy at birth (years)')

#plot customisation
ax.set_title('Birth rate and life expectancy')
ax.yaxis.grid(True)
ax.xaxis.grid(True)
ax.set_xlabel('Birth rate per 1000 population', fontsize=14)
ax.set_ylabel('Life expectancy at birth (years)', fontsize=14)

legend_handles = []
for country, point_color in zip(countries, point_colors):
    legend_handles.append(
        Line2D(
            [0],
            [0],
            marker='o',
            color='w',
            label=country,
            markerfacecolor=point_color,
            markersize=8,
        )
    )
ax.legend(handles=legend_handles)
# ax.legend()



plt.show()
