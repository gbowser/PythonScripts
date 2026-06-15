"""
Gaia snail schematic: (A) post-perturbation blob in (z, vz),
(B) action–angle annulus (sqrt(Jz), theta_z),
(C) phase-wrapped spiral back in (z, vz).

Produces: gaia_snail_schematic.png and .pdf
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


OUTPUT_DIR = Path(
    r"D:\Dropbox\Public Documents\UCLAN\MSc Research\Erwin\data_driven_astronomy_outputs"
)


def panel_A(ax, rng):
    # Background: faint "constant Ez" ellipses (harmonic guide)
    zmax_list = np.linspace(0.3, 1.6, 6)
    t = np.linspace(0, 2 * np.pi, 400)
    for zmax in zmax_list:
        vzmax = zmax
        z = zmax * np.cos(t)
        vz = vzmax * np.sin(t)
        ax.plot(z, vz, lw=1, alpha=0.18)

    # A lopsided, phase-correlated "blob"
    # Build points near a restricted phase range on a set of ellipses
    n = 2200
    A = rng.uniform(0.35, 1.55, n)  # amplitude proxy
    phi0 = rng.normal(loc=0.6, scale=0.22, size=n)  # restricted phase
    # Add some coherent tilt / asymmetry
    phi0 += 0.12 * (A - A.mean())

    # Harmonic mapping: z=A cos(phi), vz ~ A sin(phi) with mild scatter
    z = A * np.cos(phi0) + rng.normal(0, 0.05, n)
    vz = A * np.sin(phi0) + rng.normal(0, 0.06, n)

    ax.scatter(z, vz, s=4, alpha=0.45, linewidths=0)

    ax.set_title("A. Immediately after a vertical perturbation")
    ax.set_xlabel(r"$z$  (arbitrary units)")
    ax.set_ylabel(r"$v_z$  (arbitrary units)")
    ax.axhline(0, lw=1, alpha=0.25)
    ax.axvline(0, lw=1, alpha=0.25)
    ax.set_aspect("equal", adjustable="box")
    ax.text(
        0.02,
        0.98,
        "Non-uniform phase\n(coherent ‘blob’)",
        transform=ax.transAxes,
        va="top",
        ha="left",
    )


def panel_B(ax, rng):
    # Draw a true annulus in Cartesian axes using (r, theta) -> (x, y)
    ax.set_title("B. In vertical action–angle variables")
    ax.set_xlabel(r"$\sqrt{J_z}\cos\theta_z$")
    ax.set_ylabel(r"$\sqrt{J_z}\sin\theta_z$")
    ax.set_xlim(-1.8, 1.8)
    ax.set_ylim(-1.8, 1.8)
    ax.set_aspect("equal", adjustable="box")

    # "Initial sector": theta clustered, radius spanning
    n = 2200
    r = rng.uniform(0.35, 1.55, n)  # proxy ~ sqrt(Jz)
    theta = rng.normal(loc=0.35 * np.pi, scale=0.22, size=n)
    theta = np.clip(theta, -np.pi, np.pi)

    x = r * np.cos(theta)
    y = r * np.sin(theta)
    ax.scatter(x, y, s=4, alpha=0.45, linewidths=0)

    # Guide circles for r and rays for theta
    tt = np.linspace(0, 2 * np.pi, 400)
    for rr in [0.35, 0.7, 1.05, 1.4]:
        ax.plot(rr * np.cos(tt), rr * np.sin(tt), lw=1, alpha=0.15)
    for th in [-np.pi / 2, 0, np.pi / 2, np.pi]:
        ax.plot([0, 1.65 * np.cos(th)], [0, 1.65 * np.sin(th)], lw=1, alpha=0.15)

    # Put the core relation on the panel
    ax.text(
        0.02,
        0.02,
        r"$\theta_z(t)=\theta_z(0)+\Omega_z(J_z,L_z)\,t$"
        "\n"
        r"if $\Omega_z$ depends on $J_z$ $\Rightarrow$ differential rotation",
        transform=ax.transAxes,
        va="bottom",
        ha="left",
    )


def panel_C(ax, rng):
    # Background ellipses again
    zmax_list = np.linspace(0.3, 1.6, 6)
    t = np.linspace(0, 2 * np.pi, 400)
    for zmax in zmax_list:
        vzmax = zmax
        z = zmax * np.cos(t)
        vz = vzmax * np.sin(t)
        ax.plot(z, vz, lw=1, alpha=0.18)

    # Start from the same kind of initial distribution, but "evolve" theta by a Jz-dependent frequency
    n = 3200
    A = rng.uniform(0.35, 1.55, n)  # amplitude proxy ~ sqrt(Jz)
    theta0 = rng.normal(loc=0.6, scale=0.22, size=n)
    theta0 += 0.12 * (A - A.mean())

    # Model a frequency that depends on amplitude (anharmonic) and add a mild spread
    # (This is just a cartoon; sign/shape chosen to generate visible winding.)
    Omega0 = 2.0
    Omega = Omega0 * (1.0 + 0.45 * (A - A.mean())) + rng.normal(0, 0.05, n)

    # Choose a time such that multiple wraps appear
    t_evolve = 2.7
    theta = theta0 + Omega * t_evolve

    # Map back to (z, vz)
    z = A * np.cos(theta) + rng.normal(0, 0.03, n)
    vz = A * np.sin(theta) + rng.normal(0, 0.035, n)

    ax.scatter(z, vz, s=4, alpha=0.45, linewidths=0)

    ax.set_title("C. Differential winding produces the spiral")
    ax.set_xlabel(r"$z$  (arbitrary units)")
    ax.set_ylabel(r"$v_z$  (arbitrary units)")
    ax.axhline(0, lw=1, alpha=0.25)
    ax.axvline(0, lw=1, alpha=0.25)
    ax.set_aspect("equal", adjustable="box")
    ax.text(
        0.02,
        0.98,
        r"$\Delta\theta_z \approx [\Omega_z(J_{z,2})-\Omega_z(J_{z,1})]\,t$",
        transform=ax.transAxes,
        va="top",
        ha="left",
    )


def make_figure(seed=7, outfile_base=OUTPUT_DIR / "gaia_snail_schematic"):
    rng = np.random.default_rng(seed)
    outfile_base = Path(outfile_base)
    outfile_base.parent.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.8), constrained_layout=True)

    panel_A(axes[0], rng)
    panel_B(axes[1], rng)
    panel_C(axes[2], rng)

    fig.suptitle(
        "Action–angle interpretation of the Gaia phase-space spiral (schematic)", y=1.03
    )

    fig.savefig(outfile_base.with_suffix(".png"), dpi=250, bbox_inches="tight")
    fig.savefig(outfile_base.with_suffix(".pdf"), bbox_inches="tight")
    plt.show()


if __name__ == "__main__":
    make_figure()
