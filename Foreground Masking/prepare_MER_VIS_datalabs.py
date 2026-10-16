"""Build an upload-ready Datalabs notebook and source-path manifest."""
from pathlib import Path
import csv,json,requests

out=Path('../Euclid/datalabs_MER_VIS').resolve();out.mkdir(exist_ok=True)
source=Path('../Euclid/q1_mer_vis_cutouts/mer_vis_cutout_manifest.csv')
rows=list(csv.DictReader(source.open(newline='',encoding='utf-8')))
ids=sorted({int(r['mosaic_product_oid']) for r in rows})
q='SELECT mosaic_product_oid,datalabs_path,file_name FROM sedm.mosaic_product WHERE mosaic_product_oid IN ('+','.join(map(str,ids))+')'
r=requests.post('https://eas.esac.esa.int/tap-server/tap/sync',data={'REQUEST':'doQuery','LANG':'ADQL','FORMAT':'csv','QUERY':q,'MAXREC':'10000'},timeout=60)
r.raise_for_status();metadata=list(csv.DictReader(r.text.splitlines()))
paths={m['mosaic_product_oid']:m for m in metadata}
assert len(paths)==len(ids)
for row in rows:
 m=paths[row['mosaic_product_oid']]
 assert m['file_name']==row['mosaic_file_name']
 row['datalabs_path']=m['datalabs_path']
 row['datalabs_source_file']=m['datalabs_path'].rstrip('/')+'/'+m['file_name']
with (out/'MER_VIS_datalabs_manifest.csv').open('w',newline='',encoding='utf-8') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
script=Path('make_MER_VIS_datalabs_cutouts.py').read_text(encoding='utf-8')
(out/'make_MER_VIS_datalabs_cutouts.py').write_text(script,encoding='utf-8')
def cell(kind,text):
 d={'cell_type':kind,'metadata':{},'source':text.splitlines(True)}
 if kind=='code':d.update(execution_count=None,outputs=[])
 return d
cells=[cell('markdown','''# MER VIS galaxy cutouts on ESA Datalabs

Select the **euclid-tools** kernel. Run cells in order using Shift+Enter.
Upload this notebook, the companion Python file, and MER_VIS_datalabs_manifest.csv
into the same folder in your persistent workspace. No image download URLs are used.
The source mosaics are read from the mounted Euclid Q1 data volume.
'''),cell('code','''from pathlib import Path
import sys, shutil, csv
import numpy, astropy
print('Python:', sys.version)
print('Astropy:', astropy.__version__)
print('Notebook folder:', Path.cwd())
WORK = Path('/media/user/Euclid_MER_VIS')
# /media/user is the personal workspace in ESA's tutorial.
# If your instance uses another persistent workspace mount, change WORK.
WORK.mkdir(parents=True, exist_ok=True)
OUTPUT = WORK / 'cutouts'
MANIFEST = Path('MER_VIS_datalabs_manifest.csv').resolve()
assert MANIFEST.is_file(), 'Upload the manifest into the notebook folder'
assert Path('make_MER_VIS_datalabs_cutouts.py').is_file(), 'Upload the Python helper'
print('Output:', OUTPUT)
print('Filesystem free GiB:', round(shutil.disk_usage(WORK).free / 2**30, 2))
print('Also check your account quota in Datalabs; filesystem free is not your quota.')
'''),cell('markdown','''## Check the source paths and estimated output size

The source paths were retrieved from Euclid TAP's datalabs_path metadata.
If paths are missing, check the mounted Q1 volume in the official Cutouts tutorial.
Do not download full mosaics to repair a missing mount.
'''),cell('code','''import make_MER_VIS_datalabs_cutouts as mer
report = mer.preflight(MANIFEST)
report
'''),cell('markdown','''## Create a five galaxy pilot

This writes derived science cutouts to your workspace, not to the shared volume.
The native projection and WCS are retained; no deprojection or rotation is applied.
'''),cell('code',"mer.run(MANIFEST, OUTPUT, limit=5)\n"),cell('markdown','''## Inspect the first cutout

Check the galaxy position, size and whether the requested sky box is clipped.
SCIENCE cutouts do not include RMS, weight, segmentation or quality maps.
'''),cell('code','''from astropy.io import fits
from astropy.visualization import simple_norm
import matplotlib.pyplot as plt
files = sorted(OUTPUT.glob('*_MER_VIS_cutout.fits'))
assert files, 'No cutouts created; inspect the processing report'
with fits.open(files[0], checksum=True) as hdul:
    data = hdul[0].data
    header = hdul[0].header
    print(files[0].name, data.shape, 'PARTIAL:', header['PARTIAL'])
    plt.figure(figsize=(7,7))
    plt.imshow(data, origin='lower', cmap='gray',
               norm=simple_norm(data, 'asinh', percent=99.5))
    plt.plot(header['CENX']-1, header['CENY']-1, 'r+')
    plt.title(header['OBJECT'])
    plt.show()
'''),cell('markdown','''## Run all galaxies after checking the pilot and storage quota

This cell is deliberately commented out. Remove the leading # when ready.
Valid existing cutouts are checked and skipped on a rerun. Each completed
object is checkpointed in MER_VIS_processing_manifest.csv. A stopped kernel
can be restarted and the batch rerun. Keep the browser session open until complete.
'''),cell('code',"# mer.run(MANIFEST, OUTPUT, limit=None)\n"),cell('markdown','''## Review the report

Errors and PARTIAL=True need inspection. Five successful pilot products do not
guarantee every remaining galaxy will succeed. Files persist only if OUTPUT is
in your persistent personal/team workspace. Save this notebook with Ctrl+S.
'''),cell('code','''from collections import Counter
with (OUTPUT/'MER_VIS_processing_manifest.csv').open(newline='') as f:
    results = list(csv.DictReader(f))
print(Counter(r['status'] for r in results))
print('Report:', OUTPUT/'MER_VIS_processing_manifest.csv')
''')]
nb={'cells':cells,'metadata':{'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'},'language_info':{'name':'python'}},'nbformat':4,'nbformat_minor':5}
for i,c in enumerate(nb['cells']):c['id']=f'mer-vis-{i}'
(out/'MER_VIS_Datalabs_Cutouts.ipynb').write_text(json.dumps(nb,indent=2),encoding='utf-8')
print('Prepared',len(rows),'galaxies from',len(ids),'mosaics in',out)
print('Example mounted source:',rows[0]['datalabs_source_file'])
