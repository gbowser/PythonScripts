import matplotlib.pyplot as plt
#constants
Boltzmann_constant = 1.380649e-23  # J/K
A=1.024e-23/Boltzmann_constant   #Jnm^6
B=1.582e-26/Boltzmann_constant


def U(r):
    """Return the potential energy of two argon atoms separated by r nm."""
    return -A/r**6 + B/r**12

def F(r):
    return -6*A/r**7 + 12*B/r**13

def V(r,r0, k):
    """Return the kinetic energy of two argon atoms separated by r nm."""
    return 0.5 * k * (r-r0)**2

def k(r):
    """Return the effective spring constant of two argon atoms separated by r nm."""
    return (156*B/r**14) -(42*A/r**8)
    


#plotting
r_values = [0.3 + 0.01*i for i in range(100)]
U_values = [U(r) for r in r_values]
F_values = [F(r) for r in r_values]
V_values = [V(r, 0.38, k(0.38)) for r in r_values]


#set up 1st plot of U(r) and F(r) on the same graph
fig, ax1 = plt.subplots()
ax2 = ax1.twinx()

ax1.plot(r_values, U_values, color='tab:blue')
ax2.plot(r_values, F_values, color='tab:red')

ax1.set_xlabel('r (nm)')
ax1.set_ylabel('U (J)', color='tab:blue')
ax2.set_ylabel('F(r)', color='tab:red')
plt.title('Potential Energy of Two Argon Atoms')
plt.show()  

# now plot U(r) and V(r) on the same graph
fig, ax1 = plt.subplots()
ax2 = ax1.twinx()

ax1.plot(r_values, U_values, color='tab:blue')
ax2.plot(r_values, V_values, color='tab:red')

ax1.set_xlabel('r (nm)')
ax1.set_ylabel('U (J)', color='tab:blue')
ax2.set_ylabel('V (J)', color='tab:red')
plt.title('Potential Energy of Two Argon Atoms')
plt.show()  
