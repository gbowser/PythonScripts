import pandas as pd
p=r'D:\Dropbox\Public Documents\UCLAN\MSc Research\Euclid\Euclid_MER_VIS_geometry_v2\MER_VIS_local_geometry_manifest.csv';d=pd.read_csv(p);f=d[d.codex_fit_status.eq('provisional_fit')]
print('Completed',len(d),'fits',len(f),'failures',len(d)-len(f));print('Methods',f.codex_method.value_counts().to_dict());print('Centre offset arcsec',f.codex_centre_offset_arcsec.quantile([.5,.9,.99,1]).to_dict());print('Clean',f.codex_quality_flags.isna().sum())
