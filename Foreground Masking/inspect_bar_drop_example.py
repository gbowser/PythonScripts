import csv,math,statistics,json
from pathlib import Path
root=Path(r'D:\Dropbox\Public Documents\UCLAN\MSc Research\Euclid\Euclid_MER_VIS_geometry');rows={r['object_id']:r for r in csv.DictReader((root/'MER_VIS_local_geometry_manifest.csv').open(encoding='utf-8-sig'))}
for oid in ['-623118358499243253','-639567775462084647']:
 row=rows[oid];ps=list(csv.DictReader((root/'profiles'/f'Euclid_{oid}_MER_VIS_ellipse_profile.csv').open(encoding='utf-8-sig')))
 good=[{k:float(v) if k in ['sma_arcsec','ellipticity','pa_sky_deg'] else v for k,v in r.items()} for r in ps if r['used_for_geometry'].lower()=='true'];out=float(row['codex_disc_max_arcsec']);search=[r for r in good if .5<=r['sma_arcsec']<=.7*out];es=[statistics.median([search[max(0,i-1)]['ellipticity'],r['ellipticity'],search[min(len(search)-1,i+1)]['ellipticity']]) for i,r in enumerate(search)]
 selected=[r['sma_arcsec'] for r in good if r['selected_bar'].lower()=='true'];c=[]
 for i,r in enumerate(search):
  if es[i]<.2 or es[i]<max(es[max(0,i-2):i+3]):continue
  l=rr=i
  while l>0 and es[l-1]>=es[i]-.05 and i-l<12:l-=1
  while rr<len(search)-1 and es[rr+1]>=es[i]-.05 and rr-i<12:rr+=1
  plateau=search[l:rr+1]
  if [z['sma_arcsec'] for z in plateau]!=selected:continue
  beyond=[p for p in good if r['sma_arcsec']<p['sma_arcsec']<=max(2.5*r['sma_arcsec'],r['sma_arcsec']+1)]
  low=min(beyond,key=lambda z:z['ellipticity']);drop=es[i]-low['ellipticity'];c.append(dict(peak_radius=r['sma_arcsec'],smoothed_peak=es[i],low_radius=low['sma_arcsec'],low_ellipticity=low['ellipticity'],drop=drop))
 print(oid,json.dumps(c))
