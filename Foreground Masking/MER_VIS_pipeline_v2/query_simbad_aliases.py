from pathlib import Path
import csv,collections,json,urllib.request,urllib.parse,time
out=Path('MER_VIS_pipeline_v2/catalogue_names');rows=list(csv.DictReader((out/'SIMBAD_candidates_5arcsec.csv').open(encoding='utf8')))
print('Candidate rows',len(rows),'unique targets',len(set(r['object_id'] for r in rows)));print('Types',collections.Counter(r['main_type'] for r in rows));print('NGC/IC',[(r['object_id'],r['main_id'],r['angDist']) for r in rows if r['main_id'].strip().startswith(('NGC','IC ','M '))][:20])
ids=sorted(set(r['main_id'] for r in rows));aliases=[]
for k in range(0,len(ids),100):
 quoted=','.join("'"+z.replace("'","''")+"'" for z in ids[k:k+100]);query='SELECT b.main_id, i.id FROM basic AS b JOIN ident AS i ON b.oid=i.oidref WHERE b.main_id IN ('+quoted+')'
 req=urllib.request.Request('https://simbad.cds.unistra.fr/simbad/sim-tap/sync',data=urllib.parse.urlencode({'REQUEST':'doQuery','LANG':'ADQL','FORMAT':'csv','QUERY':query}).encode(),headers={'User-Agent':'EuclidGalaxyResearch/1.0'})
 with urllib.request.urlopen(req,timeout=60) as response:body=response.read().decode()
 aliases+=list(csv.DictReader(body.splitlines()));print(k,len(aliases),flush=True)
 time.sleep(.3)
(out/'SIMBAD_aliases.json').write_text(json.dumps(aliases,indent=2),encoding='utf8')
