from pathlib import Path
import csv,io,json,urllib.request,uuid
src=Path(r'D:\Dropbox\Public Documents\UCLAN\MSc Research\Euclid\Euclid_MER_VIS_geometry\MER_VIS_local_geometry_manifest.csv')
rows=list(csv.DictReader(src.open()));b=io.StringIO();w=csv.writer(b);w.writerow(['object_id','ra','dec'])
for r in rows:w.writerow([r['object_id'],r['ra_deg'],r['dec_deg']])
out=Path('MER_VIS_pipeline_v2/catalogue_names');out.mkdir(exist_ok=True)
url='https://cdsxmatch.cds.unistra.fr/xmatch/api/v1/sync'
fields={'request':'xmatch','distMaxArcsec':'5','selection':'all','RESPONSEFORMAT':'csv','cat2':'simbad','colRA1':'ra','colDec1':'dec'}
boundary='euclid_'+uuid.uuid4().hex
parts=[]
for key,value in fields.items():parts.append('--'+boundary+'\r\nContent-Disposition: form-data; name="'+key+'"\r\n\r\n'+value+'\r\n')
parts.append('--'+boundary+'\r\nContent-Disposition: form-data; name="cat1"; filename="euclid_targets.csv"\r\nContent-Type: text/csv\r\n\r\n'+b.getvalue()+'\r\n--'+boundary+'--\r\n')
req=urllib.request.Request(url,data=''.join(parts).encode(),headers={'Content-Type':'multipart/form-data; boundary='+boundary,'User-Agent':'EuclidGalaxyResearch/1.0'})
with urllib.request.urlopen(req,timeout=90) as response:body=response.read()
(out/'SIMBAD_candidates_5arcsec.csv').write_bytes(body);print(len(body),body[:1600].decode())
