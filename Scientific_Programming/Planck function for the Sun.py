import matplotlib.pyplot as plt
import numpy as np

# Physical constants in SI units.
planck_constant = 6.62607015e-34
speed_of_light = 2.99792458e8
boltzmann_constant = 1.380649e-23

# Surface temperature of the Sun, in kelvin.
temperature = 5778

# Create a NumPy array of wavelengths from 100 nm to 5000 nm.
# The formula uses metres, so we convert from nanometres to metres.
wavelength_nm = np.linspace(100, 5000, 2000)
wavelength_m = wavelength_nm * 1e-9

# Calculate the Planck function B(lambda) for each wavelength.
# This gives the spectral radiance of a black body at 5778 K.
spectral_radiance = (
    2
    * planck_constant
    * speed_of_light**2
    / wavelength_m**5
    / (
        np.exp(
            planck_constant
            * speed_of_light
            / (wavelength_m * boltzmann_constant * temperature)
        )
        - 1
    )
)

# Find the wavelength where the spectral radiance is largest.
peak_index = np.argmax(spectral_radiance)
peak_wavelength_nm = wavelength_nm[peak_index]
peak_radiance = spectral_radiance[peak_index]

fig, ax = plt.subplots()
ax.plot(wavelength_nm, spectral_radiance)
ax.axvline(
    peak_wavelength_nm,
    color="crimson",
    linestyle="--",
    label=f"Peak at {peak_wavelength_nm:.0f} nm",
)
ax.plot(peak_wavelength_nm, peak_radiance, "o", color="crimson")
ax.set_xlim(4000, 0)
ax.set_xlabel("Wavelength (nm)")
ax.set_ylabel(r"Spectral radiance, $B(\lambda)$ (W m$^{-3}$ sr$^{-1}$)")
ax.set_title("Planck Function for the Sun (T = 5778 K)")
ax.grid(True)
ax.legend()

plt.show()
