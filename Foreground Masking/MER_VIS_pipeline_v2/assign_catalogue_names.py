from pathlib import Path
import csv,json,collections,re,math,hashlib,urllib.parse
root=Path(__file__).parent;out=root/'catalogue_names'
sims=list(csv.DictReader((out/'SIMBAD_candidates_5arcsec.csv').open(encoding='utf8')))
leda=list(csv.DictReader((out/'HyperLEDA_candidates_5arcsec.csv').open(encoding='utf8')))
alias=collections.defaultdict(list)
for r in json.loads((out/'SIMBAD_aliases.json').read_text(encoding='utf8')):alias[r['main_id']].append(r['id'])
def norm(x):return ' '.join(x.split())
def pgc(x):
 m=re.match(r'^(?:LEDA|PGC)\s+(\d+)$',norm(x));return 'PGC '+str(int(m[1])) if m else None
def preferred(ids):
 for prefix in ['M ','NGC ','IC ','UGC ','ESO ']:
  hits=[norm(z) for z in ids if re.match({'M ':r'^M\s+\d+$','NGC ':r'^NGC\s+\d+', 'IC ':r'^IC\s+\d+', 'UGC ':r'^UGC\s+\d+', 'ESO ':r'^ESO\s+'}[prefix],norm(z))]
  if hits:return sorted(hits)[0]
 hits=[pgc(z) for z in ids if pgc(z)]
 return hits[0] if hits else norm(ids[0])
candidates=collections.defaultdict(list)
for r in sims:
 if r['main_type'] not in ['Galaxy','GtowardsCl','LowSurfBrghtG','EmissionG','Seyfert2','AGN','RadioG','GtowardsGroup']:continue
 ids=[r['main_id']]+alias[r['main_id']];key=next((pgc(z) for z in ids if pgc(z)),norm(r['main_id']))
 candidates[r['object_id']].append(dict(key=key,name=preferred(ids),distance=float(r['angDist']),source='SIMBAD',main_id=norm(r['main_id']),aliases=' | '.join(sorted(set(map(norm,ids)))),url='https://simbad.cds.unistra.fr/simbad/sim-id?Ident='+urllib.parse.quote(r['main_id']),otype=r['otype']))
for r in leda:
 if r['OType'] not in ['G']:continue
 key='PGC '+str(int(r['PGC']));ids=[key]+[x for x in r['ANames'].split(',') if x.strip()]
 candidates[r['object_id']].append(dict(key=key,name=preferred(ids),distance=float(r['angDist']),source='VizieR VII/237',main_id=key,aliases=' | '.join(ids),url='https://vizier.cds.unistra.fr/viz-bin/VizieR?-source=VII/237/pgc&PGC='+str(int(r['PGC'])),otype='G'))
base=Path(r'D:\Dropbox\Public Documents\UCLAN\MSc Research\Euclid');geo=base/'Euclid_MER_VIS_geometry';manifest=geo/'MER_VIS_local_geometry_manifest.csv';rows=list(csv.DictReader(manifest.open()));result=[];accepted=0
for r in rows:
 oid=r['object_id'];group=candidates[oid];unique={}
 for z in sorted(group,key=lambda z:(z['source']!='SIMBAD',z['distance'])):
  if z['key'] not in unique:unique[z['key']]=z
 vals=sorted(unique.values(),key=lambda z:z['distance']);chosen=None;status='no_match_in_searched_catalogues'
 if vals:
  status='outside_secure_radius' if vals[0]['distance']>2 else 'ambiguous' if len(vals)>1 else 'secure_positional_match'
  if status=='secure_positional_match':chosen=vals[0];accepted+=1
 r.update(catalogue_match_status=status,catalogue_name=chosen['name'] if chosen else '',catalogue_match_separation_arcsec=chosen['distance'] if chosen else '',catalogue_match_source=chosen['source'] if chosen else '',catalogue_match_url=chosen['url'] if chosen else '',catalogue_simbad_main_id=chosen['main_id'] if chosen and chosen['source']=='SIMBAD' else '',catalogue_match_checked_utc='2026-10-20',catalogue_match_note='Unique galaxy identity within 5 arcsec and separation <=2 arcsec; catalogue-coordinate match, not independent morphological confirmation.')
 result.append(dict(object_id=oid,match_status=status,adopted_name=r['catalogue_name'],separation_arcsec=r['catalogue_match_separation_arcsec'],source=r['catalogue_match_source'],url=r['catalogue_match_url'],candidates=vals))
keys=list(dict.fromkeys(k for r in rows for k in r))
with manifest.open('w',encoding='utf8',newline='') as f:
 w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)
(out/'MER_VIS_catalogue_name_matches.json').write_text(json.dumps(result,indent=2),encoding='utf8')
with (out/'MER_VIS_catalogue_name_matches.csv').open('w',encoding='utf8',newline='') as f:
 w=csv.DictWriter(f,fieldnames=['object_id','match_status','adopted_name','separation_arcsec','source','url']);w.writeheader();w.writerows({k:v for k,v in z.items() if k!='candidates'} for z in result)
summary=dict(targets=len(rows),status=dict(collections.Counter(r['catalogue_match_status'] for r in rows)),accepted_names=accepted,accepted_by_source=dict(collections.Counter(r['catalogue_match_source'] for r in rows if r['catalogue_name'])),search_radius_arcsec=5,secure_radius_arcsec=2,source_manifest_sha256=hashlib.sha256(manifest.read_bytes()).hexdigest(),named_NGC_IC_M=[r['catalogue_name'] for r in rows if r['catalogue_name'].startswith(('NGC ','IC ','M '))],date_utc='2026-10-20')
(out/'MER_VIS_catalogue_name_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf8');s=json.loads((geo/'MER_VIS_v2_summary.json').read_text());s['source_manifest_sha256']=summary['source_manifest_sha256'];s['catalogue_names']=summary;(geo/'MER_VIS_v2_summary.json').write_text(json.dumps(s,indent=2),encoding='utf8');print(json.dumps(summary,indent=2))
