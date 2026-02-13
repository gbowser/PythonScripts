import math
kb_Name="Boltzmann constant"
Kb = 1.380649e-23
Kb_unc=0.0  # Exact by definition in the revised SI
Kb_units="J K^-1"

c_Name="Speed of light in vacuum"
c= 299792458.0
c_unc=0.0  # Exact by definition in the revised SI
c_units="m s^-1"

h_Name="Planck constant"
h= 6.62607015e-34
h_unc=0.0  # Exact by definition in the revised SI  
h_units="J s"

Na_Name="Avogadro constant"
Na= 6.02214076e23
Na_unc=0.0  # Exact by definition in the revised SI
Na_units="mol^-1"

mu_e0_Name="Vacuum permeability"
mu_e0 = 4 * math.pi * 1e-7
mu_e0_unc=1.9e-16  # 1σ (from CODATA 2018: 1.256 637 062 12(19)×10^-6)
mu_e0_units="H m^-1"

G_Name="Gravitational constant"
G= 6.67430e-11
G_unc=0.00015e-11  # 1σ standard uncertainty
G_units="m^3 kg^-1 s^-2"

# column widths
w1, w2, w3, w4, w5 = 28, 8, 18, 18, 12

# header
print(f"\033[1m{'Name':<{w1}}{'Symbol':<{w2}}{'Value':<{w3}}{'Uncertainty':<{w4}}{'Units':<{w5}}\033[0m")

# rows
print(f"{kb_Name:<{w1}}{'k_B':<{w2}}{Kb:<{w3}.6e}{Kb_unc:<{w4}.2e}{Kb_units:<{w5}}")
print(f"{c_Name:<{w1}}{'c':<{w2}}{c:<{w3}.6e}{c_unc:<{w4}.2e}{c_units:<{w5}}")
print(f"{h_Name:<{w1}}{'h':<{w2}}{h:<{w3}.6e}{h_unc:<{w4}.2e}{h_units:<{w5}}")
print(f"{Na_Name:<{w1}}{'N_A':<{w2}}{Na:<{w3}.6e}{Na_unc:<{w4}.2e}{Na_units:<{w5}}")
print(f"{mu_e0_Name:<{w1}}{'μ_0':<{w2}}{mu_e0:<{w3}.6e}{mu_e0_unc:<{w4}.2e}{mu_e0_units:<{w5}}")
print(f"{G_Name:<{w1}}{'G':<{w2}}{G:<{w3}.6e}{G_unc:<{w4}.2e}{G_units:<{w5}}")

print(f"G = {G:.16f} N m^-2 kg^-2")

# aligned simple-value lines
label_w = 5
value_w = 18
print(f"{'kB':<{label_w}} = {Kb:>{value_w}.6e} {Kb_units}")
print(f"{'mu_e':<{label_w}} = {mu_e0:>{value_w}.6e} {mu_e0_units}")
print(f"{'N_A':<{label_w}} = {Na:>{value_w}.6e} {Na_units}")
print(f"{'c':<{label_w}} = {c:>{value_w}.6e} {c_units}")
