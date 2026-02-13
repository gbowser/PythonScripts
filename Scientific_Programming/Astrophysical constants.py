"""
astro_constants.py — Research-grade constants for Astronomy/Astrophysics (SI)

Conventions
- Unless noted, all constants are in SI units.
- Fundamental constants mostly follow exact SI definitions (c, h, k_B, e).
- Solar/planetary “nominal” values are widely used in astronomy (IAU-style) and
  are treated as fixed reference values in many contexts.

Tip:
    import astro_constants as C
    v_esc = (2*C.G*C.M_sun/C.R_sun)**0.5
"""

from __future__ import annotations
import math
from dataclasses import dataclass

__all__ = [
    "C", "list_constants",
]

@dataclass(frozen=True)
class _Constants:
    # =========================
    # Fundamental constants
    # =========================
    c: float = 299_792_458.0             # speed of light (m s^-1) [exact]
    h: float = 6.626_070_15e-34          # Planck constant (J s) [exact]
    k_B: float = 1.380_649e-23           # Boltzmann constant (J K^-1) [exact]
    e: float = 1.602_176_634e-19         # elementary charge (C) [exact]
    G: float = 6.674_30e-11              # gravitational constant (m^3 kg^-1 s^-2)
    sigma_SB: float = 5.670_374_419e-8   # Stefan–Boltzmann (W m^-2 K^-4)

    # EM constants (using the conventional μ0 = 4π×10^-7 H/m approximation)
    mu_0: float = 4.0 * math.pi * 1e-7   # vacuum permeability (H m^-1)
    # epsilon_0 and eta_0 are derived properties below

    # =========================
    # Particle masses
    # =========================
    m_e: float = 9.109_383_7015e-31      # electron mass (kg)
    m_p: float = 1.672_621_923_69e-27    # proton mass (kg)
    m_n: float = 1.674_927_498_04e-27    # neutron mass (kg)

    # =========================
    # Astronomical distance units
    # =========================
    AU: float = 1.495_978_707e11         # astronomical unit (m)
    pc: float = 3.085_677_581_491_367e16 # parsec (m)
    ly: float = 9.460_730_472_580_8e15   # light-year (m)

    # =========================
    # Solar & Earth reference values
    # =========================
    M_sun: float = 1.988_47e30           # solar mass (kg)
    R_sun: float = 6.957e8               # solar radius (m)
    L_sun: float = 3.828e26              # solar luminosity (W)

    M_earth: float = 5.9722e24           # Earth mass (kg)
    R_earth: float = 6.371e6             # Earth radius (m)

    # =========================
    # Angles
    # =========================
    deg: float = math.pi / 180.0         # degrees → radians
    arcmin: float = (math.pi / 180.0) / 60.0
    arcsec: float = (math.pi / 180.0) / 3600.0

    # =========================
    # Time
    # =========================
    day: float = 86400.0
    year: float = 365.25 * 86400.0       # Julian year (s)
    Myr: float = 1e6 * (365.25 * 86400.0)
    Gyr: float = 1e9 * (365.25 * 86400.0)

    # =========================
    # Cosmology defaults (common “order-of-magnitude” value)
    # =========================
    H0_km_s_Mpc: float = 70.0            # H0 (km s^-1 Mpc^-1)

    # ---------- Derived properties (computed from above) ----------
    @property
    def hbar(self) -> float:
        return self.h / (2.0 * math.pi)  # reduced Planck constant (J s)

    @property
    def epsilon_0(self) -> float:
        # vacuum permittivity (F m^-1)
        return 1.0 / (self.mu_0 * self.c**2)

    @property
    def eta_0(self) -> float:
        # impedance of free space (ohms)
        return math.sqrt(self.mu_0 / self.epsilon_0)

    @property
    def kpc(self) -> float:
        return 1e3 * self.pc

    @property
    def Mpc(self) -> float:
        return 1e6 * self.pc

    @property
    def H0(self) -> float:
        # H0 in s^-1
        return self.H0_km_s_Mpc * 1000.0 / self.Mpc

    @property
    def rho_crit(self) -> float:
        # critical density (kg m^-3)
        return 3.0 * self.H0**2 / (8.0 * math.pi * self.G)

    @property
    def GM_sun(self) -> float:
        # solar standard gravitational parameter (m^3 s^-2)
        return self.G * self.M_sun


C = _Constants()


def list_constants() -> None:
    """Print a compact listing of numeric constants (top-level + derived)."""
    # Top-level dataclass fields
    for name in C.__dataclass_fields__:
        val = getattr(C, name)
        if isinstance(val, (int, float)):
            print(f"{name:12s} = {val:.12g}")

    # A few commonly-used derived values
    derived = ["hbar", "epsilon_0", "eta_0", "kpc", "Mpc", "H0", "rho_crit", "GM_sun"]
    for name in derived:
        val = getattr(C, name)
        print(f"{name:12s} = {val:.12g}")
