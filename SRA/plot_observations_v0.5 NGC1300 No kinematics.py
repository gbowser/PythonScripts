import os

import matplotlib.pyplot as plt
import numpy as np
import scipy.stats as stats
from astropy.io import fits

# output_folder = "D:/Dropbox/Public Documents/UCLAN/MSc Research/Data"
output_folder = "C:\\Users\\gordo\\Dropbox\\Public Documents\\UCLAN\\MSc Research\\Data"


def plot_rotated_coords(data_shape, origin, angle_deg):

    # Parameters:
    # - data_shape: shape of a 2D image or map
    # - angle_deg: rotation angle in degrees (clockwise)

    ny, nx = data_shape
    y, x = np.indices((ny, nx))

    x_center, y_center = origin

    x_shifted = x - x_center
    y_shifted = y - y_center

    # Rotate coordinate grid by -angle (clockwise)
    theta = np.deg2rad(-angle_deg)
    x_rot = x_shifted * np.cos(theta) - y_shifted * np.sin(theta)
    y_rot = x_shifted * np.sin(theta) + y_shifted * np.cos(theta)

    return x_rot, y_rot


def image_profile(
    name_image,
    name_out,
    galaxy,
    PA_disc,
    inc_disc,
    PA_bar,
    distance,
    origin,
    slice_width,
    fig_image=True,
    fig_profile=True,
    Rbar=1.0,
    bins1d=100,
    xlims=(-1.5, 1.5),
):
    """
    Plot the image and extract a major-axis image-flux profile.

    :param name_image: name of the image (.fits)
    :param name_out: name of the output image
    :param galaxy: name of the target galaxy
    :param PA_disc: Position Angle of the disk (from y-axis counterclockwise)
    :param inc_disc: Inclination
    :param PA_bar: Position Angle of the bar (from y-axis counterclockwise)
    :param distance: Distance in Mpc
    :param origin: centre coordinates in pixel
    :param slice_width: width of the slice to extract the profile (expressed in kpc)
    :param fig_image/fig_profile: True or False to activate/deactivate
    """

    print()

    image = fits.open(name_image, ignore_missing_simple=True)[1].data
    positive_image = image[np.isfinite(image) & (image > 0)]
    if positive_image.size == 0:
        raise ValueError("The image contains no positive finite flux values to plot.")

    zmin, zmax = np.nanpercentile(positive_image, [5, 99.5])

    # Rotate points to have galaxy disc parallel to X axis.
    x_rot, y_rot = plot_rotated_coords(image.shape, origin, PA_disc - 90)

    # From Mpc to kpc via the pixel scale.
    # Position defined in pixels; 0.2 for MUSE (0.2 arcsec per pixel).
    scale_pixel_to_kpc = 0.2 * (distance * 1e3) / 206265.0

    # Select image pixels along disc major axis (parallel to x-axis).
    slice_width_pixel = slice_width / scale_pixel_to_kpc
    ind = abs(y_rot) < slice_width_pixel / 2

    x_slice = x_rot[ind]
    flux_slice = image[ind]
    valid = np.isfinite(x_slice) & np.isfinite(flux_slice) & (flux_slice > 0)

    X = x_slice[valid]
    F = np.log10(flux_slice[valid])

    ind = np.argsort(X)
    X = X[ind]
    F = F[ind]

    # Show data within our chosen limits of the bar.
    mask = (X < xlims[1] / scale_pixel_to_kpc) & (X > xlims[0] / scale_pixel_to_kpc)
    X = X[mask]
    F = F[mask]

    DeltaPA = abs(PA_disc - PA_bar)
    print("Delta PA (disc-bar): ", DeltaPA - 90)

    xticks = np.asarray(np.linspace(np.min(x_rot), np.max(x_rot), 7), dtype="int")
    yticks = np.asarray(np.linspace(np.min(y_rot), np.max(y_rot), 7), dtype="int")

    fs = 20
    levels = np.geomspace(zmin, zmax, 25)
    LW = 0.4

    if fig_image == True:
        ratio = image.shape[0] / image.shape[1]
        fig_img = plt.figure(figsize=(15, 15 * ratio))
        ax = fig_img.add_subplot(111)
        fig_img.suptitle(
            galaxy
            + " ,  i="
            + str(inc_disc)
            + r"$^\circ$ , $\Delta$PA="
            + str(np.round(DeltaPA))
            + r"$^\circ$ , slice width="
            + str(np.round(slice_width, 2))
            + " kpc",
            fontsize=20,
        )

        c = ax.pcolormesh(
            x_rot,
            y_rot,
            image,
            shading="auto",
            cmap="gray_r",
            vmin=zmin,
            vmax=zmax,
        )
        cbar = plt.colorbar(c, ax=ax, label="Flux", shrink=0.75)
        cbar.ax.tick_params(labelsize=16)
        cbar.ax.yaxis.label.set_size(18)
        ax.contour(x_rot, y_rot, image, levels=levels, colors="k", linewidths=LW)
        ax.fill_between(
            [np.min(x_rot), np.max(x_rot)],
            -slice_width_pixel / 2,
            +slice_width_pixel / 2,
            color="k",
            alpha=0.5,
        )
        ax.axline(
            (0, 0),
            slope=np.tan(np.radians(DeltaPA)),
            color="k",
            lw=3,
            ls=":",
            zorder=+20,
        )
        ax.tick_params(labelsize=fs)
        ax.set_xlabel(" X (kpc)", fontsize=fs)
        ax.set_ylabel(" Y (kpc)", fontsize=fs)
        ax.set_xticks(xticks, labels=np.round(xticks * scale_pixel_to_kpc, 1))
        ax.set_yticks(yticks, labels=np.round(yticks * scale_pixel_to_kpc, 1))
        ax.set_aspect("equal")

        plt.tight_layout()
        plt.savefig(
            os.path.join(output_folder, "Image_map_" + name_out + ".jpg"),
            dpi=250,
        )

    if fig_profile == True:
        ms = 10

        flabel = r"$\log(\mu$ $[10^{-16}$ erg s$^{-1}$ cm$^{-2}])$"
        Rbar_err_pct = 0.15
        strd = 10

        fig, ax = plt.subplots(figsize=(10, 6))

        F_bins = stats.binned_statistic(X, F, "median", bins=bins1d)
        bin_middles = F_bins.bin_edges[:-1] + np.diff(F_bins.bin_edges) / 2
        F_all = F_bins.statistic.T

        F_bins16 = stats.binned_statistic(
            X, F, statistic=lambda y: np.nanpercentile(y, 16), bins=bins1d
        )
        F_all16 = F_bins16.statistic.T
        F_bins84 = stats.binned_statistic(
            X, F, statistic=lambda y: np.nanpercentile(y, 84), bins=bins1d
        )
        F_all84 = F_bins84.statistic.T

        ax.scatter(
            X[::strd],
            F[::strd],
            c="yellow",
            s=ms,
            edgecolors="k",
            zorder=+10,
            rasterized=True,
        )

        ax.plot(bin_middles, F_all, c="k", lw=3.0, ls="-", zorder=20)
        ax.plot(bin_middles, F_all, c="w", lw=1.0, ls="-", zorder=20)
        ax.fill_between(bin_middles, F_all16, F_all84, color="grey", alpha=0.3)

        left_bound = Rbar / scale_pixel_to_kpc * (1 - Rbar_err_pct)
        right_bound = Rbar / scale_pixel_to_kpc * (1 + Rbar_err_pct)
        left_bound_ = -Rbar / scale_pixel_to_kpc * (1 - Rbar_err_pct)
        right_bound_ = -Rbar / scale_pixel_to_kpc * (1 + Rbar_err_pct)

        ax.axvspan(left_bound_, right_bound_, color="gray", alpha=0.3)
        ax.axvline(-Rbar / scale_pixel_to_kpc, c="k", ls="--", lw=2.0)
        ax.axvspan(left_bound, right_bound, color="gray", alpha=0.3)
        ax.axvline(Rbar / scale_pixel_to_kpc, c="k", ls="--", lw=2.0)

        ax.tick_params(labelsize=fs)
        ax.set_ylabel(flabel, fontsize=fs)
        ax.set_xlabel(r"$x$ [kpc]", fontsize=fs)
        ax.set_xticks(xticks, labels=np.round(xticks * scale_pixel_to_kpc, 1))
        ax.set_xlim(xlims[0] / scale_pixel_to_kpc, xlims[1] / scale_pixel_to_kpc)
        ax.grid()

        fig.suptitle(galaxy, fontsize=fs + 5)

        plt.tight_layout()
        fig.savefig(
            os.path.join(output_folder, "Obs_image_profile_" + name_out + ".pdf"),
            format="pdf",
        )


# -----------------
# PLOT FOR NGC1300, NGC 3627 and NGC 1566
# -----------------

# NGC 1300
# Bar radius is 85 arcsec (https://articles.adsabs.harvard.edu/cgi-bin/nph-iarticle_query?2000A%26A...361..841A&defaultprint=YES&filetype=.pdf)
# This is 87/0.2 pixels, because MUSE has 0.2 arcsec per pixel, so 435 pixels
os.chdir(output_folder)

Rbar = 435 * (0.2 * (19.6 * 1e3) / 206265.0)
xlims = (-1.5 * Rbar, 1.5 * Rbar)
image_profile(
    name_image="NGC1300_PHANGS_IMAGE_white_copt_0.89asec.fits",
    name_out="NGC1300",
    galaxy="NGC 1300",
    PA_disc=278,
    inc_disc=32,
    PA_bar=99,
    distance=19.6,
    origin=(745.0, 453.0),
    slice_width=Rbar * 0.2,
    Rbar=Rbar,
    fig_image=True,
    fig_profile=True,
    bins1d=100,
    xlims=xlims,
)
