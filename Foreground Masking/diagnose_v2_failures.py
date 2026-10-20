import pandas as pd
from pathlib import Path
base=Path(r'D:\Dropbox\Public Documents\UCLAN\MSc Research\Euclid\Euclid_MER_VIS_geometry_v2/profiles')
for oid in ['-586374330510251740','-611842176499414781','-584896980492699093']:
 p=base/f'Euclid_{oid}_MER_VIS_ellipse_profile.csv';d=pd.read_csv(p);print(oid,len(d));print(d[['ellipticity','stop_code','ellipticity_error','pa_error_deg','sampled_fraction','centre_offset_fit_pix','sma_fit_pix']].describe().round(2).to_string())
