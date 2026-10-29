from pathlib import Path
import json,hashlib,csv
ROOT=Path(__file__).resolve().parents[1]
CONFIG=ROOT/'laptop_setup/config';CONFIG.mkdir(exist_ok=True)
research=Path(r'C:\Users\gordo\Dropbox\Public Documents\UCLAN\MSc Research')
cv=research/'Remove foreground objects/clean22_haigh_aligned_bright150_galaxy150_sep_sensitivity'
def local(value):
    prefix='/mnt/d/Dropbox/Public Documents/UCLAN/MSc Research/'
    prefix2='D:\\Dropbox\\Public Documents\\UCLAN\\MSc Research\\'
    if value.startswith(prefix):return '\\\\?\\'+str(research/value[len(prefix):])
    if value.startswith(prefix2):return '\\\\?\\'+str(research/value[len(prefix2):])
    return value
rejected=json.loads((cv/'SEP_cross_validation/sep_toy_cross_validation_rejected.json').read_text())
sep=Path(local(rejected['best_diagnostic_candidate']['best_json']))
mto=cv/'MTObjects_cross_validation/mtobjects_toy_cross_validation_best.json'
provenance={}
for label,p,name in [('SEP diagnostic rejected fold 20',sep,'sep-diagnostic-rejected-fold20.json'),('MTObjects final winner',mto,'mto-final.json')]:
    assert p.is_file(),str(p)
    target=CONFIG/name;target.write_bytes(p.read_bytes())
    provenance[name]={'label':label,'source':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
source=cv/'paired_injections/paired_toy_injection_manifest.json'
original=json.loads(source.read_text()); missing=[];references=[]
def walk(v):
    if isinstance(v,dict):return {k:walk(x) for k,x in v.items()}
    if isinstance(v,list):return [walk(x) for x in v]
    if isinstance(v,str):
        translated=local(v)
        if translated!=v:
            references.append(translated)
            if not Path(translated).exists():missing.append(translated)
        return translated
    return v
(CONFIG/'paired-injections-laptop.json').write_text(json.dumps(walk(original),indent=2))
provenance['paired-injections-laptop.json']={'source':str(source),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'translated_paths':len(references),'missing':missing}
(CONFIG/'provenance.json').write_text(json.dumps(provenance,indent=2))
print(json.dumps(provenance,indent=2))
