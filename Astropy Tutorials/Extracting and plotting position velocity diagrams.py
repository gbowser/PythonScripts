import matplotlib.pyplot as plt
from astropy.utils.data import download_file
from spectral_cube import SpectralCube

# set so that these display properly on black backgrounds
plt.rcParams["figure.facecolor"] = "w"
cube_path = download_file(
    "https://www.astropy.org/astropy-data/l1448/l1448_13co.fits",
    cache=True,
)
cube = SpectralCube.read(cube_path)
plt.figure(figsize=(8, 6))
plt.imshow(cube[25].value, origin="lower")
plt.colorbar(label="Intensity")
plt.title("L1448 13CO Channel 25")
plt.tight_layout()
plt.show()
