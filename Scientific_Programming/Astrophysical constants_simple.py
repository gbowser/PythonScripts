"""
Astrophysics / Astronomy Standard Constants
All values in SI units unless otherwise stated.
Source references: CODATA 2018/IAU 2015 recommended values.
"""
# Constants follow CODATA/IAU recommended values
import math

# =========================
# Fundamental Constants
# =========================
c = 299792458.0  # Speed of light (m s^-1)
G = 6.67430e-11  # Gravitational constant (m^3 kg^-1 s^-2)
h = 6.62607015e-34  # Planck constant (J s)
hbar = h / (2 * math.pi)  # Reduced Planck constant (J s)
k_B = 1.380649e-23  # Boltzmann constant (J K^-1)
e = 1.602176634e-19  # Electron charge (C)
sigma_SB = 5.670374419e-8  # Stefan–Boltzmann constant (W m^-2 K^-4)

# =========================
# Particle Masses
# =========================
m_e = 9.1093837015e-31  # Electron mass (kg)
m_p = 1.67262192369e-27  # Proton mass (kg)
m_n = 1.67492749804e-27  # Neutron mass (kg)

# =========================
# Astronomical Constants
# =========================
AU = 1.495978707e11  # Astronomical Unit (m)
pc = 3.085677581491367e16  # Parsec (m)
kpc = 1e3 * pc
Mpc = 1e6 * pc
ly = 9.4607304725808e15  # Light year (m)

M_sun = 1.98847e30  # Solar mass (kg)
R_sun = 6.957e8  # Solar radius (m)
L_sun = 3.828e26  # Solar luminosity (W)

M_earth = 5.9722e24  # Earth mass (kg)
R_earth = 6.371e6  # Earth radius (m)

# =========================
# Derived Astrophysical Quantities
# =========================
H0_km_s_Mpc = 70.0  # Hubble constant (km/s/Mpc)
H0 = H0_km_s_Mpc * 1000 / Mpc  # Convert to s^-1

rho_crit = 3 * H0**2 / (8 * math.pi * G)  # Critical density (kg m^-3)

# =========================
# Useful Conversion Factors
# =========================
deg = math.pi / 180  # degrees → radians
arcmin = deg / 60
arcsec = arcmin / 60

year = 365.25 * 24 * 3600  # Julian year (s)
Myr = 1e6 * year
Gyr = 1e9 * year

# Electromagnetic constants
mu_0 = 4 * math.pi * 1e-7  # Vacuum permeability (H m^-1 or N A^-2)
epsilon_0 = 1 / (mu_0 * c**2)  # Vacuum permittivity (F m^-1)
eta_0 = math.sqrt(mu_0 / epsilon_0)  # Impedance of free space (Ohms)

def list_constants():
    for name, val in globals().items():
        if not name.startswith("_") and isinstance(val, (int, float)):
            print(f"{name:12s} = {val:.6e}")


list_constants()