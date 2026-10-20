import csv,json,collections
with open(r'D:\Dropbox\Public Documents\UCLAN\MSc Research\Euclid\Euclid_MER_VIS_geometry\MER_VIS_local_geometry_manifest.csv',encoding='utf-8-sig') as f:rows=list(csv.DictReader(f))
counts=collections.Counter();flags=collections.Counter();face=0;suppressed=0
for r in rows:
 if r['codex_fit_status']!='provisional_fit':continue
 fs=set(x.strip() for x in r['codex_quality_flags'].split(';') if x.strip())
 if 'nearly_face_on_PA_uncertain' in fs:
  face+=1
  if 'disc_PA_unstable' in fs:suppressed+=1
  fs.discard('disc_PA_unstable')
 fs.discard('nearly_face_on_PA_uncertain')
 counts[len(fs)]+=1;flags.update(fs)
result=dict(multiplicity=dict(sorted(counts.items())),flags=dict(flags),face_on=face,suppressed_disc_pa=suppressed,denominator=2777,fits=2207)
print(json.dumps(result,indent=2));open('MER_VIS_summary_build/face_on_adjusted_chart_counts.json','w').write(json.dumps(result,indent=2))
