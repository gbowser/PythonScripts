from pathlib import Path
p=Path('MER_VIS_pipeline_v2/query_catalogue_names.py');s=p.read_text(encoding='utf-8-sig').replace('import csv,io,json,requests','import csv,io,json,urllib.request,uuid')
i=s.index('r=requests.post')
s=s[:i]+'''fields={'request':'xmatch','distMaxArcsec':'5','selection':'all','RESPONSEFORMAT':'csv','cat2':'simbad','colRA1':'ra','colDec1':'dec'}
boundary='euclid_'+uuid.uuid4().hex
parts=[]
for key,value in fields.items():parts.append('--'+boundary+'\\r\\nContent-Disposition: form-data; name="'+key+'"\\r\\n\\r\\n'+value+'\\r\\n')
parts.append('--'+boundary+'\\r\\nContent-Disposition: form-data; name="cat1"; filename="euclid_targets.csv"\\r\\nContent-Type: text/csv\\r\\n\\r\\n'+b.getvalue()+'\\r\\n--'+boundary+'--\\r\\n')
req=urllib.request.Request(url,data=''.join(parts).encode(),headers={'Content-Type':'multipart/form-data; boundary='+boundary,'User-Agent':'EuclidGalaxyResearch/1.0'})
with urllib.request.urlopen(req,timeout=90) as response:body=response.read()
(out/'SIMBAD_candidates_5arcsec.csv').write_bytes(body);print(len(body),body[:1600].decode())
'''
p.write_text(s,encoding='utf8')
