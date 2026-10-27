import csv,math,json,statistics
from pathlib import Path
p=Path(r'C:\Users\gordo\Documents\Github\PythonScripts\Euclid\datalabs_MER_VIS\MER_VIS_geometry_comparison_manifest.csv')
rows=list(csv.DictReader(p.open(encoding='utf-8-sig')))
def num(r,k):
 try:
  v=float(r[k]);return v if math.isfinite(v) else None
 except:return None
pairs=[]
for r in rows:
 a=num(r,'zenodo_bar_any_fraction');b=num(r,'euclid_zoobot_bar_any_fraction')
 if a is not None and b is not None:pairs.append((a,b,r))
d=[b-a for a,b,r in pairs];sd=sorted(d)
def percentile(q):
 x=(len(sd)-1)*q;lo=int(x);hi=min(lo+1,len(sd)-1);return sd[lo]+(x-lo)*(sd[hi]-sd[lo])
out=dict(total=len(rows),unique_ids=len(set(r['object_id'] for r in rows)),main_matches=sum(r['euclid_main_match'].lower()=='true' for r in rows),morphology_matches=sum(r['euclid_morphology_match'].lower()=='true' for r in rows),valid_pairs=len(pairs),unavailable=len(rows)-len(pairs),euclid_bar_ge_08=sum(b>=.8 for a,b,r in pairs),euclid_bar_lt_08=sum(b<.8 for a,b,r in pairs),median_euclid_minus_zenodo=statistics.median(d),mean_absolute_difference=statistics.mean(abs(x) for x in d),percentile5_difference=percentile(.05),percentile95_difference=percentile(.95),max_abs_difference=max(abs(x) for x in d),checks_dates=sorted(set(r['catalogue_checked_utc'][:10] for r in rows)),versions=sorted(set(r['zenodo_version_ordinal'] for r in rows)))
out['largest_disagreements']=[dict(object_id=r['object_id'],zenodo=a,euclid=b,difference=b-a) for a,b,r in sorted(pairs,key=lambda p:abs(p[1]-p[0]),reverse=True)[:3]]
print(json.dumps(out,indent=2))
