from pathlib import Path
import requests,time,hashlib,json
out=Path(r'D:\Dropbox\Public Documents\UCLAN\MSc Research\Euclid\MER_VIS_PA_validation');out.mkdir(exist_ok=True)
f='EUC_MER_BGSUB-MOSAIC-VIS_TILE102023983-8D3C9A_20241018T181958.121344Z_00.00.fits';dst=out/f;tmp=dst.with_suffix('.fits.part')
if not dst.exists():
 url='https://eas.esac.esa.int/sas-dd/data';params={'RETRIEVAL_TYPE':'FILE','FILE_NAME':f,'RELEASE':'sedm'}
 with requests.get(url,params=params,stream=True,timeout=(30,120)) as r:
  r.raise_for_status();total=int(r.headers.get('Content-Length',1474565760));n=0;t=time.monotonic();last=t;md=hashlib.md5()
  with tmp.open('wb') as h:
   for chunk in r.iter_content(4*1024*1024):
    h.write(chunk);md.update(chunk);n+=len(chunk)
    if time.monotonic()-last>20:print(f'{n/2**20:.0f}/{total/2**20:.0f} MiB downloaded',flush=True);last=time.monotonic()
  if n!=total:raise ValueError('Download incomplete')
  if md.hexdigest()!='bb20bec6eea0750a1c97cb002d33147e':raise ValueError('Archive MD5 mismatch')
  tmp.replace(dst);print('Verified archive MD5; complete',dst,flush=True)

