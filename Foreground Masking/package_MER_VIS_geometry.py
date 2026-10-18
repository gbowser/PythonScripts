"""Prepare the portable version of the existing geometry algorithm for Datalabs."""
import ast,json
from pathlib import Path
root=Path('../Euclid').resolve();out=root/'datalabs_MER_VIS'
def function(path,name):
 source=path.read_text(encoding='utf-8')
 node=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name==name)
 return ast.get_source_segment(source,node)
parts=['"""Portable copies of the project WCS and bar-alignment transforms."""',
       'import math\nimport numpy as np\nfrom astropy.io import fits\nfrom astropy.wcs import WCS',
       function(Path('Shared/foreground_display_helpers.py'),'image_transform'),
       function(root/'extract_euclid_VIS_bars.py','local_pixel_matrix'),
       function(root/'deproject_calibrated_VIS_galaxies.py','transform_cutout').replace('display.image_transform','image_transform')]
(out/'MER_VIS_geometry_transforms.py').write_text('\n\n'.join(parts)+'\n',encoding='utf-8')
source=(root/'fit_euclid_VIS_geometry.py').read_text(encoding='utf-8')
source=source.replace('from extract_calibrated_VIS_galaxies import DEFAULT_OUTPUT',"DEFAULT_OUTPUT = Path('/media/user/Euclid_MER_VIS/cutouts')")
source=source.replace('from extract_euclid_VIS_bars import local_pixel_matrix','from MER_VIS_geometry_transforms import local_pixel_matrix')
source=source.replace('from deproject_calibrated_VIS_galaxies import transform_cutout','from MER_VIS_geometry_transforms import transform_cutout')
(out/'fit_MER_VIS_geometry_portable.py').write_text(source,encoding='utf-8')
(out/'compare_MER_VIS_datalabs_geometry.py').write_text(Path('compare_MER_VIS_datalabs_geometry.py').read_text(encoding='utf-8'),encoding='utf-8')
def cell(kind,text,i):
 d=dict(cell_type=kind,id=f'geometry-{i}',metadata={},source=text.splitlines(True))
 if kind=='code':d.update(outputs=[],execution_count=None)
 return d
texts=[('markdown','''# Compare Codex ellipse geometry with Euclid Q1 morphology

Upload the notebook, the three companion Python files, and the comparison CSV
to your Euclid_MER_VIS workspace folder. Use EUCLID-TOOLS. No image download.
All PAs are degrees east of north modulo 180; inclinations are degrees, face-on=0.
Euclid detection/Sersic shapes are whole-object proxies, not measured bars or
isolated outer discs. Euclid bar PA is unavailable and is intentionally blank.
The thin circular-disc assumption q0=0 is used consistently for comparisons.
Zoobot fractions are classifications, not physical torque-based bar strength.
'''),('code','''from pathlib import Path
import sys
WORK = Path('/media/user/Euclid_MER_VIS')
sys.path.insert(0, str(WORK))
import compare_MER_VIS_datalabs_geometry as comparison
TEMPLATE = WORK / 'MER_VIS_geometry_comparison_manifest.csv'
CUTOUTS = WORK / 'cutouts'
RESULTS = WORK / 'geometry_comparison'
assert TEMPLATE.is_file()
print('Existing cutouts:', len(list(CUTOUTS.glob('*_MER_VIS_cutout.fits'))))
print('Output manifest:', RESULTS/'MER_VIS_geometry_comparison_manifest.csv')
'''),('markdown','''## First calculate five objects
This makes diagnostic profiles and fills the comparison manifest. Every one
of the 2777 target rows is retained, including failures and not-yet-run rows.
'''),('code',"comparison.run(TEMPLATE, CUTOUTS, RESULTS, limit=5)\n"),('markdown','''## Inspect the results and overlays
The result CSV is in geometry_comparison; PNGs and radial profiles are in
geometry_comparison/profiles. Fit failures and quality flags must be retained.
No flag-free automatic fit is a final scientific measurement without review.
'''),('code','''import csv
from collections import Counter
with (RESULTS/'MER_VIS_geometry_comparison_manifest.csv').open() as handle:
    rows = list(csv.DictReader(handle))
print(Counter(r['codex_fit_status'] for r in rows))
'''),('markdown','''## Full batch and optional provisional face-on images
Remove # from the next line after checking the pilot. It calculates all objects
and writes aligned SCI/COVERAGE outputs only for fits with clear quality flags.
It keeps native inputs and does not fabricate values for failed fits.
Omit make_aligned=True if you only want the manifest. Keep your kernel running.
Reruns skip successful fits. Use retry_failures=True to retry failed fits.
Extra storage is needed for profiles and aligned images; check your quota.
'''),('code',"# comparison.run(TEMPLATE, CUTOUTS, RESULTS, limit=None, make_aligned=True)\n"),('markdown','''## Interpretation
codex_* geometry uses the earlier Photutils bar/outer-disc radial selection.
euclid_detection_pa_sky_deg is converted from Euclid THETA_IMAGE using the
native cutout WCS, assuming the native MER detection/science tile grid alignment.
Euclid raw Sersic/disc-fit PAs are retained without an unverified convention conversion.
The euclid_detection_inclination_proxy_deg uses q=1-ellipticity; the Sersic proxy
uses its fitted VIS b/a. Neither replaces an independently selected outer disc.
All angle comparisons use matched units, but measure different structures.
The aligned output has linear arcsecond axes, not a celestial RA/Dec WCS.
''')]
nb=dict(nbformat=4,nbformat_minor=5,metadata={'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'},'language_info':{'name':'python'}},cells=[cell(k,t,i) for i,(k,t) in enumerate(texts)])
(out/'MER_VIS_Geometry_Comparison.ipynb').write_text(json.dumps(nb,indent=2),encoding='utf-8')
print('Packaged portable fitter, transforms, batch runner and notebook')
