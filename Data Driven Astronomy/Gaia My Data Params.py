# https://www.cosmos.esa.int/web/gaia-users/archive/use-cases#ClusterAnalysisPythonTutorial

# This code shows how to retrieve the different DataLink
# products associated to a sample of stars associated to the Pleiades open cluster.

from astroquery.gaia import Gaia
output_file_name="Gaia Test2.vot.gz"

radius = 1.0  # Degrees
inp_ra = 56.87125  # Degrees
inp_dec = 24.10493  # Degrees
mystar="Gaia DR3 68828225308044288"

query=f"SELECT gaia_source.designation,gaia_source.ra,gaia_source.dec FROM gaiadr3.gaia_source WHERE gaia.source.designation=mystar" 

job = Gaia.launch_job_async(query, dump_to_file="true", output_file=output_file_name,output_format="votable_gzip")

results = job.get_results()
print(f"Table size (rows): {len(results)}")
print(results)
df = results.to_pandas()

df.to_csv("mydata-specific-params.csv")

#  gaia_source.radial_velocity, gaia_source.teff_gspphot , gaia_source.radius_gspphot 

#  query = f"SELECT gaia_source.ra, gaia_source.dec, gaia_source.parallax FROM gaiadr3.gaia_source WHERE DISTANCE(POINT({inp_ra}, {inp_dec}),POINT(ra, dec)) < {radius} AND ruwe  < 1.5 AND parallax_over_error >10"
#  query = f"SELECT * FROM gaiadr3.gaia_source WHERE DISTANCE(POINT({inp_ra}, {inp_dec}),POINT(ra, dec)) < {radius} AND ruwe  < 1.5 AND parallax_over_error >10"
#   gaiadr3.astrophysical_parameters.mass_flame WHERE designation="Gaia DR3 68828225308044288"
