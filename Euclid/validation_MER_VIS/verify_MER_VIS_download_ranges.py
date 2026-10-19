from pathlib import Path
import json,requests
out=Path(r'D:\Dropbox\Public Documents\UCLAN\MSc Research\Euclid\MER_VIS_PA_validation');p=next(out.glob('*BGSUB*.fits'));n=p.stat().st_size;checks=[]
for start in [0,n-5760]:
 r=requests.get('https://eas.esac.esa.int/sas-dd/data',params={'RETRIEVAL_TYPE':'FILE','FILE_NAME':p.name,'RELEASE':'sedm'},headers={'Range':f'bytes={start}-{start+5759}'},stream=True,timeout=90)
 if r.status_code==206:
  data=r.content
  with p.open('rb') as f:f.seek(start);local=f.read(5760)
  checks.append({'offset':start,'status':r.status_code,'match':data==local,'content_range':r.headers.get('Content-Range')})
 else:checks.append({'offset':start,'status':r.status_code,'match':None})
 r.close()
(out/'MER_VIS_download_range_checks.json').write_text(json.dumps(checks,indent=2));print(checks)
