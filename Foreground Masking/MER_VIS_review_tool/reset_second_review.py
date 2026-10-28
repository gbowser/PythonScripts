import csv,json,shutil,urllib.request
from pathlib import Path
from datetime import datetime,timezone
root=Path(r'C:\Users\gordo\Documents\Github\PythonScripts\Euclid\review_MER_VIS\saved_reviews')
review_file=root/'MER_VIS_saved_reviews.json'
state=json.loads((root/'server.json').read_text(encoding='utf8'))
base=state['url']
if not base.startswith('http://127.0.0.1:') or not base.endswith('/'):raise RuntimeError('Unexpected server URL')
def request(path,payload=None,token=None):
 headers={}
 data=None
 if payload is not None:
  data=json.dumps(payload).encode();headers={'Content-Type':'application/json','X-Review-Token':token}
 with urllib.request.urlopen(urllib.request.Request(base+path,data=data,headers=headers),timeout=20) as response:return json.load(response)
boot=request('api/bootstrap');before=json.loads(review_file.read_text(encoding='utf8'))
if before!=boot['reviews']:raise RuntimeError('Disk and server reviews differ; no changes made')
stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
backup=root/'review_backups'/('before_second_review_'+stamp);backup.mkdir(parents=True,exist_ok=False)
for name in ['MER_VIS_saved_reviews.json','MER_VIS_saved_reviews.csv']:
 if (root/name).exists():shutil.copy2(root/name,backup/name)
changed=0;warnings=set()
for oid,record in before.items():
 if record.get('reviewed',True) is False:continue
 result=request('api/review-status',{'object_id':oid,'reviewed':False},boot['token']);changed+=1
 if result.get('warning'):warnings.add(result['warning'])
after=json.loads(review_file.read_text(encoding='utf8'));live=request('api/bootstrap')['reviews']
assert after==live,'Disk/server mismatch after reset'
assert after.keys()==before.keys(),'Review records changed'
for oid,record in before.items():
 assert after[oid].get('reviewed') is False
 for key,value in record.items():
  if key not in ('reviewed','review_status_changed_utc'):assert after[oid].get(key)==value,f'Existing field changed: {oid} {key}'
if not warnings:
 with (root/'MER_VIS_saved_reviews.csv').open(encoding='utf-8-sig',newline='') as stream:
  exported={r['object_id']:r for r in csv.DictReader(stream)}
 for oid,r in after.items():assert exported[oid]['reviewed']=='False' and exported[oid]['notes']==r.get('notes','')
report={'reset':changed,'remaining_reviewed':sum(r.get('reviewed',True) is not False for r in after.values()),'records_preserved':len(after),'notes_preserved':sum(bool(r.get('notes')) for r in after.values()),'all_existing_fields_preserved':True,'backup':str(backup),'warnings':sorted(warnings)}
(backup/'reset_verification.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps(report,indent=2))
