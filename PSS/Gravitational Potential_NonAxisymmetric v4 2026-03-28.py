"""
Plot a non-axisymmetric Milky Way potential in 3D:
The top-left panel compares the true vertical potential rise at fixed radius
against its harmonic approximation, and the other panels show x-y maps at fixed z.

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
from matplotlib.font_manager import FontProperties

# Increase all plot text sizes by about 20% from the previous settings.
FONT_SCALE = 1.8


def _scaled_fontsize(rc_key, fallback_pts):
    size = plt.rcParams.get(rc_key, fallback_pts)
    if isinstance(size, (int, float)):
        return float(size) * FONT_SCALE
    return FontProperties(size=size).get_size_in_points() * FONT_SCALE


TITLE_FONTSIZE = _scaled_fontsize("axes.titlesize", 12)
AXIS_LABEL_FONTSIZE = _scaled_fontsize("axes.labelsize", 10)
TICK_LABEL_FONTSIZE = _scaled_fontsize("xtick.labelsize", 10)
COLORBAR_LABEL_FONTSIZE = AXIS_LABEL_FONTSIZE
COLORBAR_TICK_FONTSIZE = TICK_LABEL_FONTSIZE


def shift_to_nonpositive(phi_component):
    """Shift a potential component by a constant so its maximum is zero."""
    offset = float(np.max(phi_component))
    return phi_component - offset, offset


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

# Evaluate axisymmetric + non-axisymmetric component potentials Phi(R, z=z_kpc, phi)
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

# Shift the zero-point of each plotted component so every contribution is <= 0.
# Potentials are only defined up to additive constants, so this preserves the
# forces while making each displayed term purely attractive.
Phi_axisym_display_dimless, axisym_offset_dimless = shift_to_nonpositive(
    Phi_axisym_dimless
)
Phi_bar_display_dimless, bar_offset_dimless = shift_to_nonpositive(Phi_baronly_dimless)
Phi_spiral_display_dimless, spiral_offset_dimless = shift_to_nonpositive(
    Phi_spiralonly_dimless
)

# Build total explicitly from the three displayed components.
Phi_total_dimless = (
    Phi_axisym_display_dimless + Phi_bar_display_dimless + Phi_spiral_display_dimless
)

# Optional closure check against direct total evaluation in the same gauge.
Phi_total_direct_dimless = np.array(
    [
        evaluatePotentials(mw_nonaxisymmetric, r, z_galpy, phi=p)
        for r, p in zip(R.ravel(), phi.ravel())
    ]
).reshape(R.shape)
Phi_total_direct_display_dimless = Phi_total_direct_dimless - (
    axisym_offset_dimless + bar_offset_dimless + spiral_offset_dimless
)
closure_err_kms2_thousands = (
    (Phi_total_dimless - Phi_total_direct_display_dimless) * vo**2
) / 1000.0
closure_err_max = np.max(np.abs(closure_err_kms2_thousands))

Phi_kms2_thousands = (Phi_total_dimless * vo**2) / 1000.0
Phi_axisym_kms2_thousands = (Phi_axisym_display_dimless * vo**2) / 1000.0
Phi_bar_kms2_thousands = (Phi_bar_display_dimless * vo**2) / 1000.0
Phi_spiral_kms2_thousands = (Phi_spiral_display_dimless * vo**2) / 1000.0
Phi_nonaxisymmetric_kms2_thousands = (
    (Phi_bar_display_dimless + Phi_spiral_display_dimless) * vo**2
) / 1000.0
resid_vlim_total = np.max(np.abs(Phi_nonaxisymmetric_kms2_thousands))
resid_vlim_bar = np.max(np.abs(Phi_bar_kms2_thousands))
resid_vlim_spiral = np.max(np.abs(Phi_spiral_kms2_thousands))

print(f"max |Phi_bar|         = {resid_vlim_bar:.6g} [10^3 (km/s)^2]")
print(f"max |Phi_spiral|      = {resid_vlim_spiral:.6g} [10^3 (km/s)^2]")
print(f"max |Phi_bar+spiral|  = {resid_vlim_total:.6g} [10^3 (km/s)^2]")
print(f"max |closure error|   = {closure_err_max:.6g} [10^3 (km/s)^2]")
print(
    f"axisym zero shift     = {axisym_offset_dimless * vo**2 / 1000.0:.6g} [10^3 (km/s)^2]"
)
print(
    f"bar zero shift        = {bar_offset_dimless * vo**2 / 1000.0:.6g} [10^3 (km/s)^2]"
)
print(
    f"spiral zero shift     = {spiral_offset_dimless * vo**2 / 1000.0:.6g} [10^3 (km/s)^2]"
)
print(f"bar pattern speed     = {bar_pattern_speed_kmskpc:.1f} km/s/kpc")
print(f"spiral pattern speed  = {spiral_pattern_speed_kmskpc:.1f} km/s/kpc")

# Top-left anharmonicity test plus x-y maps
fig = plt.figure(figsize=(14, 10))
ax = fig.add_subplot(2, 2, 1)
R_anharm_kpc = ro
phi_slice_rad = 0.0
z_slice_kpc = np.linspace(0.0, 1.5, 240)
Phi_z_dimless = np.array(
    [
        evaluatePotentials(
            mw_nonaxisymmetric, R_anharm_kpc / ro, z_kpc_i / ro, phi=phi_slice_rad
        )
        for z_kpc_i in z_slice_kpc
    ]
)
Phi_midplane_dimless = evaluatePotentials(
    mw_nonaxisymmetric, R_anharm_kpc / ro, 0.0, phi=phi_slice_rad
)
delta_phi_kms2_thousands = ((Phi_z_dimless - Phi_midplane_dimless) * vo**2) / 1000.0

dz_nu_kpc = 0.01
Phi_plus_dimless = evaluatePotentials(
    mw_nonaxisymmetric, R_anharm_kpc / ro, dz_nu_kpc / ro, phi=phi_slice_rad
)
Phi_minus_dimless = evaluatePotentials(
    mw_nonaxisymmetric, R_anharm_kpc / ro, -dz_nu_kpc / ro, phi=phi_slice_rad
)
nu0_squared_kms2_per_kpc2 = (
    (Phi_plus_dimless - 2.0 * Phi_midplane_dimless + Phi_minus_dimless)
    * vo**2
    / dz_nu_kpc**2
)
delta_phi_harm_kms2_thousands = (
    0.5 * nu0_squared_kms2_per_kpc2 * z_slice_kpc**2
) / 1000.0

ax.plot(
    z_slice_kpc,
    delta_phi_kms2_thousands,
    color="tab:blue",
    linewidth=2.2,
    label=r"True $\Delta \Phi(z)$",
)
ax.plot(
    z_slice_kpc,
    delta_phi_harm_kms2_thousands,
    color="tab:orange",
    linewidth=2.0,
    linestyle="--",
    label=r"Harmonic $\frac{1}{2}\nu_0^2 z^2$",
)
ax.set_xlim(0.0, np.max(z_slice_kpc))
ax.set_xlabel("z [kpc]", fontsize=AXIS_LABEL_FONTSIZE)
ax.set_ylabel(r"$\Delta \Phi$ [10$^3$ (km/s)$^2$]", fontsize=AXIS_LABEL_FONTSIZE)
ax.tick_params(axis="both", labelsize=TICK_LABEL_FONTSIZE)
ax.set_title(
    "Vertical Anharmonicity at Fixed Radius",
    fontsize=TITLE_FONTSIZE,
)
ax.grid(alpha=0.25, linewidth=0.5)
ax.legend(loc="upper left", fontsize=TICK_LABEL_FONTSIZE * 0.78, frameon=True)
ax.text(
    0.04,
    0.94,
    f"R = {R_anharm_kpc:.1f} kpc, $\\phi$ = {np.rad2deg(phi_slice_rad):.0f}$^\\circ$",
    transform=ax.transAxes,
    ha="left",
    va="top",
    fontsize=AXIS_LABEL_FONTSIZE,
    bbox=dict(facecolor="white", alpha=0.75, edgecolor="none"),
)

ax2 = fig.add_subplot(2, 2, 2)
im = ax2.pcolormesh(
    X_kpc,
    Y_kpc,
    Phi_axisym_kms2_thousands,
    shading="auto",
    cmap="viridis",
)
ax2.set_aspect("equal", adjustable="box")
ax2.set_xlabel("X [kpc]", fontsize=AXIS_LABEL_FONTSIZE)
ax2.set_ylabel("Y [kpc]", fontsize=AXIS_LABEL_FONTSIZE)
ax2.tick_params(axis="both", labelsize=TICK_LABEL_FONTSIZE)
ax2.set_title(
    r"Axisymmetric Contribution $\Phi_{\mathrm{axisym}}$",
    fontsize=TITLE_FONTSIZE,
)
ax2.text(
    0.04,
    0.94,
    "z = 500pc",
    transform=ax2.transAxes,
    ha="left",
    va="top",
    fontsize=AXIS_LABEL_FONTSIZE,
    bbox=dict(facecolor="white", alpha=0.75, edgecolor="none"),
)
cbar = fig.colorbar(
    im, ax=ax2, shrink=0.85, pad=0.02, label=r"$\Phi$ [10$^3$ (km/s)$^2$]"
)
cbar.ax.tick_params(labelsize=COLORBAR_TICK_FONTSIZE)
cbar.set_label(r"$\Phi$ [10$^3$ (km/s)$^2$]", fontsize=COLORBAR_LABEL_FONTSIZE)

ax3 = fig.add_subplot(2, 2, 3)
im_bar = ax3.pcolormesh(
    X_kpc,
    Y_kpc,
    Phi_bar_kms2_thousands,
    shading="auto",
    cmap="viridis",
    vmin=np.min(Phi_bar_kms2_thousands),
    vmax=0.0,
)
ax3.set_aspect("equal", adjustable="box")
ax3.set_xlabel("X [kpc]", fontsize=AXIS_LABEL_FONTSIZE)
ax3.set_ylabel("Y [kpc]", fontsize=AXIS_LABEL_FONTSIZE)
ax3.tick_params(axis="both", labelsize=TICK_LABEL_FONTSIZE)
ax3.set_title(r"Bar Contribution $\Phi_{\mathrm{bar}}$", fontsize=TITLE_FONTSIZE)
ax3.text(
    0.04,
    0.94,
    "z = 500pc",
    transform=ax3.transAxes,
    ha="left",
    va="top",
    fontsize=AXIS_LABEL_FONTSIZE,
    bbox=dict(facecolor="white", alpha=0.75, edgecolor="none"),
)
cbar = fig.colorbar(
    im_bar, ax=ax3, shrink=0.85, pad=0.02, label=r"$\Phi$ [10$^3$ (km/s)$^2$]"
)
cbar.ax.tick_params(labelsize=COLORBAR_TICK_FONTSIZE)
cbar.set_label(r"$\Phi$ [10$^3$ (km/s)$^2$]", fontsize=COLORBAR_LABEL_FONTSIZE)

ax4 = fig.add_subplot(2, 2, 4)
im_sp = ax4.pcolormesh(
    X_kpc,
    Y_kpc,
    Phi_spiral_kms2_thousands,
    shading="auto",
    cmap="viridis",
    vmin=np.min(Phi_spiral_kms2_thousands),
    vmax=0.0,
)
ax4.set_aspect("equal", adjustable="box")
ax4.set_xlabel("X [kpc]", fontsize=AXIS_LABEL_FONTSIZE)
ax4.set_ylabel("Y [kpc]", fontsize=AXIS_LABEL_FONTSIZE)
ax4.tick_params(axis="both", labelsize=TICK_LABEL_FONTSIZE)
ax4.set_title(r"Spiral Contribution $\Phi_{\mathrm{spiral}}$", fontsize=TITLE_FONTSIZE)
ax4.text(
    0.04,
    0.94,
    "z = 500pc",
    transform=ax4.transAxes,
    ha="left",
    va="top",
    fontsize=AXIS_LABEL_FONTSIZE,
    bbox=dict(facecolor="white", alpha=0.75, edgecolor="none"),
)
cbar = fig.colorbar(
    im_sp, ax=ax4, shrink=0.85, pad=0.02, label=r"$\Phi$ [10$^3$ (km/s)$^2$]"
)
cbar.ax.tick_params(labelsize=COLORBAR_TICK_FONTSIZE)
cbar.set_label(r"$\Phi$ [10$^3$ (km/s)$^2$]", fontsize=COLORBAR_LABEL_FONTSIZE)

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
        f"anharmonicity_radius_kpc = {R_anharm_kpc}",
        f"anharmonicity_phi_deg = {np.rad2deg(phi_slice_rad)}",
        f"nu0_squared_kms2_per_kpc2 = {nu0_squared_kms2_per_kpc2}",
        f"axisym_zero_shift_1e3kms2 = {axisym_offset_dimless * vo**2 / 1000.0}",
        f"bar_zero_shift_1e3kms2 = {bar_offset_dimless * vo**2 / 1000.0}",
        f"spiral_zero_shift_1e3kms2 = {spiral_offset_dimless * vo**2 / 1000.0}",
        f"max_abs_Phi_barplusspiral_1e3kms2 = {resid_vlim_total}",
        f"max_abs_Phi_bar_1e3kms2 = {resid_vlim_bar}",
        f"max_abs_Phi_spiral_1e3kms2 = {resid_vlim_spiral}",
        f"max_abs_closure_error_1e3kms2 = {closure_err_max}",
    ]
)
(output_dir / f"{output_base}_summary.txt").write_text(summary, encoding="utf-8")

plt.show()
