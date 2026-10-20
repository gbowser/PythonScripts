from pathlib import Path
import sys,csv,textwrap,collections
sys.path.insert(0,str(Path(__file__).parent/'review_code'))
from make_MER_VIS_galaxy_report_cards import FLAG_LABELS
root=Path(r'D:\Dropbox\Public Documents\UCLAN\MSc Research\Euclid');result=[]
for r in csv.DictReader((root/'Euclid_MER_VIS_geometry/MER_VIS_local_geometry_manifest.csv').open(encoding='utf8')):
 flags=list(filter(None,r['codex_quality_flags'].split(';')));issues=['QUALITY: '+'; '.join(FLAG_LABELS.get(f,f) for f in flags)]
 if r.get('codex_centre_offset_arcsec'):issues.append(f"Centre offset {float(r['codex_centre_offset_arcsec']):.2f} arcsec; method {r['codex_method']}. Red + fitted; white x catalogue.")
 if r['cutout_partial'].lower()=='true':issues.append('COVERAGE: requested cutout is PARTIAL; inspect galaxy coverage.')
 lines=sum(len(textwrap.wrap(x,width=88,break_long_words=False)) for x in issues)
 if lines>5:result.append((r['object_id'],lines))
print(len(result),'cards with >5 footer lines',collections.Counter(n for _,n in result),result[:4])
