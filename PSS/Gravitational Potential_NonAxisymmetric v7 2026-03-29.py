"""
Plot vertical force and frequency diagnostics for a non-axisymmetric Milky Way model.

Panels:
1. Restoring force versus z at fixed radii, compared with the local
   harmonic approximation.
2. Vertical frequency versus z_max at fixed radii, compared with the local
   harmonic approximation.
3. Restoring force versus radius at fixed heights.
4. Vertical frequency versus radius at fixed amplitudes.
5. Restoring force versus azimuthal angle relative to the bar.
6. Vertical frequency versus azimuthal angle relative to the bar.

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

from datetime import datetime
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
FONT_SCALE = 2.34
KPC_IN_KM = 3.0856775814913673e16
SECONDS_PER_MYR = 365.25 * 24.0 * 3600.0 * 1.0e6


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
z_force_plot_kpc = np.linspace(0.01, 1.5, 240)
z_frequency_plot_kpc = np.linspace(0.08, 1.5, 32)
dz_nu_kpc = 0.01
integration_points = 1200
colors = ["tab:blue", "tab:orange", "tab:green"]

phi_scan_deg = np.arange(0.0, 181.0, 5.0)
phi_scan_rad = np.deg2rad(phi_scan_deg)
angle_force_height_kpc = 0.5
angle_frequency_zmax_kpc = 0.5
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


def vertical_period_myr_from_omega_kmskpc(omega_kmskpc):
    omega_s = omega_kmskpc / KPC_IN_KM
    return (2.0 * np.pi / omega_s) / SECONDS_PER_MYR


timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
fig_height, (ax_force_z, ax_frequency_z) = plt.subplots(1, 2, figsize=(18, 7.5))
fig_radius, (ax_force_radius, ax_frequency_radius) = plt.subplots(1, 2, figsize=(18, 7.5))
fig_angle, (ax_force_phi, ax_frequency_phi) = plt.subplots(1, 2, figsize=(18, 7.5))
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
    f"phi_scan_deg = {phi_scan_deg.tolist()}",
    f"angle_force_height_kpc = {angle_force_height_kpc}",
    f"angle_frequency_zmax_kpc = {angle_frequency_zmax_kpc}",
    f"radius_force_reference_kpc = {radius_force_reference_kpc}",
    f"radius_force_scan_kpc = [{radius_force_scan_kpc[0]}, ..., {radius_force_scan_kpc[-1]}]",
    f"radius_force_z_samples_kpc = {radius_force_z_samples_kpc.tolist()}",
    f"timestamp = {timestamp}",
]

for radius_kpc, color in zip(radii_kpc, colors):
    nu_squared = local_nu_squared_kms2_per_kpc2(radius_kpc, phi_slice_rad, dz_nu_kpc)
    nu_kmskpc = np.sqrt(max(nu_squared, 0.0))
    nu_period_myr = vertical_period_myr_from_omega_kmskpc(nu_kmskpc)

    force_curve = np.array(
        [fz_physical_kms2_per_kpc(radius_kpc, z_val, phi_slice_rad) for z_val in z_force_plot_kpc]
    )
    force_harm = -nu_squared * z_force_plot_kpc

    omega_curve = np.array(
        [vertical_frequency_kmskpc(radius_kpc, zmax_kpc, phi_slice_rad) for zmax_kpc in z_frequency_plot_kpc]
    )
    omega_harm = np.full_like(z_frequency_plot_kpc, nu_kmskpc)
    omega_period_curve_myr = vertical_period_myr_from_omega_kmskpc(omega_curve)

    force_phi_curve = np.array(
        [
            fz_physical_kms2_per_kpc(radius_kpc, angle_force_height_kpc, barphi_rad + phi_offset_rad)
            for phi_offset_rad in phi_scan_rad
        ]
    )
    force_phi_delta_curve = force_phi_curve - force_phi_curve[0]
    omega_phi_curve = np.array(
        [
            vertical_frequency_kmskpc(radius_kpc, angle_frequency_zmax_kpc, barphi_rad + phi_offset_rad)
            for phi_offset_rad in phi_scan_rad
        ]
    )
    omega_phi_delta_curve = omega_phi_curve - omega_phi_curve[0]

    label = rf"R = {radius_kpc:.1f} kpc"
    ax_force_z.plot(
        z_force_plot_kpc,
        force_curve / 1000.0,
        color=color,
        linewidth=2.3,
        label=f"{label} true",
    )
    ax_force_z.plot(
        z_force_plot_kpc,
        force_harm / 1000.0,
        color=color,
        linewidth=1.8,
        linestyle="--",
        label=f"{label} harmonic",
    )

    ax_frequency_z.plot(
        z_frequency_plot_kpc,
        omega_curve,
        color=color,
        linewidth=2.3,
        label=f"{label} true",
    )
    ax_frequency_z.plot(
        z_frequency_plot_kpc,
        omega_harm,
        color=color,
        linewidth=1.8,
        linestyle="--",
        label=f"{label} harmonic",
    )

    ax_force_phi.plot(
        phi_scan_deg,
        force_phi_delta_curve / 1000.0,
        color=color,
        linewidth=2.1,
        label=label,
    )
    ax_frequency_phi.plot(
        phi_scan_deg,
        omega_phi_delta_curve,
        color=color,
        linewidth=2.1,
        label=label,
    )

    summary_lines.extend(
        [
            f"R_{radius_kpc:.1f}_kpc_nu_squared_kms2_per_kpc2 = {nu_squared}",
            f"R_{radius_kpc:.1f}_kpc_nu_kmskpc = {nu_kmskpc}",
            f"R_{radius_kpc:.1f}_kpc_nu_period_myr = {nu_period_myr}",
            f"R_{radius_kpc:.1f}_kpc_omega_zmax_min_kmskpc = {np.min(omega_curve)}",
            f"R_{radius_kpc:.1f}_kpc_omega_zmax_max_kmskpc = {np.max(omega_curve)}",
            f"R_{radius_kpc:.1f}_kpc_period_zmax_min_myr = {np.min(omega_period_curve_myr)}",
            f"R_{radius_kpc:.1f}_kpc_period_zmax_max_myr = {np.max(omega_period_curve_myr)}",
            f"R_{radius_kpc:.1f}_kpc_delta_force_phi_min_1e3kms2perkpc = {np.min(force_phi_delta_curve / 1000.0)}",
            f"R_{radius_kpc:.1f}_kpc_delta_force_phi_max_1e3kms2perkpc = {np.max(force_phi_delta_curve / 1000.0)}",
            f"R_{radius_kpc:.1f}_kpc_delta_omega_phi_min_kmskpc = {np.min(omega_phi_delta_curve)}",
            f"R_{radius_kpc:.1f}_kpc_delta_omega_phi_max_kmskpc = {np.max(omega_phi_delta_curve)}",
        ]
    )

for z_sample_kpc, color in zip(radius_force_z_samples_kpc, radius_force_colors):
    force_radius_curve = np.array(
        [fz_physical_kms2_per_kpc(radius_kpc, z_sample_kpc, phi_slice_rad) for radius_kpc in radius_force_scan_kpc]
    )
    frequency_radius_curve = np.array(
        [vertical_frequency_kmskpc(radius_kpc, z_sample_kpc, phi_slice_rad) for radius_kpc in radius_force_scan_kpc]
    )
    ax_force_radius.plot(
        radius_force_scan_kpc,
        force_radius_curve / 1000.0,
        color=color,
        linewidth=2.3,
        label=rf"z = {int(round(z_sample_kpc * 1000.0))} pc",
    )
    ax_frequency_radius.plot(
        radius_force_scan_kpc,
        frequency_radius_curve,
        color=color,
        linewidth=2.3,
        label=rf"z = {int(round(z_sample_kpc * 1000.0))} pc",
    )
    reference_force = fz_physical_kms2_per_kpc(radius_force_reference_kpc, z_sample_kpc, phi_slice_rad) / 1000.0
    reference_frequency = vertical_frequency_kmskpc(radius_force_reference_kpc, z_sample_kpc, phi_slice_rad)
    ax_force_radius.scatter([radius_force_reference_kpc], [reference_force], color=color, s=36, zorder=3)
    ax_frequency_radius.scatter(
        [radius_force_reference_kpc], [reference_frequency], color=color, s=36, zorder=3
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

ax_force_z.set_title("Restoring Force vs z", fontsize=TITLE_FONTSIZE)
ax_force_z.set_xlabel("z [kpc]", fontsize=AXIS_LABEL_FONTSIZE)
ax_force_z.set_ylabel(r"$F_z$ [10$^3$ (km/s)$^2$/kpc]", fontsize=AXIS_LABEL_FONTSIZE)
ax_force_z.tick_params(axis="both", labelsize=TICK_LABEL_FONTSIZE)
ax_force_z.set_xlim(np.min(z_force_plot_kpc), np.max(z_force_plot_kpc))
ax_force_z.grid(alpha=0.25, linewidth=0.5)
ax_force_z.legend(fontsize=LEGEND_FONTSIZE, loc="best", ncol=1, frameon=True)

ax_frequency_z.set_title("Vertical Frequency vs z", fontsize=TITLE_FONTSIZE)
ax_frequency_z.set_xlabel(r"$z_{\max}$ [kpc]", fontsize=AXIS_LABEL_FONTSIZE)
ax_frequency_z.set_ylabel(r"$\Omega_z$ [km s$^{-1}$ kpc$^{-1}$]", fontsize=AXIS_LABEL_FONTSIZE)
ax_frequency_z.tick_params(axis="both", labelsize=TICK_LABEL_FONTSIZE)
ax_frequency_z.set_xlim(np.min(z_frequency_plot_kpc), np.max(z_frequency_plot_kpc))
ax_frequency_z.grid(alpha=0.25, linewidth=0.5)
ax_frequency_z.legend(fontsize=LEGEND_FONTSIZE, loc="best", ncol=1, frameon=True)

ax_force_radius.set_title("Restoring Force vs Radius", fontsize=TITLE_FONTSIZE)
ax_force_radius.set_xlabel("R [kpc]", fontsize=AXIS_LABEL_FONTSIZE)
ax_force_radius.set_ylabel(r"$F_z(R,z)$ [10$^3$ (km/s)$^2$/kpc]", fontsize=AXIS_LABEL_FONTSIZE)
ax_force_radius.tick_params(axis="both", labelsize=TICK_LABEL_FONTSIZE)
ax_force_radius.grid(alpha=0.25, linewidth=0.5)
ax_force_radius.axvline(radius_force_reference_kpc, color="0.35", linewidth=0.8, alpha=0.7)
ax_force_radius.legend(fontsize=LEGEND_FONTSIZE, loc="best", frameon=True)

ax_frequency_radius.set_title("Vertical Frequency vs Radius", fontsize=TITLE_FONTSIZE)
ax_frequency_radius.set_xlabel("R [kpc]", fontsize=AXIS_LABEL_FONTSIZE)
ax_frequency_radius.set_ylabel(
    r"$\Omega_z(R,z_{\max})$ [km s$^{-1}$ kpc$^{-1}$]",
    fontsize=AXIS_LABEL_FONTSIZE,
)
ax_frequency_radius.tick_params(axis="both", labelsize=TICK_LABEL_FONTSIZE)
ax_frequency_radius.grid(alpha=0.25, linewidth=0.5)
ax_frequency_radius.axvline(radius_force_reference_kpc, color="0.35", linewidth=0.8, alpha=0.7)
ax_frequency_radius.legend(fontsize=LEGEND_FONTSIZE, loc="best", frameon=True)

ax_force_phi.set_title(
    rf"$\Delta F_z$ vs Angle at z = {int(round(angle_force_height_kpc * 1000.0))} pc",
    fontsize=TITLE_FONTSIZE,
)
ax_force_phi.set_xlabel(r"Angle Relative to Bar [$^\circ$]", fontsize=AXIS_LABEL_FONTSIZE)
ax_force_phi.set_ylabel(
    r"$\Delta F_z(\phi)$ [10$^3$ (km/s)$^2$/kpc]",
    fontsize=AXIS_LABEL_FONTSIZE,
)
ax_force_phi.tick_params(axis="both", labelsize=TICK_LABEL_FONTSIZE)
ax_force_phi.set_xlim(np.min(phi_scan_deg), np.max(phi_scan_deg))
ax_force_phi.grid(alpha=0.25, linewidth=0.5)
ax_force_phi.legend(fontsize=LEGEND_FONTSIZE, loc="best", frameon=True, ncol=1)

ax_frequency_phi.set_title(
    rf"$\Delta \Omega_z$ vs Angle at $z_{{\max}}$ = {int(round(angle_frequency_zmax_kpc * 1000.0))} pc",
    fontsize=TITLE_FONTSIZE,
)
ax_frequency_phi.set_xlabel(r"Angle Relative to Bar [$^\circ$]", fontsize=AXIS_LABEL_FONTSIZE)
ax_frequency_phi.set_ylabel(r"$\Delta \Omega_z(\phi)$ [km s$^{-1}$ kpc$^{-1}$]", fontsize=AXIS_LABEL_FONTSIZE)
ax_frequency_phi.tick_params(axis="both", labelsize=TICK_LABEL_FONTSIZE)
ax_frequency_phi.set_xlim(np.min(phi_scan_deg), np.max(phi_scan_deg))
ax_frequency_phi.grid(alpha=0.25, linewidth=0.5)
ax_frequency_phi.legend(fontsize=LEGEND_FONTSIZE, loc="best", frameon=True, ncol=1)


fig_height.tight_layout()

fig_radius.tight_layout()

fig_angle.tight_layout()

output_dir.mkdir(parents=True, exist_ok=True)
fig_height.savefig(output_dir / f"{output_base}_height_{timestamp}.png", dpi=400, bbox_inches="tight")
fig_radius.savefig(output_dir / f"{output_base}_radius_{timestamp}.png", dpi=400, bbox_inches="tight")
fig_angle.savefig(output_dir / f"{output_base}_azimuth_{timestamp}.png", dpi=400, bbox_inches="tight")

(output_dir / f"{output_base}_summary.txt").write_text(
    "\n".join(summary_lines), encoding="utf-8"
)
plt.show()





