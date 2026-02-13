# Gravitational constant
# astro_constants_simple_u.py
# Astronomy/Astrophysics constants (SI) with 1-sigma standard uncertainties.
# Fundamental values/uncertainties sourced from NIST/CODATA 2018 tables.

import math

# -------------------------
# Exact (by SI definition, post-2019)
# -------------------------
c = 299792458.0  # m s^-1 (exact)
h = 6.62607015e-34  # J s (exact)
k_B = 1.380649e-23  # J K^-1 (exact)
e = 1.602176634e-19  # C (exact)

# Stefan–Boltzmann is treated as exact in NIST’s listing (derived from exact defining constants)
sigma_SB = 5.670374419e-8  # W m^-2 K^-4 (exact per NIST listing)

# Reduced Planck constant (exact, derived from exact h)
hbar = h / (2 * math.pi)

# -------------------------
# Measured (have uncertainties)
# -------------------------
G = 6.67430e-11  # m^3 kg^-1 s^-2
u_G = 0.00015e-11  # 1σ standard uncertainty

m_e = 9.1093837015e-31  # kg
u_m_e = 0.0000000028e-31  # 1σ

m_p = 1.67262192369e-27  # kg
u_m_p = 0.00000000051e-27  # 1σ

m_n = 1.67492749804e-27  # kg
# (If you want u_m_n too, we can add it from the same CODATA table.)

# -------------------------
# Electromagnetism
# -------------------------
# Note: μ0 is not exact in the revised SI; NIST/CODATA provides a value and uncertainty.
mu_0 = 4 * math.pi * 1e-7  # H m^-1 (≈ 1.25663706212e-6)
u_mu_0 = 1.9e-16  # 1σ (from CODATA 2018: 1.256 637 062 12(19)×10^-6)

epsilon_0 = 1 / (mu_0 * c**2)  # F m^-1
# Propagate uncertainty from mu_0 (c exact): ε0 ∝ 1/μ0 → relative uncertainty same as μ0
u_epsilon_0 = epsilon_0 * (u_mu_0 / mu_0)

# Free-space impedance: η0 = sqrt(μ0/ε0) = μ0*c (given ε0 = 1/(μ0 c^2))
eta_0 = mu_0 * c  # ohms
u_eta_0 = eta_0 * (u_mu_0 / mu_0)

# -------------------------
# Astronomy distances
# -------------------------
AU = 1.495978707e11
pc = 3.085677581491367e16
kpc = 1e3 * pc
Mpc = 1e6 * pc
ly = 9.4607304725808e15

# -------------------------
# Solar/Earth reference values (commonly used; treated as fixed here)
# -------------------------
M_sun = 1.98847e30
R_sun = 6.957e8
L_sun = 3.828e26

M_earth = 5.9722e24
R_earth = 6.371e6

# -------------------------
# Conversions
# -------------------------
deg = math.pi / 180
arcmin = deg / 60
arcsec = arcmin / 60

year = 365.25 * 24 * 3600
Myr = 1e6 * year
Gyr = 1e9 * year

# -------------------------
# OPTIONAL: uncertainty-aware versions (automatic propagation)
# -------------------------
try:
    from uncertainties import ufloat

    G_u = ufloat(G, u_G)
    m_e_u = ufloat(m_e, u_m_e)
    m_p_u = ufloat(m_p, u_m_p)

    mu_0_u = ufloat(mu_0, u_mu_0)
    epsilon_0_u = 1 / (mu_0_u * c**2)
    eta_0_u = mu_0_u * c

except ImportError:
    # If uncertainties isn't installed, just skip ufloat objects.
    pass
