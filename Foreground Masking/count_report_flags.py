import csv,collections,json
p=r'D:\Dropbox\Public Documents\UCLAN\MSc Research\Euclid\Euclid_MER_VIS_geometry\MER_VIS_local_geometry_manifest.csv'
with open(p,encoding='utf-8-sig') as f:r=list(csv.DictReader(f))
c=collections.Counter(len([x for x in a['codex_quality_flags'].split(';') if x.strip()]) for a in r if a['codex_fit_status']=='provisional_fit')
print(dict(sorted(c.items())))
