from pathlib import Path
import csv,collections
p=Path(r'C:\Users\gordo\Downloads\Euclid_VIS_disc_bar_PA_manifest.csv');r=list(csv.DictReader(p.open(encoding='utf-8-sig')))
print('Rows',len(r),'Unique IDs',len(set(x['object_id'] for x in r)))
for k in ['status','method','bar_quality','flags']:print(k,collections.Counter(x[k] for x in r).most_common(15))
