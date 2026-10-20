from pathlib import Path
p=Path('MER_VIS_pipeline_v2/recover_failed_MER_VIS_geometry.py');s=p.read_text(encoding='utf-8-sig');needle="if len(best_good)>=8:break\n\n   if len(best_good)<8:";replace="""if len(best_good)>=8:break
   if len(best_good)<3:
    # Fragmented segmentation may have labelled parts of the target as neighbours.
    # Removing that mask is a final, explicitly flagged recovery, not a clean fit.
    for altx,alty in [(x,y),(cx0,cy0)]:
     try:
      isos=run_ellipse(gaussian_filter(data,.7),mask,altx,alty,max(2,min(.3*rrseg,maxsma*.5)),.2,pa,maxsma)
      trial=profile_rows(isos,wcs,altx,alty,xa,ya,b);strict=[z for z in trial if accepted(z)];loose=[z for z in trial if accepted(z,True)]
      if (len(strict),len(loose))>(len(best_good),sum(accepted(z,True) for z in best)):
       best=trial;best_good=strict;xc=altx;yc=alty;chosen='neighbour_mask_removed';chosen_mask=mask;method='segmentation_mask_removed_recovery'
      if len(best_good)>=8:break
     except Exception as e:log.append('Segmentation recovery: '+str(e))
   if len(best_good)<8:"""
assert needle in s;s=s.replace(needle,replace)
s=s.replace("if 'neighbour_mask' in chosen:flags.append('star_mask_removed')", "if chosen=='neighbour_mask_removed':flags.append('neighbour_mask_removed')\n  elif 'neighbour_mask' in chosen:flags.append('star_mask_removed')")
p.write_text(s,encoding='utf8')
