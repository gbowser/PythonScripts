import pandas as pd
p=r'D:\Dropbox\Public Documents\UCLAN\MSc Research\Euclid\Euclid_MER_VIS_geometry_v2\MER_VIS_local_geometry_manifest.csv'
d=pd.read_csv(p);print(len(d));print(d.codex_bar_status.value_counts());print(d.calculation_seconds.describe())
