"""
Plot a non-axisymmetric Milky Way potential in 3D:
X, Y are the Galactic plane and Z-axis is Phi(X, Y, z=0).

Model = MWPotential2014 + Dehnen bar + SpiralArmsPotential.

Reference notes (approximate, education-focused setup):
- MWPotential2014 baseline: Bovy (2015), ApJS 216, 29,
  doi:10.1088/0067-0049/216/2/29
- Bar angle and pattern-speed context:
  Portail et al. (2017), MNRAS 470, 1233
  https://academic.oup.com/mnras/article/470/1/1233/3854794
  Sanders et al. (2019), MNRAS 488, 4552
  https://academic.oup.com/mnras/article/488/4/4552/5533338
- Spiral functional form: Cox & Gomez (2002),
  https://arxiv.org/abs/astro-ph/0207635
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from galpy.potential import (
    DehnenBarPotential,
    MWPotential2014,
    SpiralArmsPotential,
    evaluatePotentials,
)

# galpy scale factors (set these to your preferred Galactic constants)
ro = 8.2  # kpc
vo = 232.0  # km/s
z_kpc = 0.5  # kpc, vertical height above the MW plane (try 0.0 to 1.0)
z_galpy = z_kpc / ro
output_base = "mw_potential_nonaxisymmetric"
output_dir = Path(
    r"D:\Dropbox\Public Documents\UCLAN\MSc Research\Erwin\data_driven_astronomy_outputs"
)

# Pattern speeds in physical units -> galpy dimensionless units
# Typical modern bar estimates are roughly 31-41 km/s/kpc; we adopt 40.
bar_pattern_speed_kmskpc = 40.0
# Spiral pattern speed is uncertain; 20-30 km/s/kpc is commonly used.
spiral_pattern_speed_kmskpc = 23.0
omegab = bar_pattern_speed_kmskpc * ro / vo
omegasp = spiral_pattern_speed_kmskpc * ro / vo

# Non-axisymmetric components (dimensionless galpy units)
bar = DehnenBarPotential(
    omegab=omegab,
    rb=0.5,
    Af=0.01,
    barphi=np.deg2rad(28.0),
    tform=-10.0,
    tsteady=5.0,
)
spiral = SpiralArmsPotential(
    amp=5e-4,
    N=2,
    alpha=0.2,
    r_ref=1.0,
    phi_ref=np.deg2rad(25.0),
    Rs=0.35,
    H=0.125,
    omega=omegasp,
)

mw_nonaxisymmetric = MWPotential2014 + [bar, spiral]

# XY grid in kpc
x_kpc = np.linspace(-12.0, 12.0, 180)
y_kpc = np.linspace(-12.0, 12.0, 180)
X_kpc, Y_kpc = np.meshgrid(x_kpc, y_kpc)

# Convert to galpy coordinates
R = np.hypot(X_kpc, Y_kpc) / ro
R = np.clip(R, 1e-3, None)  # avoid R=0 singular behavior for some potentials
phi = np.arctan2(Y_kpc, X_kpc)

# Evaluate total and axisymmetric Phi(R, z=z_kpc, phi)
Phi_total_dimless = np.array(
    [
        evaluatePotentials(mw_nonaxisymmetric, r, z_galpy, phi=p)
        for r, p in zip(R.ravel(), phi.ravel())
    ]
).reshape(R.shape)
Phi_axisym_dimless = np.array(
    [evaluatePotentials(MWPotential2014, r, z_galpy) for r in R.ravel()]
).reshape(R.shape)
Phi_baronly_dimless = np.array(
    [
        evaluatePotentials([bar], r, z_galpy, phi=p)
        for r, p in zip(R.ravel(), phi.ravel())
    ]
).reshape(R.shape)
Phi_spiralonly_dimless = np.array(
    [
        evaluatePotentials([spiral], r, z_galpy, phi=p)
        for r, p in zip(R.ravel(), phi.ravel())
    ]
).reshape(R.shape)

Phi_kms2_thousands = (Phi_total_dimless * vo**2) / 1000.0
DeltaPhi_kms2_thousands = ((Phi_total_dimless - Phi_axisym_dimless) * vo**2) / 1000.0
DeltaPhi_bar_kms2_thousands = (Phi_baronly_dimless * vo**2) / 1000.0
DeltaPhi_spiral_kms2_thousands = (Phi_spiralonly_dimless * vo**2) / 1000.0
resid_vlim_total = np.max(np.abs(DeltaPhi_kms2_thousands))
resid_vlim_bar = np.max(np.abs(DeltaPhi_bar_kms2_thousands))
resid_vlim_spiral = np.max(np.abs(DeltaPhi_spiral_kms2_thousands))

print(f"max |DeltaPhi_total|  = {resid_vlim_total:.6g} [10^3 (km/s)^2]")
print(f"max |DeltaPhi_bar|    = {resid_vlim_bar:.6g} [10^3 (km/s)^2]")
print(f"max |DeltaPhi_spiral| = {resid_vlim_spiral:.6g} [10^3 (km/s)^2]")
print(f"bar pattern speed     = {bar_pattern_speed_kmskpc:.1f} km/s/kpc")
print(f"spiral pattern speed  = {spiral_pattern_speed_kmskpc:.1f} km/s/kpc")

# 3D total potential + residual maps
fig = plt.figure(figsize=(14, 10))
ax = fig.add_subplot(2, 2, 1, projection="3d")
surf = ax.plot_surface(
    X_kpc,
    Y_kpc,
    Phi_kms2_thousands,
    cmap="viridis",
    linewidth=0,
    antialiased=True,
)

ax.set_xlabel("X [kpc]")
ax.set_ylabel("Y [kpc]")
ax.set_zlabel(r"$\Phi$ [10$^3$ (km/s)$^2$]")
ax.set_title(
    f"Illustrative Total Potential: MWPotential2014 + Bar + Spiral (z={z_kpc:.2f} kpc)"
)
fig.colorbar(surf, ax=ax, shrink=0.75, pad=0.08, label=r"$\Phi$ [10$^3$ (km/s)$^2$]")

ax2 = fig.add_subplot(2, 2, 2)
im = ax2.pcolormesh(
    X_kpc,
    Y_kpc,
    DeltaPhi_kms2_thousands,
    shading="auto",
    cmap="coolwarm",
    vmin=-resid_vlim_total,
    vmax=resid_vlim_total,
)
ax2.set_aspect("equal", adjustable="box")
ax2.set_xlabel("X [kpc]")
ax2.set_ylabel("Y [kpc]")
ax2.set_title(r"Residual $\Delta\Phi = \Phi_{\mathrm{total}}-\Phi_{\mathrm{axisym}}$")
fig.colorbar(
    im, ax=ax2, shrink=0.85, pad=0.02, label=r"$\Delta\Phi$ [10$^3$ (km/s)$^2$]"
)

ax3 = fig.add_subplot(2, 2, 3)
im_bar = ax3.pcolormesh(
    X_kpc,
    Y_kpc,
    DeltaPhi_bar_kms2_thousands,
    shading="auto",
    cmap="coolwarm",
    vmin=-resid_vlim_bar,
    vmax=resid_vlim_bar,
)
ax3.set_aspect("equal", adjustable="box")
ax3.set_xlabel("X [kpc]")
ax3.set_ylabel("Y [kpc]")
ax3.set_title(r"Bar Contribution $\Delta\Phi_{\mathrm{bar}}$")
fig.colorbar(
    im_bar, ax=ax3, shrink=0.85, pad=0.02, label=r"$\Delta\Phi$ [10$^3$ (km/s)$^2$]"
)

ax4 = fig.add_subplot(2, 2, 4)
im_sp = ax4.pcolormesh(
    X_kpc,
    Y_kpc,
    DeltaPhi_spiral_kms2_thousands,
    shading="auto",
    cmap="coolwarm",
    vmin=-resid_vlim_spiral,
    vmax=resid_vlim_spiral,
)
ax4.set_aspect("equal", adjustable="box")
ax4.set_xlabel("X [kpc]")
ax4.set_ylabel("Y [kpc]")
ax4.set_title(r"Spiral Contribution $\Delta\Phi_{\mathrm{spiral}}$")
fig.colorbar(
    im_sp, ax=ax4, shrink=0.85, pad=0.02, label=r"$\Delta\Phi$ [10$^3$ (km/s)$^2$]"
)

plt.tight_layout()
output_dir.mkdir(parents=True, exist_ok=True)
fig.savefig(output_dir / f"{output_base}.png", dpi=250, bbox_inches="tight")
fig.savefig(output_dir / f"{output_base}.pdf", bbox_inches="tight")

summary = "\n".join(
    [
        "Milky Way Non-Axisymmetric Potential Run Summary",
        f"ro_kpc = {ro}",
        f"vo_kms = {vo}",
        f"z_kpc = {z_kpc}",
        f"bar_pattern_speed_kmskpc = {bar_pattern_speed_kmskpc}",
        f"spiral_pattern_speed_kmskpc = {spiral_pattern_speed_kmskpc}",
        f"bar_omegab_dimensionless = {omegab}",
        f"spiral_omega_dimensionless = {omegasp}",
        f"bar_rb_ro = {0.5}",
        f"bar_Af = {0.01}",
        f"barphi_deg = {28.0}",
        f"spiral_amp = {5e-4}",
        f"spiral_N = {2}",
        f"spiral_alpha = {0.2}",
        f"spiral_Rs = {0.35}",
        f"spiral_H = {0.125}",
        f"max_abs_DeltaPhi_total_1e3kms2 = {resid_vlim_total}",
        f"max_abs_DeltaPhi_bar_1e3kms2 = {resid_vlim_bar}",
        f"max_abs_DeltaPhi_spiral_1e3kms2 = {resid_vlim_spiral}",
    ]
)
(output_dir / f"{output_base}_summary.txt").write_text(summary, encoding="utf-8")

plt.show()
