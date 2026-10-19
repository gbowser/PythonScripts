from pathlib import Path
from astropy.io import fits
import hashlib,requests,csv
out=Path(r'D:\Dropbox\Public Documents\UCLAN\MSc Research\Euclid\MER_VIS_PA_validation')
p=next(out.glob('*.part'));print('SIZE',p.stat().st_size,'MD5',hashlib.file_digest(p.open('rb'),'md5').hexdigest())
with fits.open(p,checksum=True) as h:
 print(h.info(output=False));print(repr(h[0].header));print('checksums',[(z.verify_checksum(),z.verify_datasum()) for z in h])
f=next(r['file_name'] for r in csv.DictReader(open('MER_VIS_explanation_work/files.csv')) if 'FINAL-CAT_TILE' in r['file_name'])
r=requests.get('https://eas.esac.esa.int/sas-dd/data',params={'RETRIEVAL_TYPE':'FILE','FILE_NAME':f,'RELEASE':'sedm'},timeout=120);r.raise_for_status();(out/f).write_bytes(r.content);print('Catalogue downloaded',len(r.content))
