import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
from galpy.potential import MWPotential2014, evaluatePotentials

# Galactic scaling constants
ro = 8.2  # kpc
vo = 232.0  # km/s

# Radius and height grids
R_kpc = np.linspace(0.0, 10.0, 500)
z_levels_kpc = [0.25, 0.50, 0.75, 1.00]
output_dir = Path(
    r"D:\Dropbox\Public Documents\UCLAN\AA3057 Collaborative Investigation\Presentation"
)
output_file_1 = output_dir / "mw_potential_z_vs_r.png"
output_file_2 = output_dir / "mw_potential_r_fixed_vs_z.png"

R_galpy = np.clip(R_kpc / ro, 1e-6, None)

plt.figure(figsize=(9, 6))

for z_kpc in z_levels_kpc:
    z_galpy = z_kpc / ro
    phi_dimless = np.array(
        [evaluatePotentials(MWPotential2014, r, z_galpy) for r in R_galpy]
    )
    phi_1e3_kms2 = (phi_dimless * vo**2) / 1000.0
    plt.plot(R_kpc, phi_1e3_kms2, linewidth=2, label=f"z = {z_kpc:.2f} kpc")

plt.xlim(0.0, 10.0)
plt.xlabel("Radius R [kpc]")
plt.ylabel(r"Potential $\Phi(R, z)$ [$10^3\,(\mathrm{km}/\mathrm{s})^2$]")
plt.title("MWPotential2014: Gravitational Potential vs Radius at Fixed Heights")
plt.grid(True, alpha=0.3)
plt.legend()
plt.tight_layout()
output_dir.mkdir(parents=True, exist_ok=True)
plt.savefig(output_file_1, dpi=300, bbox_inches="tight")

# Second plot: potential (x) vs z (y) for fixed radii
z_kpc = np.linspace(0.0, 1.0, 500)
R_levels_kpc = [2.0, 4.0, 6.0, 10.0]

plt.figure(figsize=(9, 6))

for R_fixed_kpc in R_levels_kpc:
    R_fixed_galpy = max(R_fixed_kpc / ro, 1e-6)
    phi_dimless = np.array(
        [evaluatePotentials(MWPotential2014, R_fixed_galpy, z_val / ro) for z_val in z_kpc]
    )
    phi_1e3_kms2 = (phi_dimless * vo**2) / 1000.0
    plt.plot(phi_1e3_kms2, z_kpc, linewidth=2, label=f"R = {R_fixed_kpc:.0f} kpc")

plt.ylim(0.0, 1.0)
plt.xlabel(r"Potential $\Phi(R, z)$ [$10^3\,(\mathrm{km}/\mathrm{s})^2$]")
plt.ylabel("Height z [kpc]")
plt.title("MWPotential2014: Potential vs Height at Fixed Radii")
plt.grid(True, alpha=0.3)
plt.legend()
plt.tight_layout()
plt.savefig(output_file_2, dpi=300, bbox_inches="tight")
plt.show()
