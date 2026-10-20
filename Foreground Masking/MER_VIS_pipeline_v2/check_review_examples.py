from pathlib import Path
import csv,json
root=Path(r'D:\Dropbox\Public Documents\UCLAN\MSc Research\Euclid\Euclid_MER_VIS_geometry')
rows={r['object_id']:r for r in csv.DictReader((root/'MER_VIS_local_geometry_manifest.csv').open())}
for oid in ['-518633776290631360','-601121275504424227','-586374330510251740','-524824554283124036']:
 r=rows[oid];print(oid,r['codex_fit_status'],r['codex_n_disc'],r.get('codex_disc_sampling_max_gap_fraction'),r['codex_quality_flags'])
