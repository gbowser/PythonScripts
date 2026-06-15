"""
Plot vertical anharmonicity diagnostics for a non-axisymmetric Milky Way model.

Panels:
1. Potential shape: Delta Phi(z) at fixed radii, compared with the local
   harmonic approximation.
2. Restoring force: F_z(z) compared with the local linear approximation.
3. Vertical frequency versus oscillation amplitude z_max, showing the
   amplitude dependence relevant to phase mixing and the Gaia snail.
4. Face-on map of the vertical-force residual at a reference height,
   highlighting where the bar and spiral structure alter vertical forcing.

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
    evaluatezforces,
)
from matplotlib.font_manager import FontProperties

# Increase all plot text sizes by about 20% from the previous settings.
FONT_SCALE = 1.8
KPC_IN_KM = 3.0856775814913673e16


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
LEGEND_FONTSIZE = TICK_LABEL_FONTSIZE * 0.73


# galpy scale factors (set these to your preferred Galactic constants)
ro = 8.2  # kpc
vo = 232.0  # km/s
output_base = "mw_potential_nonaxisymmetric_vertical_diagnostics"
output_dir = Path(
    r"D:\Dropbox\Public Documents\UCLAN\B.Sc. DL Astronomy\AA3057 Collaborative Investigation\PSS Outputs\Figures"
)

# Pattern speeds in physical units -> galpy dimensionless units
# Typical modern bar estimates are roughly 31-41 km/s/kpc; we adopt 40.
bar_pattern_speed_kmskpc = 40.0
# Spiral pattern speed is uncertain; 20-30 km/s/kpc is commonly used.
spiral_pattern_speed_kmskpc = 23.0
omegab = bar_pattern_speed_kmskpc * ro / vo
omegasp = spiral_pattern_speed_kmskpc * ro / vo

# Non-axisymmetric components (dimensionless galpy units)
barphi_rad = np.deg2rad(28.0)
bar = DehnenBarPotential(
    omegab=omegab,
    rb=0.5,
    Af=0.01,
    barphi=barphi_rad,
    tform=-10.0,
    tsteady=5.0,
)
spiral_N = 2
spiral_alpha_rad = 0.2
spiral_r_ref = 1.0
spiral_phi_ref_rad = np.deg2rad(25.0)
spiral = SpiralArmsPotential(
    amp=5e-4,
    N=spiral_N,
    alpha=spiral_alpha_rad,
    r_ref=spiral_r_ref,
    phi_ref=spiral_phi_ref_rad,
    Rs=0.35,
    H=0.125,
    omega=omegasp,
)

mw_nonaxisymmetric = MWPotential2014 + [bar, spiral]

# Diagnostics settings
phi_slice_rad = 0.0
radii_kpc = np.array([4.0, 8.0, 12.0])
z_plot_kpc = np.linspace(0.0, 1.5, 240)
z_force_kpc = np.linspace(-1.5, 1.5, 321)
zmax_grid_kpc = np.linspace(0.08, 1.5, 32)
dz_nu_kpc = 0.01
integration_points = 1200
colors = ["tab:blue", "tab:orange", "tab:green"]

phi_scan_deg = np.arange(0.0, 181.0, 5.0)
phi_scan_rad = np.deg2rad(phi_scan_deg)
zmax_panel4_kpc = 0.5
radius_force_reference_kpc = 8.0
radius_force_scan_kpc = np.linspace(6.5, 9.5, 121)
radius_force_z_samples_kpc = np.array([0.5, 1.0])
radius_force_colors = ["tab:blue", "tab:orange"]


def phi_physical_kms2(R_kpc, z_kpc, phi_rad):
    return (
        evaluatePotentials(mw_nonaxisymmetric, R_kpc / ro, z_kpc / ro, phi=phi_rad)
        * vo**2
    )


def fz_physical_kms2_per_kpc(R_kpc, z_kpc, phi_rad):
    return (
        evaluatezforces(mw_nonaxisymmetric, R_kpc / ro, z_kpc / ro, phi=phi_rad)
        * vo**2
        / ro
    )


def fz_axisymmetric_kms2_per_kpc(R_kpc, z_kpc):
    return evaluatezforces(MWPotential2014, R_kpc / ro, z_kpc / ro) * vo**2 / ro


def local_nu_squared_kms2_per_kpc2(R_kpc, phi_rad, dz_kpc):
    phi_mid = phi_physical_kms2(R_kpc, 0.0, phi_rad)
    phi_plus = phi_physical_kms2(R_kpc, dz_kpc, phi_rad)
    phi_minus = phi_physical_kms2(R_kpc, -dz_kpc, phi_rad)
    return (phi_plus - 2.0 * phi_mid + phi_minus) / dz_kpc**2


def vertical_frequency_kmskpc(R_kpc, zmax_kpc, phi_rad):
    phi_turn = phi_physical_kms2(R_kpc, zmax_kpc, phi_rad)
    z_samples = np.linspace(0.0, zmax_kpc * (1.0 - 1.0e-6), integration_points)
    delta_phi = phi_turn - np.array(
        [phi_physical_kms2(R_kpc, z_val, phi_rad) for z_val in z_samples]
    )
    delta_phi = np.maximum(delta_phi, 1.0e-12)
    vz_kms = np.sqrt(2.0 * delta_phi)
    quarter_period_s = np.trapezoid(KPC_IN_KM / vz_kms, z_samples)
    full_period_s = 4.0 * quarter_period_s
    omega_s = 2.0 * np.pi / full_period_s
    return omega_s * KPC_IN_KM


def phi_axisymmetric_kms2(R_kpc, z_kpc):
    return evaluatePotentials(MWPotential2014, R_kpc / ro, z_kpc / ro) * vo**2


def vertical_frequency_axisymmetric_kmskpc(R_kpc, zmax_kpc):
    phi_turn = phi_axisymmetric_kms2(R_kpc, zmax_kpc)
    z_samples = np.linspace(0.0, zmax_kpc * (1.0 - 1.0e-6), integration_points)
    delta_phi = phi_turn - np.array(
        [phi_axisymmetric_kms2(R_kpc, z_val) for z_val in z_samples]
    )
    delta_phi = np.maximum(delta_phi, 1.0e-12)
    vz_kms = np.sqrt(2.0 * delta_phi)
    quarter_period_s = np.trapezoid(KPC_IN_KM / vz_kms, z_samples)
    full_period_s = 4.0 * quarter_period_s
    omega_s = 2.0 * np.pi / full_period_s
    return omega_s * KPC_IN_KM


fig, axes = plt.subplots(2, 2, figsize=(18, 12))
ax1, ax2, ax3, ax4 = axes.ravel()
summary_lines = [
    "Milky Way Non-Axisymmetric Vertical Diagnostics Summary",
    f"ro_kpc = {ro}",
    f"vo_kms = {vo}",
    f"bar_pattern_speed_kmskpc = {bar_pattern_speed_kmskpc}",
    f"spiral_pattern_speed_kmskpc = {spiral_pattern_speed_kmskpc}",
    f"bar_omegab_dimensionless = {omegab}",
    f"spiral_omega_dimensionless = {omegasp}",
    f"phi_slice_deg = {np.rad2deg(phi_slice_rad)}",
    f"radii_kpc = {radii_kpc.tolist()}",
    f"panel4_phi_scan_deg = {phi_scan_deg.tolist()}",
    f"panel4_zmax_kpc = {zmax_panel4_kpc}",
    f"radius_force_reference_kpc = {radius_force_reference_kpc}",
    f"radius_force_scan_kpc = [{radius_force_scan_kpc[0]}, ..., {radius_force_scan_kpc[-1]}]",
    f"radius_force_z_samples_kpc = {radius_force_z_samples_kpc.tolist()}",
]

for radius_kpc, color in zip(radii_kpc, colors):
    phi_mid = phi_physical_kms2(radius_kpc, 0.0, phi_slice_rad)
    phi_curve = np.array(
        [phi_physical_kms2(radius_kpc, z_val, phi_slice_rad) for z_val in z_plot_kpc]
    )
    delta_phi_curve_thousands = (phi_curve - phi_mid) / 1000.0

    nu_squared = local_nu_squared_kms2_per_kpc2(radius_kpc, phi_slice_rad, dz_nu_kpc)
    nu_kmskpc = np.sqrt(max(nu_squared, 0.0))
    delta_phi_harm_thousands = 0.5 * nu_squared * z_plot_kpc**2 / 1000.0

    force_curve = np.array(
        [
            fz_physical_kms2_per_kpc(radius_kpc, z_val, phi_slice_rad)
            for z_val in z_force_kpc
        ]
    )
    force_harm = -nu_squared * z_force_kpc

    omega_curve = np.array(
        [
            vertical_frequency_kmskpc(radius_kpc, zmax_kpc, phi_slice_rad)
            for zmax_kpc in zmax_grid_kpc
        ]
    )
    omega_harm = np.full_like(zmax_grid_kpc, nu_kmskpc)

    label = rf"R = {radius_kpc:.0f} kpc"
    ax1.plot(
        z_plot_kpc,
        delta_phi_curve_thousands,
        color=color,
        linewidth=2.3,
        label=f"{label} true",
    )
    ax1.plot(
        z_plot_kpc,
        delta_phi_harm_thousands,
        color=color,
        linewidth=1.8,
        linestyle="--",
        label=f"{label} harmonic",
    )

    ax2.plot(
        z_force_kpc,
        force_curve / 1000.0,
        color=color,
        linewidth=2.3,
        label=f"{label} true",
    )
    ax2.plot(
        z_force_kpc,
        force_harm / 1000.0,
        color=color,
        linewidth=1.8,
        linestyle="--",
        label=f"{label} harmonic",
    )

    ax3.plot(
        zmax_grid_kpc, omega_curve, color=color, linewidth=2.3, label=f"{label} true"
    )
    ax3.plot(
        zmax_grid_kpc,
        omega_harm,
        color=color,
        linewidth=1.8,
        linestyle="--",
        label=f"{label} harmonic",
    )

    summary_lines.extend(
        [
            f"R_{radius_kpc:.1f}_kpc_nu_squared_kms2_per_kpc2 = {nu_squared}",
            f"R_{radius_kpc:.1f}_kpc_nu_kmskpc = {nu_kmskpc}",
            f"R_{radius_kpc:.1f}_kpc_omega_zmax_min_kmskpc = {np.min(omega_curve)}",
            f"R_{radius_kpc:.1f}_kpc_omega_zmax_max_kmskpc = {np.max(omega_curve)}",
        ]
    )

ax1.set_title("Potential Shape", fontsize=TITLE_FONTSIZE)
ax1.set_xlabel("z [kpc]", fontsize=AXIS_LABEL_FONTSIZE)
ax1.set_ylabel(r"$\Delta \Phi$ [10$^3$ (km/s)$^2$]", fontsize=AXIS_LABEL_FONTSIZE)
ax1.tick_params(axis="both", labelsize=TICK_LABEL_FONTSIZE)
ax1.grid(alpha=0.25, linewidth=0.5)
ax1.legend(fontsize=LEGEND_FONTSIZE, loc="upper left", ncol=1, frameon=True)

ax2.set_title("Restoring Force", fontsize=TITLE_FONTSIZE)
ax2.set_xlabel("z [kpc]", fontsize=AXIS_LABEL_FONTSIZE)
ax2.set_ylabel(r"$F_z$ [10$^3$ (km/s)$^2$/kpc]", fontsize=AXIS_LABEL_FONTSIZE)
ax2.tick_params(axis="both", labelsize=TICK_LABEL_FONTSIZE)
ax2.grid(alpha=0.25, linewidth=0.5)
ax2.axhline(0.0, color="0.35", linewidth=0.8, alpha=0.7)
ax2.axvline(0.0, color="0.35", linewidth=0.8, alpha=0.7)
ax2.legend(fontsize=LEGEND_FONTSIZE, loc="lower left", ncol=1, frameon=True)

ax3.set_title("Vertical Frequency vs Amplitude", fontsize=TITLE_FONTSIZE)
ax3.set_xlabel(r"$z_{\max}$ [kpc]", fontsize=AXIS_LABEL_FONTSIZE)
ax3.set_ylabel(r"$\Omega_z$ [km s$^{-1}$ kpc$^{-1}$]", fontsize=AXIS_LABEL_FONTSIZE)
ax3.tick_params(axis="both", labelsize=TICK_LABEL_FONTSIZE)
ax3.grid(alpha=0.25, linewidth=0.5)
ax3.legend(fontsize=LEGEND_FONTSIZE, loc="upper right", ncol=1, frameon=True)

for radius_kpc, color in zip(radii_kpc, colors):
    omega_axisym = vertical_frequency_axisymmetric_kmskpc(radius_kpc, zmax_panel4_kpc)
    omega_full_curve = np.array(
        [
            vertical_frequency_kmskpc(
                radius_kpc, zmax_panel4_kpc, barphi_rad + phi_offset_rad
            )
            for phi_offset_rad in phi_scan_rad
        ]
    )
    delta_omega_curve = omega_full_curve - omega_axisym

    ax4.plot(
        phi_scan_deg,
        delta_omega_curve,
        color=color,
        linewidth=2.1,
        linestyle="-",
        label=rf"R = {radius_kpc:.0f} kpc",
    )

    summary_lines.extend(
        [
            f"R_{radius_kpc:.1f}_kpc_panel4_axisym_omega_kmskpc = {omega_axisym}",
            f"R_{radius_kpc:.1f}_kpc_panel4_full_omega_min_kmskpc = {np.min(omega_full_curve)}",
            f"R_{radius_kpc:.1f}_kpc_panel4_full_omega_max_kmskpc = {np.max(omega_full_curve)}",
            f"R_{radius_kpc:.1f}_kpc_panel4_delta_omega_min_kmskpc = {np.min(delta_omega_curve)}",
            f"R_{radius_kpc:.1f}_kpc_panel4_delta_omega_max_kmskpc = {np.max(delta_omega_curve)}",
        ]
    )

ax4.set_title(
    r"$\Delta \Omega_z$ at $z_{\max}=500$ pc vs Angle", fontsize=TITLE_FONTSIZE
)
ax4.set_xlabel(r"Angle Relative to Bar [$^\circ$]", fontsize=AXIS_LABEL_FONTSIZE)
ax4.set_ylabel(
    r"$\Omega_{z,\mathrm{full}}-\Omega_{z,\mathrm{axi}}$ [km s$^{-1}$ kpc$^{-1}$]",
    fontsize=AXIS_LABEL_FONTSIZE,
)
ax4.tick_params(axis="both", labelsize=TICK_LABEL_FONTSIZE)
ax4.set_xlim(np.min(phi_scan_deg), np.max(phi_scan_deg))
ax4.grid(alpha=0.25, linewidth=0.5)
ax4.axhline(0.0, color="0.35", linewidth=0.8, alpha=0.7)
ax4.text(
    0.03,
    0.97,
    r"Positive values mean bar + spiral raise $\Omega_z$ above axisymmetric",
    transform=ax4.transAxes,
    ha="left",
    va="top",
    fontsize=LEGEND_FONTSIZE,
    bbox=dict(facecolor="white", alpha=0.75, edgecolor="none"),
)
ax4.legend(fontsize=LEGEND_FONTSIZE * 0.92, loc="best", frameon=True, ncol=1)

fig.suptitle(
    r"Vertical Diagnostics in $\mathrm{MWPotential2014} + \Phi_{\mathrm{bar}} + \Phi_{\mathrm{spiral}}$",
    fontsize=TITLE_FONTSIZE * 1.03,
)
plt.tight_layout(rect=[0.0, 0.0, 1.0, 0.97])
output_dir.mkdir(parents=True, exist_ok=True)
fig.savefig(output_dir / f"{output_base}.png", dpi=250, bbox_inches="tight")
fig.savefig(output_dir / f"{output_base}.pdf", bbox_inches="tight")

fig_radius, (ax_radius, ax_frequency_radius) = plt.subplots(
    2, 1, figsize=(9, 12), sharex=True
)
for z_sample_kpc, color in zip(radius_force_z_samples_kpc, radius_force_colors):
    force_radius_curve = np.array(
        [
            fz_physical_kms2_per_kpc(radius_kpc, z_sample_kpc, phi_slice_rad)
            for radius_kpc in radius_force_scan_kpc
        ]
    )
    frequency_radius_curve = np.array(
        [
            vertical_frequency_kmskpc(radius_kpc, z_sample_kpc, phi_slice_rad)
            for radius_kpc in radius_force_scan_kpc
        ]
    )
    ax_radius.plot(
        radius_force_scan_kpc,
        force_radius_curve / 1000.0,
        color=color,
        linewidth=2.3,
        label=rf"z = {int(round(z_sample_kpc * 1000.0))} pc",
    )
    reference_force = (
        fz_physical_kms2_per_kpc(
            radius_force_reference_kpc, z_sample_kpc, phi_slice_rad
        )
        / 1000.0
    )
    reference_frequency = vertical_frequency_kmskpc(
        radius_force_reference_kpc, z_sample_kpc, phi_slice_rad
    )
    ax_radius.scatter(
        [radius_force_reference_kpc],
        [reference_force],
        color=color,
        s=36,
        zorder=3,
    )
    ax_frequency_radius.plot(
        radius_force_scan_kpc,
        frequency_radius_curve,
        color=color,
        linewidth=2.3,
        label=rf"$z_{{\max}}$ = {int(round(z_sample_kpc * 1000.0))} pc",
    )
    ax_frequency_radius.scatter(
        [radius_force_reference_kpc],
        [reference_frequency],
        color=color,
        s=36,
        zorder=3,
    )
    summary_lines.extend(
        [
            f"z_{z_sample_kpc:.1f}_kpc_fz_vs_radius_min_1e3kms2perkpc = {np.min(force_radius_curve / 1000.0)}",
            f"z_{z_sample_kpc:.1f}_kpc_fz_vs_radius_max_1e3kms2perkpc = {np.max(force_radius_curve / 1000.0)}",
            f"z_{z_sample_kpc:.1f}_kpc_fz_at_8kpc_1e3kms2perkpc = {reference_force}",
            f"zmax_{z_sample_kpc:.1f}_kpc_omega_vs_radius_min_kmskpc = {np.min(frequency_radius_curve)}",
            f"zmax_{z_sample_kpc:.1f}_kpc_omega_vs_radius_max_kmskpc = {np.max(frequency_radius_curve)}",
            f"zmax_{z_sample_kpc:.1f}_kpc_omega_at_8kpc_kmskpc = {reference_frequency}",
        ]
    )

ax_radius.set_title("Restoring Force vs Radius Near 8 kpc", fontsize=TITLE_FONTSIZE)
ax_radius.set_ylabel(
    r"$F_z(R,z)$ [10$^3$ (km/s)$^2$/kpc]",
    fontsize=AXIS_LABEL_FONTSIZE,
)
ax_radius.tick_params(axis="both", labelsize=TICK_LABEL_FONTSIZE)
ax_radius.grid(alpha=0.25, linewidth=0.5)
ax_radius.axvline(radius_force_reference_kpc, color="0.35", linewidth=0.8, alpha=0.7)
ax_radius.text(
    0.03,
    0.97,
    rf"Fixed azimuth $\phi$ = {np.rad2deg(phi_slice_rad):.0f}$^\circ$; marker at $R=8$ kpc",
    transform=ax_radius.transAxes,
    ha="left",
    va="top",
    fontsize=LEGEND_FONTSIZE,
    bbox=dict(facecolor="white", alpha=0.75, edgecolor="none"),
)
ax_radius.legend(fontsize=LEGEND_FONTSIZE, loc="best", frameon=True)

ax_frequency_radius.set_title("Vertical Frequency vs Radius", fontsize=TITLE_FONTSIZE)
ax_frequency_radius.set_xlabel("R [kpc]", fontsize=AXIS_LABEL_FONTSIZE)
ax_frequency_radius.set_ylabel(
    r"$\Omega_z(R,z_{\max})$ [km s$^{-1}$ kpc$^{-1}$]",
    fontsize=AXIS_LABEL_FONTSIZE,
)
ax_frequency_radius.tick_params(axis="both", labelsize=TICK_LABEL_FONTSIZE)
ax_frequency_radius.grid(alpha=0.25, linewidth=0.5)
ax_frequency_radius.axvline(
    radius_force_reference_kpc, color="0.35", linewidth=0.8, alpha=0.7
)
ax_frequency_radius.text(
    0.03,
    0.97,
    rf"Fixed azimuth $\phi$ = {np.rad2deg(phi_slice_rad):.0f}$^\circ$; marker at $R=8$ kpc",
    transform=ax_frequency_radius.transAxes,
    ha="left",
    va="top",
    fontsize=LEGEND_FONTSIZE,
    bbox=dict(facecolor="white", alpha=0.75, edgecolor="none"),
)
ax_frequency_radius.legend(fontsize=LEGEND_FONTSIZE, loc="best", frameon=True)
fig_radius.tight_layout()
fig_radius.savefig(
    output_dir / f"{output_base}_radius_force_change.png", dpi=250, bbox_inches="tight"
)
fig_radius.savefig(
    output_dir / f"{output_base}_radius_force_change.pdf", bbox_inches="tight"
)

(output_dir / f"{output_base}_summary.txt").write_text(
    "\n".join(summary_lines), encoding="utf-8"
)
plt.show()
