from pathlib import Path
p=Path('MER_VIS_pipeline_v2/prepare_current_MER_VIS_report_data.py');s=p.read_text(encoding='utf-8-sig');needle="# Subsets and diagnostics retain data rather than treating face-on as a QI."
addition="""paired={}
for name,ours,theirs,axial in [('disc','codex_disc_pa_sky_deg','disc_PA_deg',True),('bar','codex_bar_pa_sky_deg','bar_PA_deg',True),('inclination','codex_inclination_deg','inclination_deg',False)]:
 before=[];after=[]
 for r in fits:
  z=old[r['object_id']];ext=external[r['object_id']];aa=f(z,ours);bb=f(r,ours);cc=f(ext,theirs)
  if z['codex_fit_status']=='provisional_fit' and all(math.isfinite(x) for x in [aa,bb,cc]):
   before.append(abs(delta(aa,cc) if axial else aa-cc));after.append(abs(delta(bb,cc) if axial else bb-cc))
 paired[name]=dict(n=len(before),before_median_abs=float(np.median(before)),after_median_abs=float(np.median(after))) if before else dict(n=0)
summary['paired_supplied_comparison']=paired
"""
s=s.replace(needle,addition+'\n'+needle);p.write_text(s,encoding='utf8')
p=Path('MER_VIS_pipeline_v2/write_current_MER_VIS_comparison_summary.py');s=p.read_text(encoding='utf-8-sig');needle="(out/'comparison_summary.md').write_text"
addition="""lines+=['','## Before and after on exactly the same galaxies','','These subsets require available old, current and supplied measurements. A bar must be accepted in the new run, so the bar subset is selective. Agreement is not independent accuracy.','', '| Quantity | Matched galaxies | Original median absolute difference | Current median absolute difference |','|---|---:|---:|---:|']
for k,z in v['paired_supplied_comparison'].items():
 if z['n']:lines.append(f\"| {k} | {z['n']} | {z['before_median_abs']:.2f}° | {z['after_median_abs']:.2f}° |\")
"""
s=s.replace(needle,addition+'\n'+needle);p.write_text(s,encoding='utf8')
