"""Build current-run evidence for the revised Word/PPT reports. No fitting."""
from pathlib import Path
import csv,json,collections,math
import numpy as np
from PIL import Image
BASE=Path(r'D:\Dropbox\Public Documents\UCLAN\MSc Research\Euclid');GEO=BASE/'Euclid_MER_VIS_geometry';CARDS=BASE/'MER_VIS_galaxy_reports/all_2777_sampling_review';WORK=Path(__file__).parent/'current_report';WORK.mkdir(exist_ok=True);(WORK/'images').mkdir(exist_ok=True)
rows=list(csv.DictReader((GEO/'MER_VIS_local_geometry_manifest.csv').open(encoding='utf8')));summary=json.loads((GEO/'MER_VIS_v2_summary.json').read_text());verification=json.loads((CARDS/'MER_VIS_report_verification.json').read_text()) if (CARDS/'MER_VIS_report_verification.json').exists() else dict(groups={'QI':2694,'NoQI':83},PDF_files=47,PDF_pages=463);metadata={r['object_id']:r for r in json.loads((CARDS/'MER_VIS_report_manifest.json').read_text())}
old={r['object_id']:r for r in csv.DictReader(open(r'C:\Users\gordo\Documents\Github\PythonScripts\Euclid\reports\MER_VIS_current\audit\original_v1_geometry_manifest.csv',encoding='utf8'))}
external={r['object_id']:r for r in csv.DictReader(open(r'C:\Users\gordo\Downloads\Euclid_VIS_disc_bar_PA_manifest.csv',encoding='utf-8-sig'))}
def f(r,k):
 try:return float(r[k])
 except:return math.nan
def flags(r):return list(filter(None,r['codex_quality_flags'].split(';')))
def delta(x,y):return (x-y+90)%180-90
fits=[r for r in rows if r['codex_fit_status']=='provisional_fit'];clean=[r for r in fits if not flags(r)];nonface=[r for r in fits if 'nearly_face_on' not in r['codex_information']]
comp={}
for key,col,axial in [('disc','disc_PA_deg',True),('bar','bar_PA_deg',True),('inclination','inclination_deg',False)]:
 ours='codex_'+('disc_pa_sky_deg' if key=='disc' else 'bar_pa_sky_deg' if key=='bar' else 'inclination_deg');v=[]
 for r in fits:
  a=f(r,ours);b=f(external[r['object_id']],col)
  if math.isfinite(a) and math.isfinite(b):v.append(delta(a,b) if axial else a-b)
 v=np.array(v);comp[key]=dict(n=len(v),median_abs=float(np.median(abs(v))),median_signed=float(np.median(v)),within10=int((abs(v)<=10).sum())) if len(v) else dict(n=0)
paired={}
for name,ours,theirs,axial in [('disc','codex_disc_pa_sky_deg','disc_PA_deg',True),('bar','codex_bar_pa_sky_deg','bar_PA_deg',True),('inclination','codex_inclination_deg','inclination_deg',False)]:
 before=[];after=[]
 for r in fits:
  z=old[r['object_id']];ext=external[r['object_id']];aa=f(z,ours);bb=f(r,ours);cc=f(ext,theirs)
  if z['codex_fit_status']=='provisional_fit' and all(math.isfinite(x) for x in [aa,bb,cc]):
   before.append(abs(delta(aa,cc) if axial else aa-cc));after.append(abs(delta(bb,cc) if axial else bb-cc))
 paired[name]=dict(n=len(before),before_median_abs=float(np.median(before)),after_median_abs=float(np.median(after))) if before else dict(n=0)
summary['paired_supplied_comparison']=paired
summary['original_face_on_count']=sum('nearly_face_on_PA_uncertain' in r.get('codex_quality_flags','') for r in old.values())

# Subsets and diagnostics retain data rather than treating face-on as a QI.
summary.update(verification=verification,clean=len(clean),partial=sum(str(r['cutout_partial']).lower()=='true' for r in rows),nonface_fits=len(nonface),supplied_comparison=comp,baseline_fits=sum(r['codex_fit_status']=='provisional_fit' for r in old.values()),baseline_failures=sum(r['codex_fit_status']=='fit_failed' for r in old.values()))
labels={'disc_PA_sparse_sampling':'Sparse disc sampling','disc_PA_unstable':'Disc PA varies across radius','disc_axis_ratio_unstable':'Changing disc ellipticity','weak_ellipse_bar_signature':'Weaker accepted bar signature','small_bar_sensitive_to_resolution':'Bar identification uncertain: small interval','relaxed_fit':'Relaxed recovery','iteration_limited_samples':'Iteration-limited samples','short_accepted_profile':'Short accepted profile','disc_range_fallback':'Disc interval fallback','bar_disc_ranges_close':'Bar and disc intervals close','small_disc':'Small disc','star_mask_removed':'Star mask removed in retry','neighbour_mask_removed':'Neighbour mask removed in recovery','no_bar_detected':'No accepted bar; disc retained','centre_offset_large':'Large centre offset','centre_unstable':'Centre changes across disc','high_inclination':'High inclination'}
# Reusable figures are cropped from the verified current cards only.
def example(r):
 oid=r['object_id'];src=CARDS/metadata[oid]['relative_png'];im=Image.open(src);image=WORK/'images'/f'{oid}.png';im.crop((50,210,1950,1080)).save(image)
 return dict(id=oid,image=str(image.resolve()),full_card=str(src).replace('all_2777_sampling_review','all_2777'),disc=f(r,'codex_disc_pa_sky_deg'),bar=f(r,'codex_bar_pa_sky_deg'),inc=f(r,'codex_inclination_deg'),centre_offset=f(r,'codex_centre_offset_arcsec'),method=r.get('codex_method',''),flags=flags(r),bar_status=r['codex_bar_status'],error=r['codex_error'],n_good=r.get('codex_n_good',''),n_disc=r.get('codex_n_disc',''),n_bar=r.get('codex_n_bar',''),disc_scatter=f(r,'codex_disc_pa_scatter_deg'),disc_span=f(r,'codex_disc_eps_span'),bar_end=f(r,'codex_bar_max_arcsec'),information=r['codex_information'])
good=sorted([r for r in clean if r['codex_bar_status']=='detected_A' and str(r['cutout_partial']).lower()!='true'],key=lambda r:f(r,'codex_disc_pa_scatter_deg'))[:4]
issues=sorted([r for r in fits if 'disc_PA_unstable' in flags(r)],key=lambda r:(r['object_id']!='-601121275504424227',-f(r,'codex_disc_pa_scatter_deg')))[:2]
example_groups=[]
for key in ['disc_PA_sparse_sampling','small_bar_sensitive_to_resolution','disc_PA_unstable','disc_axis_ratio_unstable','weak_ellipse_bar_signature','no_bar_detected','centre_offset_large','centre_unstable','disc_range_fallback','relaxed_fit']:
 singles=[r for r in fits if flags(r)==[key] and str(r['cutout_partial']).lower()!='true']
 if key=='disc_PA_unstable':singles.sort(key=lambda r:r['object_id']!='-601121275504424227')
 if key=='disc_PA_sparse_sampling':singles.sort(key=lambda r:r['object_id']!='-518633776290631360')
 if len(singles)>=2:example_groups.append(dict(key=key,title=labels[key],kind='isolated_flag',examples=[example(r) for r in singles[:2]],available=len(singles)))
# Save all actual remaining failures, without inventing two examples if fewer exist.
fail=[r for r in rows if r['codex_fit_status']=='fit_failed']
for i in range(0,len(fail),2):example_groups.append(dict(key='failure',title='Remaining fit failures',kind='failure',examples=[example(r) for r in fail[i:i+2]],available=len(fail)))
availability={key:sum(flags(r)==[key] and str(r['cutout_partial']).lower()!='true' for r in fits) for key in summary['flags']}
summary['isolated_example_availability']=availability
centre_row=max(fits,key=lambda r:f(r,'codex_centre_offset_arcsec'))
centre=example(centre_row);centre_source=CARDS/metadata[centre_row['object_id']]['relative_png'];centre_image=WORK/'images'/'centre_detail.png';Image.open(centre_source).crop((75,230,955,1010)).save(centre_image);centre['detail_image']=str(centre_image.resolve())

result=dict(centre_example=centre,summary=summary,flag_labels=labels,good_examples=[example(r) for r in good],poor_examples=[example(r) for r in issues],example_groups=example_groups)
# Nonfinite values are represented as null in the report input.
def safe(v):
 if isinstance(v,dict):return {k:safe(z) for k,z in v.items()}
 if isinstance(v,list):return [safe(z) for z in v]
 if isinstance(v,float) and not math.isfinite(v):return None
 return v
(WORK/'report_data.json').write_text(json.dumps(safe(result),indent=2),encoding='utf8');print(json.dumps(summary,indent=2))
