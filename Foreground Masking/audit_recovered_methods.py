import pandas as pd
p='MER_VIS_external_comparison/galaxy_by_galaxy_comparison.csv';m=pd.read_csv(p,dtype={'object_id':str});r=m[m.codex_fit_status.eq('fit_failed')].copy()
r['failure_group']=r.codex_error.fillna('').apply(lambda x:'Interval' if 'Insufficient bar/disc' in x else 'Short profile' if 'reliable isophotes' in x else 'Centre')
print(pd.crosstab(r.failure_group,r.method).to_string())
print('Recovered bar classes');print(pd.crosstab(r.failure_group,r.bar_quality).to_string())
print('Recovered counts');print(r.groupby('failure_group').agg(n=('object_id','size'),median_good=('n_good','median'),min_good=('n_good','min'),median_disc=('n_disc_ellipses','median')).to_string())
print('Supplied good<10',m.loc[m.status.eq('ok') & (m.n_good<10),['object_id','n_good','method']].to_string(index=False))
