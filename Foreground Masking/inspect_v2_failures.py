import pandas as pd
p=r'D:\Dropbox\Public Documents\UCLAN\MSc Research\Euclid\Euclid_MER_VIS_geometry_v2\MER_VIS_local_geometry_manifest.csv'
d=pd.read_csv(p,dtype={'object_id':str});print(d.loc[d.codex_fit_status.eq('fit_failed'),['object_id','codex_error','codex_n_good','codex_method']].to_string(index=False))
