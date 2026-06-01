import os

import matplotlib.pyplot as plt
import numpy as np
import scipy.stats as stats

# from photutils.aperture import EllipticalAperture # type: ignore
# from photutils.isophote import Ellipse, EllipseGeometry # type: ignore
from astropy.io import fits
from scipy.signal import butter, filtfilt

output_folder = "D:/Dropbox/Public Documents/UCLAN/MSc Research/Data"


def calc_percentile(window, pct):
    return np.nanpercentile(window, pct)


def butterworth_lowpass(cutoff, fs, order=4):
    """
    cutoff: cutoff frequency in Hz
    fs: sampling frequency in Hz
    order: filter order
    """
    nyq = 0.5 * fs
    normal_cutoff = cutoff / nyq
    b, a = butter(order, normal_cutoff, btype="low", analog=False)
    return b, a


def smooth_profile(data, cutoff, fs, order):

    b, a = butterworth_lowpass(cutoff, fs, order)
    filtered = filtfilt(b, a, data)  # zero-phase filtering

    return filtered


def adaptive_gaussian_smooth(x, y, smooth_scale):
    """
    Adaptive Gaussian smoothing for unevenly sampled 1D data.

    Parameters
    ----------
    x : 1D array
        Independent variable (position)
    y : 1D array
        Dependent variable (profile to smooth)
    smooth_scale : float or 1D array
        Smoothing scale in same units as x. Can be scalar or array of length len(x)

    Returns
    -------
    y_smooth : 1D array
        Smoothed profile
    """
    y_smooth = np.zeros_like(y)
    x = np.asarray(x)
    y = np.asarray(y)

    # ensure smooth_scale is array
    if np.isscalar(smooth_scale):
        sigma = np.full_like(x, smooth_scale)
    else:
        sigma = np.asarray(smooth_scale)

    for i in range(len(x)):
        # Gaussian weights centered at x[i]
        w = np.exp(-0.5 * ((x - x[i]) / sigma[i]) ** 2)
        y_smooth[i] = np.sum(w * y) / np.sum(w)

    return y_smooth


def plot_rotated_coords(data_shape, origin, angle_deg):

    # Parameters:
    # - data: 2D numpy array (e.g., velocity map)
    # - angle_deg: Rotation angle in degrees (clockwise)

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


def kinematics_maps(
    name_file,
    name_image,
    name_out,
    galaxy,
    PA_disc,
    inc_disc,
    PA_bar,
    vsyst,
    distance,
    VLIM,
    SMIN,
    SMAX,
    origin,
    slice_width,
    cutoff=None,
    fs=None,
    order=None,
    fig_maps=True,
    fig_profile=True,
    Rbar=1.0,
    bins1d=100,
    xlims=(-1.5, 1.5),
):
    """
    Docstring for kinematics_maps

    :param name_file: name of the kinematics file (.fits)
    :param name_image: name of the image (.fits)
    :param name_out: name of the output image
    :param galaxy: name of the target galaxy
    :param PA_disc: Position Angle of the disk (from y-axis counterclockwise)
    :param inc_disc: Inclination
    :param PA_bar: Position Angle of the bar (from y-axis counterclockwise)
    :param vsyst: if needed, systemic velocity
    :param distance: Distance in Mpc
    :param VLIM: Limit on colorbar for velocity
    :param SMIN: Limit on colorbar for sigma (minimum)
    :param SMAX: Limit on colorbar for sigma (maximum)
    :param origin: centre coordinates in pixel
    :param slice_width: width of the slice to extract the profile (expressed in kpc)
    :param cutoff, fs, order: only define for butterworth_lowpass filter
    :param fig_maps/fig_profile: True or False to activate/deactivate
    """

    print()

    file_kin = fits.open(name_file, ignore_missing_simple=True)
    image = fits.open(name_image, ignore_missing_simple=True)[1].data

    bin = file_kin["BIN_ID"].data
    vlos = file_kin["V_STARS"].data - vsyst
    sigmalos = file_kin["SIGMA_STARS"].data

    err_vlos = file_kin["FORM_ERR_V_STARS"].data
    err_sigmalos = file_kin["FORM_ERR_SIGMA_STARS"].data

    zmin, zmax = 3 * 1e3, np.nanmax(image)

    # Rotate points to have galaxy disc parallel to X axis
    x_rot, y_rot = plot_rotated_coords(vlos.shape, origin, PA_disc - 90)

    # From Mpc to kpc via the pixel scale
    # Position defined in pixels; 0.2 for MUSE (0.2 arcsec per pixel)
    # Distance must be in Mpc
    scale_pixel_to_kpc = 0.2 * (distance * 1e3) / 206265.0
    # print(scale_pixel_to_kpc)

    # Select datapoint along disc major axis (parallel to x-axis)
    slice_width_pixel = slice_width / scale_pixel_to_kpc
    ind = abs(y_rot) < slice_width_pixel / 2

    bin_slice = bin[ind]
    x_slice = x_rot[ind]
    v_slice = vlos[ind]
    err_v_slice = err_vlos[ind]
    sigma_slice = sigmalos[ind]
    err_sigma_slice = err_sigmalos[ind]
    flux_slice = image[ind]

    # discretize data: MAJOR AXIS
    ubin = np.unique(bin_slice[~np.isnan(bin_slice)])
    X = np.zeros((ubin.shape))
    V, ERR_V = np.zeros((ubin.shape)), np.zeros((ubin.shape))
    S, ERR_S = np.zeros((ubin.shape)), np.zeros((ubin.shape))
    FLUX = np.zeros((ubin.shape))

    for i in range(len(ubin)):
        index = np.where(bin_slice == ubin[i])[0]  # extract indices array

        if len(index) == 0:
            # No data points in bin: assign NaNs
            X[i] = V[i] = ERR_V[i] = S[i] = ERR_S[i] = FLUX[i] = np.nan

        else:
            idx = index[0]
            # Multiple points: calculate mean/std
            X[i] = (x_slice[index][0] + x_slice[index][-1]) / 2
            V[i] = v_slice[idx]
            ERR_V[i] = err_v_slice[idx]
            S[i] = sigma_slice[idx]
            ERR_S[i] = err_sigma_slice[idx]
            FLUX[i] = flux_slice[idx]

    ind = np.argsort(X)
    X = X[ind]
    V = V[ind]
    ERR_V = ERR_V[ind]
    S = S[ind]
    ERR_S = ERR_S[ind]
    F = np.log10(FLUX[ind])

    # for the plot
    CMAP = "coolwarm"

    levels = np.geomspace(zmin, zmax, 25)
    SK = 0.75
    LW = 0.4

    # Show data within our chosen limits of the bar
    mask = (X < xlims[1] / scale_pixel_to_kpc) & (X > xlims[0] / scale_pixel_to_kpc)
    X = X[mask]
    S = S[mask]
    F = F[mask]
    ERR_S = ERR_S[mask]
    V = V[mask]
    ERR_V = ERR_V[mask]

    DeltaPA = abs(PA_disc - PA_bar)
    print("Delta PA (disc-bar): ", DeltaPA - 90)

    xticks = np.asarray(np.linspace(np.min(x_rot), np.max(x_rot), 7), dtype="int")
    yticks = np.asarray(np.linspace(np.min(y_rot), np.max(y_rot), 7), dtype="int")

    fs = 20

    if fig_maps == True:
        # KINEMATIC MAPS, ALL MOMENTS

        ratio = image.shape[0] / image.shape[1]
        fig_kin = plt.figure(figsize=(15, 15 * ratio))
        plt.suptitle(
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

        ax1 = fig_kin.add_subplot(221)
        plt.axline(
            (0, 0),
            slope=np.tan(np.radians(DeltaPA)),
            color="k",
            lw=3,
            ls=":",
            zorder=+20,
        )
        plt.title(r" $V_{\rm LOS}$", fontsize=fs)
        c = ax1.pcolormesh(
            x_rot, y_rot, vlos, shading="auto", cmap="coolwarm", vmin=-VLIM, vmax=+VLIM
        )
        cbar = plt.colorbar(c, ax=ax1, label="[km/s]", shrink=SK)
        cbar.ax.tick_params(labelsize=16)
        cbar.ax.yaxis.label.set_size(18)
        contours = ax1.contour(
            x_rot, y_rot, image, levels=levels, colors="k", linewidths=LW
        )
        plt.fill_between(
            [np.min(x_rot), np.max(x_rot)],
            -slice_width_pixel / 2,
            +slice_width_pixel / 2,
            color="k",
            alpha=0.5,
        )
        plt.tick_params(labelsize=fs)
        plt.xlabel(" X (kpc)", fontsize=fs)
        plt.ylabel(" Y (kpc)", fontsize=fs)
        plt.xticks(xticks, labels=np.round(xticks * scale_pixel_to_kpc, 1))
        plt.yticks(yticks, labels=np.round(yticks * scale_pixel_to_kpc, 1))
        ax1.set_aspect("equal")

        ax2 = fig_kin.add_subplot(222)
        plt.axline(
            (0, 0),
            slope=np.tan(np.radians(DeltaPA)),
            color="k",
            lw=3,
            ls=":",
            zorder=+20,
        )
        plt.title(r" $\sigma_{\rm LOS}$ ", fontsize=fs)
        c = ax2.pcolormesh(
            x_rot,
            y_rot,
            sigmalos,
            shading="auto",
            cmap="coolwarm",
            vmin=SMIN,
            vmax=SMAX,
        )

        cbar = plt.colorbar(c, ax=ax2, label="[km/s]", shrink=SK)
        cbar.ax.tick_params(labelsize=16)
        cbar.ax.yaxis.label.set_size(18)
        contours = ax2.contour(
            x_rot, y_rot, image, levels=levels, colors="k", linewidths=LW
        )
        plt.fill_between(
            [np.min(x_rot), np.max(x_rot)],
            -slice_width_pixel / 2,
            +slice_width_pixel / 2,
            color="k",
            alpha=0.5,
        )
        plt.tick_params(labelsize=fs)
        plt.xlabel(" X (kpc)", fontsize=fs)
        plt.ylabel(" Y (kpc)", fontsize=fs)
        plt.xticks(xticks, labels=np.round(xticks * scale_pixel_to_kpc, 1))
        plt.yticks(yticks, labels=np.round(yticks * scale_pixel_to_kpc, 1))
        ax2.set_aspect("equal")

        ax1 = fig_kin.add_subplot(223)
        plt.axline(
            (0, 0),
            slope=np.tan(np.radians(DeltaPA)),
            color="k",
            lw=3,
            ls=":",
            zorder=+20,
        )
        plt.title(r" Errors on $V_{\rm LOS}$", fontsize=fs)
        c = ax1.pcolormesh(
            x_rot, y_rot, err_vlos, shading="auto", cmap="coolwarm", vmin=0, vmax=20
        )
        cbar = plt.colorbar(c, ax=ax1, label="[km/s]", shrink=SK)
        cbar.ax.tick_params(labelsize=16)
        cbar.ax.yaxis.label.set_size(18)
        contours = ax1.contour(
            x_rot, y_rot, image, levels=levels, colors="k", linewidths=LW
        )
        plt.fill_between(
            [np.min(x_rot), np.max(x_rot)],
            -slice_width_pixel / 2,
            +slice_width_pixel / 2,
            color="k",
            alpha=0.5,
        )
        plt.tick_params(labelsize=fs)
        plt.xlabel("X (kpc)", fontsize=fs)
        plt.ylabel("Y (kpc)", fontsize=fs)
        plt.xticks(xticks, labels=np.round(xticks * scale_pixel_to_kpc, 1))
        plt.yticks(yticks, labels=np.round(yticks * scale_pixel_to_kpc, 1))
        ax1.set_aspect("equal")

        ax2 = fig_kin.add_subplot(224)
        plt.axline(
            (0, 0),
            slope=np.tan(np.radians(DeltaPA)),
            color="k",
            lw=3,
            ls=":",
            zorder=+20,
        )
        plt.title(r" Errors on $\sigma_{\rm LOS}$ ", fontsize=fs)
        c = ax2.pcolormesh(
            x_rot, y_rot, err_sigmalos, shading="auto", cmap="coolwarm", vmin=0, vmax=20
        )
        cbar = plt.colorbar(c, ax=ax2, label="[km/s]", shrink=SK)
        cbar.ax.tick_params(labelsize=16)
        cbar.ax.yaxis.label.set_size(18)
        contours = ax2.contour(
            x_rot, y_rot, image, levels=levels, colors="k", linewidths=LW
        )
        plt.fill_between(
            [np.min(x_rot), np.max(x_rot)],
            -slice_width_pixel / 2,
            +slice_width_pixel / 2,
            color="k",
            alpha=0.5,
        )
        plt.tick_params(labelsize=fs)
        plt.xlabel(" X (kpc)", fontsize=fs)
        plt.ylabel(" Y (kpc)", fontsize=fs)
        plt.xticks(xticks, labels=np.round(xticks * scale_pixel_to_kpc, 1))
        plt.yticks(yticks, labels=np.round(yticks * scale_pixel_to_kpc, 1))
        ax2.set_aspect("equal")

        plt.tight_layout()
        plt.savefig("Kinematic_maps_" + name_out + ".jpg", dpi=250)

    if fig_profile == True:
        ms = 10

        flabel = r"$\log(\mu$ $[10^{-16}$ erg s$^{-1}$ cm$^{-2}])$"
        Rbar_err_pct = 0.15
        strd = 10

        fig, axes = plt.subplots(nrows=3, ncols=1, figsize=(10, 12), sharex=True)
        ax1, ax2, ax3 = axes[0], axes[1], axes[2]
        ax3t = ax3.twinx()

        # Profile along disc axis
        SK = 0.95

        # ax1.set_title(r' $V_{\rm LOS}$', fontsize=fs)
        # sc1 = ax1.scatter(X, V, c=V, s=15, cmap=CMAP, vmin=-VLIM, vmax=+VLIM, edgecolors ='k', zorder=+10)

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

        # sc1 = ax1.scatter(bin_middles, F_all, c='yellow', s=ms, edgecolors ='k', zorder=+10, rasterized=True)
        sc1 = ax1.scatter(
            X[::strd],
            F[::strd],
            c="yellow",
            s=ms,
            edgecolors="k",
            zorder=+10,
            rasterized=True,
        )

        ax1.plot(bin_middles, F_all, c="k", lw=3.0, ls="-", zorder=20)
        ax1.plot(bin_middles, F_all, c="w", lw=1.0, ls="-", zorder=20)
        ax1.fill_between(bin_middles, F_all16, F_all84, color="grey", alpha=0.3)

        # window_size = ws
        # running_median_F = median_filter(F, size=window_size)
        # ax1.plot(X, running_median_F, c='k', lw=3., ls='-', zorder=20)
        # ax1.plot(X, running_median_F, c='w', lw=1., ls='-', zorder=20)

        # cbar = plt.colorbar(sc1, label='[km/s]', shrink=SK)
        # cbar.ax.tick_params(labelsize=16)
        # cbar.ax.yaxis.label.set_size(18)

        # Bar radius
        ax1.axvline(Rbar / scale_pixel_to_kpc, c="k", ls="--", lw=2.0)
        ax1.axvline(-Rbar / scale_pixel_to_kpc, c="k", ls="--", lw=2.0)

        # ax1.fill_between(X, V-ERR_V, V+ERR_V, color='grey', alpha=0.3)
        # plt.errorbar(X, V, yerr=ERR_V, fmt='+k', capsize=5)
        ax1.tick_params(labelsize=fs)
        # ax1.set_xlabel(' X [kpc]', fontsize=fs)
        ax1.set_ylabel(flabel, fontsize=fs)
        # ax1.set_ylim(0, 5e5)

        ax1.set_xticks(xticks, labels=np.round(xticks * scale_pixel_to_kpc, 1))
        ax1.grid()

        # ax2.set_title(r' $\sigma_{\rm LOS}$ [km/s]', fontsize=fs)
        sc2 = ax2.scatter(
            X[::strd],
            S[::strd],
            c="cyan",
            s=ms,
            edgecolors="k",
            zorder=+10,
            rasterized=True,
        )

        S_bins = stats.binned_statistic(X, S, "median", bins=bins1d)
        bin_middles = F_bins.bin_edges[:-1] + np.diff(F_bins.bin_edges) / 2
        S_all = S_bins.statistic.T

        S_bins16 = stats.binned_statistic(
            X, S, statistic=lambda y: np.nanpercentile(y, 16), bins=bins1d
        )
        S_all16 = S_bins16.statistic.T
        S_bins84 = stats.binned_statistic(
            X, S, statistic=lambda y: np.nanpercentile(y, 84), bins=bins1d
        )
        S_all84 = S_bins84.statistic.T

        # Calculate Running Median using SciPy
        # size must be an odd integer for best results
        # window_size = ws
        # running_median_S = median_filter(S, size=window_size)

        # Calculate 16th percentile
        # running_p16 = generic_filter(
        #     S,
        #     lambda window: calc_percentile(window, 16),
        #     size=window_size,
        #     mode='constant',
        #     cval=np.nan
        # )
        # running_p84 = generic_filter(
        #     S,
        #     lambda window: calc_percentile(window, 84),
        #     size=window_size,
        #     mode='constant',
        #     cval=np.nan
        # )

        # ax2.plot(X, running_median_S, c='r', lw=2., ls='-', zorder=20)
        ax2.plot(bin_middles, S_all, c="r", lw=2.0, ls="-", zorder=20)
        ax2.fill_between(bin_middles, S_all16, S_all84, color="r", alpha=0.3)

        # ax2.plot(X, running_p16, c='r', lw=2., ls='-', zorder=20, alpha=0.75)
        # ax2.plot(X, running_p84, c='r', lw=2., ls='-', zorder=20, alpha=0.75)

        # Bar radius
        ax2.axvline(-Rbar / scale_pixel_to_kpc, c="k", ls="--", lw=2.0)
        ax2.axvline(Rbar / scale_pixel_to_kpc, c="k", ls="--", lw=2.0)

        # cbar = plt.colorbar(sc2, label='[km/s]', shrink=SK)
        # cbar.ax.tick_params(labelsize=16)
        # cbar.ax.yaxis.label.set_size(18)

        ax2.fill_between(X, S - ERR_S, S + ERR_S, color="grey", alpha=0.3)
        # plt.errorbar(X, S, yerr=ERR_S, fmt='+k', capsize=5)
        ax2.tick_params(labelsize=fs)
        ax2.set_ylabel(r" $\sigma_{\rm LOS}$ [km/s]", fontsize=fs)
        ax2.set_ylim(SMIN - 5, SMAX + 5)
        ax2.set_xticks(xticks, labels=np.round(xticks * scale_pixel_to_kpc, 1))
        ax2.grid()

        # ax3.plot(X, running_median_F, c='k', lw=3., ls='-', zorder=20)
        # ax3.plot(X, running_median_F, c='w', lw=1., ls='-', zorder=20)

        ax3.plot(bin_middles, F_all, c="k", lw=3.0, ls="-", zorder=20)
        ax3.plot(bin_middles, F_all, c="w", lw=1.0, ls="-", zorder=20)
        ax3.fill_between(bin_middles, F_all16, F_all84, color="grey", alpha=0.3)

        # ax3t.plot(X, running_median_S, c='r', lw=2., ls='-', zorder=20)
        ax3t.plot(bin_middles, S_all, c="r", lw=2.0, ls="-", zorder=20)
        ax3t.fill_between(bin_middles, S_all16, S_all84, color="r", alpha=0.3)

        # Calculate the shaded area boundaries for 20% bar radius uncertainty
        left_bound = Rbar / scale_pixel_to_kpc * (1 - Rbar_err_pct)
        right_bound = Rbar / scale_pixel_to_kpc * (1 + Rbar_err_pct)
        left_bound_ = -Rbar / scale_pixel_to_kpc * (1 - Rbar_err_pct)
        right_bound_ = -Rbar / scale_pixel_to_kpc * (1 + Rbar_err_pct)

        ax3.axvspan(left_bound_, right_bound_, color="gray", alpha=0.3)
        ax3.axvline(-Rbar / scale_pixel_to_kpc, c="k", ls="--", lw=2.0)

        ax3.axvspan(left_bound, right_bound, color="gray", alpha=0.3)
        ax3.axvline(Rbar / scale_pixel_to_kpc, c="k", ls="--", lw=2.0)
        ax3.set_ylabel(flabel, fontsize=fs)
        ax3.set_xlabel(r"$x$ [kpc]", fontsize=fs)
        ax3t.set_ylabel(r" $\sigma_{\rm LOS}$ [km/s]", fontsize=fs, color="r")
        ax3t.set_ylim(SMIN - 5, SMAX + 5)
        ax3.tick_params(labelsize=fs)
        ax3t.tick_params(labelsize=fs, colors="r")
        ax3.grid()

        ax1.set_xlim(xlims[0] / scale_pixel_to_kpc, xlims[1] / scale_pixel_to_kpc)
        ax2.set_xlim(xlims[0] / scale_pixel_to_kpc, xlims[1] / scale_pixel_to_kpc)
        ax3.set_xlim(xlims[0] / scale_pixel_to_kpc, xlims[1] / scale_pixel_to_kpc)

        fig.suptitle(galaxy, fontsize=fs + 5)

        plt.tight_layout()
        fig.subplots_adjust(hspace=0.0)
        fig.align_ylabels()

        fig.savefig(
            os.path.join(output_folder, "Obs_profiles_" + name_out + ".pdf"),
            format="pdf",
        )


# -----------------
# PLOT FOR NGC1300, NGC 3627 and NGC 1566
# -----------------

# NGC 1300
# Bar radius is 85 arcsec (https://articles.adsabs.harvard.edu/cgi-bin/nph-iarticle_query?2000A%26A...361..841A&defaultprint=YES&filetype=.pdf)
# This is 87/0.2 pixels, because MUSE has 0.2 arcsec per pixel, so 435 pixels
os.chdir("D:/Dropbox/Public Documents/UCLAN/MSc Research/Data")

Rbar = 435 * (0.2 * (19.6 * 1e3) / 206265.0)
xlims = (-1.5 * Rbar, 1.5 * Rbar)
kinematics_maps(
    name_file="NGC1300_MAPS_copt_0.89asec.fits",
    name_image="NGC1300_PHANGS_IMAGE_white_copt_0.89asec.fits",
    name_out="NGC1300",
    galaxy="NGC 1300",
    PA_disc=278,
    inc_disc=32,
    PA_bar=99,
    vsyst=0,
    distance=19.6,
    VLIM=250,
    SMIN=0,
    SMAX=140,
    origin=(745.0, 453.0),
    slice_width=Rbar * 0.2,
    Rbar=Rbar,
    fig_maps=False,
    fig_profile=True,
    bins1d=100,
    xlims=xlims,
)
