# https://www.cosmos.esa.int/web/gaia-users/archive/use-cases#ClusterAnalysisPythonTutorial

# This code shows how to retrieve the different DataLink 
# products associated to a sample of stars associated to the Pleiades open cluster.

import pandas as pd
import astropy.units as u
from astropy.coordinates import SkyCoord
from astroquery.gaia import Gaia

from astropy.table import Table
import numpy as np

radius  = 1.0        # Degrees
inp_ra  = 56.87125   # Degrees
inp_dec = 24.10493   # Degrees

query = f"SELECT * FROM gaiadr3.gaia_source_lite WHERE DISTANCE(POINT({inp_ra}, {inp_dec}),POINT(ra, dec)) < {radius} AND ruwe <1.4 AND parallax_over_error >10"

job     = Gaia.launch_job_async(query)
results = job.get_results()
print(f'Table size (rows): {len(results)}')
df=results.to_pandas()

df.to_csv('mydata.csv')
df.to_parquet('mydata.parquet')