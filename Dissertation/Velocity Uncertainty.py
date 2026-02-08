import pandas as pd
import numpy as np
from astropy.coordinates import SkyCoord, Galactic
import astropy.units as u

# Load Excel file
file_path = "D://Dropbox/Public Documents/UCLAN/AA3050 Dissertation/Kinematics/PL_Vel.xlsx"
df = pd.read_excel(file_path)

# List of required columns
required_columns = [
    'RA', 'RA_err', 'Dec', 'Dec_err',
    'Parallax', 'Parallax_err',
    'PM_RA', 'PM_RA_err', 'PM_Dec', 'PM_Dec_err',
    'RV', 'RV_err'
]

# Drop any rows with missing values in required columns
df = df.dropna(subset=required_columns)

# Constants
k = 4.74047  # Converts mas/yr * pc to km/s

results = []

for _, row in df.iterrows():
    ra, dec = row['RA'], row['Dec']
    parallax = row['Parallax']  # in mas
    parallax_err = row['Parallax_err']  # in mas
    pm_ra, pm_dec = row['PM_RA'], row['PM_Dec']
    rv = row['RV']

    # Uncertainties
    ra_err, dec_err = row['RA_err'], row['Dec_err']
    pm_ra_err, pm_dec_err = row['PM_RA_err'], row['PM_Dec_err']
    rv_err = row['RV_err']

    # Convert parallax to distance (pc)
    d = 1000 / parallax
    d_err = (1000 * parallax_err) / parallax**2

    # Spherical velocity components
    v_ra = k * pm_ra * d / 1000
    v_dec = k * pm_dec * d / 1000
    v_d = rv

    # Spherical velocity uncertainties
    v_ra_err = k * np.sqrt((pm_ra_err * d / 1000)**2 + (pm_ra * d_err / 1000)**2)
    v_dec_err = k * np.sqrt((pm_dec_err * d / 1000)**2 + (pm_dec * d_err / 1000)**2)
    v_d_err = rv_err

    # Create SkyCoord object
    c = SkyCoord(ra=ra*u.deg, dec=dec*u.deg, distance=d*u.pc,
                 pm_ra_cosdec=pm_ra*u.mas/u.yr, pm_dec=pm_dec*u.mas/u.yr,
                 radial_velocity=rv*u.km/u.s)

    gal = c.transform_to(Galactic)
    v_xyz = gal.velocity.d_xyz.to_value(u.km/u.s)

    # Uncertainty propagation using finite differences
    def perturbed_velocity(key, delta):
        p_row = row.copy()
        p_row[key] += delta
        parallax = p_row['Parallax']
        d = 1000 / parallax
        c_pert = SkyCoord(
            ra=p_row['RA']*u.deg, dec=p_row['Dec']*u.deg,
            distance=d*u.pc,
            pm_ra_cosdec=p_row['PM_RA']*u.mas/u.yr,
            pm_dec=p_row['PM_Dec']*u.mas/u.yr,
            radial_velocity=p_row['RV']*u.km/u.s
        ).transform_to(Galactic)
        return c_pert.velocity.d_xyz.to_value(u.km/u.s)

    deltas = {
        'RA': ra_err, 'Dec': dec_err,
        'Parallax': parallax_err,
        'PM_RA': pm_ra_err, 'PM_Dec': pm_dec_err, 'RV': rv_err
    }

    variances = np.zeros(3)
    for key, delta in deltas.items():
        v_plus = np.array(perturbed_velocity(key, delta))
        v_minus = np.array(perturbed_velocity(key, -delta))
        deriv = (v_plus - v_minus) / 2
        variances += deriv**2

    v_cart_err = np.sqrt(variances)

    results.append({
        "v_RA_err": round(v_ra_err, 2),
        "v_Dec_err": round(v_dec_err, 2),
        "v_Dist_err": round(d_err, 2),
        "U_err": round(v_cart_err[0], 2),
        "V_err": round(v_cart_err[1], 2),
        "W_err": round(v_cart_err[2], 2)
    })

# Output the results
results_df = pd.DataFrame(results)
print(results_df.to_string(index=False))
