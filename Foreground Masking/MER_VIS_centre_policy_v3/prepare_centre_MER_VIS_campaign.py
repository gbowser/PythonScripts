"""Build an isolated centre-policy review campaign; original reviews are read-only."""
import csv,hashlib,json,math,shutil,sys,uuid,urllib.request
from pathlib import Path
from datetime import datetime,timezone
BASE=Path(__file__).resolve().parent;WORK=BASE/'round_output';APP=BASE.parent/'MER_VIS_review_tool'
ORIGINAL=Path(r'C:\Users\gordo\Documents\Github\PythonScripts\Euclid\review_MER_VIS\saved_reviews')
DATA=Path(r'D:\Dropbox\Public Documents\UCLAN\MSc Research\Euclid')
REPO=Path(r'C:\Users\gordo\Documents\Github\PythonScripts\Euclid')
sys.path.insert(0,str(APP))
from centre_policy_MER_VIS import POLICY_VERSION,DEFAULT_POLICY
state=json.loads((ORIGINAL/'server.json').read_text());url=state['url']
def get(path):
 with urllib.request.urlopen(url+path,timeout=30) as r:return json.load(r)
boot=get('api/bootstrap');raw=(ORIGINAL/'MER_VIS_saved_reviews.json').read_bytes();reviews=json.loads(raw);assert reviews==boot['reviews']
source=DATA/'Euclid_MER_VIS_geometry'/'MER_VIS_local_geometry_manifest.csv';manifest_hash=hashlib.sha256(source.read_bytes()).hexdigest();rows=list(csv.DictReader(source.open(encoding='utf-8-sig')));byid={r['object_id']:r for r in rows};old_ids={r['object_id'] for r in boot['sample']}
seg={r['object_id']:r.get('segmentation_area') for r in csv.DictReader((REPO/'datalabs_MER_VIS'/'MER_VIS_datalabs_manifest.csv').open(encoding='utf-8-sig'))}
priority=['-663928688473758026','2756030807655229287','-595029565493921205','-537890362287224823','-518633776290631360','2681494150647395085','2654474268655808169','-586374330510251740','-524824554283124036','2645436353651870062','2697242050653408730']
controls=[r['object_id'] for r in boot['sample'] if r['category']=='control' and r['object_id'] not in priority][:2]
selected=set(priority+controls);validation=[]
def finite(v):
 try:return math.isfinite(float(v))
 except:return False
eligible=[r for r in rows if r['object_id'] not in old_ids and r['codex_fit_status']=='provisional_fit' and finite(r.get('codex_fit_centre_x_pix')) and finite(r.get('codex_fit_centre_y_pix')) and finite(r.get('codex_disc_min_arcsec')) and finite(r.get('codex_disc_max_arcsec')) and Path(r['fits_path']).is_file() and Path(r['fits_path']).stat().st_size<100_000_000]
for label,test in [('new_clean',lambda r:not r['codex_quality_flags'] and float(r.get('codex_n_disc') or 0)>=6),('new_centre',lambda r:any(f in r['codex_quality_flags'] for f in ['centre_offset_large','centre_unstable'])),('new_geometry',lambda r:any(f in r['codex_quality_flags'] for f in ['disc_PA_unstable','disc_axis_ratio_unstable']))]:
 candidates=sorted([r for r in eligible if test(r) and r['object_id'] not in selected],key=lambda r:float(r['ra_deg']))
 if len(candidates)<2:raise RuntimeError('Not enough validation examples: '+label)
 for index in [len(candidates)//3,2*len(candidates)//3]:
  row=candidates[index];selected.add(row['object_id']);validation.append((row['object_id'],label))
WORK.mkdir(parents=True,exist_ok=True);(WORK/'refits').mkdir(exist_ok=True);(WORK/'original_review_snapshot.json').write_bytes(raw)
campaign=dict(campaign_id='MER_VIS_centre_policy_v3_2026-10-28',title='Centre acceptance re-review',policy_version=POLICY_VERSION,policy=DEFAULT_POLICY,
              original_output=str(ORIGINAL),source_review_sha256=hashlib.sha256(raw).hexdigest(),source_manifest_sha256=manifest_hash,
              categories={'centre_priority':'Centre acceptance — priority re-review','centre_control':'Centre acceptance — clean references','centre_validation':'Centre acceptance — new validation examples'},sample=[],cases={},previous_reviews={},requires_visual_validation=True)
records={};index={};jobs=[]
for oid in priority+controls+[oid for oid,_ in validation]:
 prior=reviews.get(oid);g=get('api/galaxy?id='+oid+(('&refit='+prior['settings']['refit_id']) if prior and prior.get('settings',{}).get('refit_id') else ''))
 ref=g['centre'];provenance='previous_review_confirmed_adopted_centre' if prior and prior.get('centre_decision')=='looks_correct' else 'automatic_reference_unverified'
 reference_uncertain=bool(prior and prior.get('centre_decision')!='looks_correct')
 if not all(isinstance(v,(int,float)) and math.isfinite(v) for v in ref):raise RuntimeError('No usable reference for '+oid)
 category='centre_priority' if oid in priority else 'centre_control' if oid in controls else 'centre_validation'
 reason=('Previous review / geometry uncertainty; validate centre and fixed-centre shape' if oid in priority else 'Previously clean reference; confirm no degradation' if oid in controls else next(label for ident,label in validation if ident==oid)+'; centre needs visual confirmation')
 case=dict(object_id=oid,reference_centre=ref,reference_provenance=provenance,original_category=next((r['category'] for r in boot['sample'] if r['object_id']==oid),None),previous_refit_id=(prior or {}).get('settings',{}).get('refit_id'),previous_calculation=(prior or {}).get('calculation'),reference_uncertain=reference_uncertain,reason=reason)
 if reference_uncertain:
  oldjob=prior['settings']['refit_id'];shutil.copytree(ORIGINAL/'refits'/oldjob,WORK/'refits'/oldjob,dirs_exist_ok=True);job=oldjob;case['trial_action']='Existing trial retained: centre uncertain; no automatic refit/adoption'
 else:
  job=uuid.uuid4().hex;folder=WORK/'refits'/job;folder.mkdir();row=dict(byid[oid],manual_centre_x_pix=ref[0],manual_centre_y_pix=ref[1]);request=dict(object_id=oid,row=row,segmentation_area=seg[oid],lock_centre=True,centre_policy=DEFAULT_POLICY,reference_provenance=provenance,source_manifest_sha256=manifest_hash,engine_sha256=hashlib.sha256((APP/'fit_manual_centre_MER_VIS.py').read_bytes()).hexdigest(),worker_sha256=hashlib.sha256((APP/'refit_MER_VIS.py').read_bytes()).hexdigest(),requested_utc=datetime.now(timezone.utc).isoformat().replace('+00:00','Z'));(folder/'request.json').write_text(json.dumps(request,indent=2),encoding='utf8');jobs.append(dict(object_id=oid,job=job,request=str(folder/'request.json')));case['trial_action']='Fixed-centre refit; visual acceptance pending'
 index[oid]=job;case['recommended_refit_id']=job;campaign['cases'][oid]=case
 campaign['sample'].append(dict(object_id=oid,category=category,category_label=campaign['categories'][category],selection_reason=reason))
 if prior:campaign['previous_reviews'][oid]=prior
 def bounds(kind):
  values=g['intervals'][kind]
  return values if all(isinstance(v,(int,float)) for v in values) else ([.5,2] if kind=='bar' else [.5,4])
 settings=dict((prior or {}).get('settings',{}));settings.update(refit_id=job,disc=settings.get('disc',bounds('disc')),bar=settings.get('bar',bounds('bar')),editedDisc=True,editedBar=True,pool=settings.get('pool','pipeline'),noBar=settings.get('noBar',False),centre_policy_version=POLICY_VERSION)
 settings['rules']={**boot['rules'],**settings.get('rules',{}),**dict(centre_enabled=True,centre_cap_native=3,centre_fraction=.05,centre_floor_native=1)}
 settings['display']={**settings.get('display',{}),**dict(defaultVersion=2,stretch='autostf',gamma=1,ellipses=False,excludedEllipses=False,paComparison=False,centres=True,overlayMode='selected',showWarnings=False)}
 records[oid]=dict(object_id=oid,reviewed=False,disc_decision='not_assessed',bar_decision='not_assessed',centre_decision='not_assessed',rule_action='unsure',notes='',settings=settings,calculation={},previous_review_retained=bool(prior),campaign_id=campaign['campaign_id'])
(WORK/'MER_VIS_saved_reviews.json').write_text(json.dumps(records,indent=2),encoding='utf8');(WORK/'MER_VIS_latest_refits.json').write_text(json.dumps(index,indent=2),encoding='utf8');(BASE/'centre_policy_MER_VIS_campaign.json').write_text(json.dumps(campaign,indent=2),encoding='utf8');(BASE/'jobs.json').write_text(json.dumps(jobs,indent=2),encoding='utf8');assert hashlib.sha256((ORIGINAL/'MER_VIS_saved_reviews.json').read_bytes()).hexdigest()==campaign['source_review_sha256']
print(json.dumps(dict(examples=len(records),fixed_refits=len(jobs),new_validation=validation,original_reviews_preserved=True),indent=2))
