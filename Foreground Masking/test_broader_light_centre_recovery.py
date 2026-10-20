from pathlib import Path
p=Path('MER_VIS_pipeline_v2/recover_failed_MER_VIS_geometry.py');s=p.read_text(encoding='utf-8-sig');needle="   if len(best_good)<8:\n    # Re-reference centre";add="""   if len(best_good)<3:
    # Visual QA of failed objects revealed catalogue positions on off-centre knots.
    # A broader, extended-light peak provides a new centre candidate, not a result.
    extended=gaussian_filter(np.where(mask,0,data),max(2,.1*rrseg))
    allowed=(np.hypot(xx-x,yy-y)<=max(8,1.5*rrseg))&~mask
    cyext,cxext=np.unravel_index(np.argmax(np.where(allowed,extended,-np.inf)),data.shape)
    for frac,angle in [(.2,pa),(.5,pa),(.3,(pa+np.pi/2)%np.pi)]:
     try:
      isos=run_ellipse(data,mask,cxext,cyext,max(2,min(frac*rrseg,maxsma*.6)),.2,angle,maxsma)
      trial=profile_rows(isos,wcs,cxext,cyext,xa,ya,b);strict=[z for z in trial if accepted(z)];loose=[z for z in trial if accepted(z,True)]
      if (len(strict),len(loose))>(len(best_good),sum(accepted(z,True) for z in best)):
       best=trial;best_good=strict;xc=cxext;yc=cyext;chosen='neighbour_mask_removed';chosen_mask=mask;method='extended_light_centre_recovery'
      if len(best_good)>=8:break
     except Exception as e:log.append('Extended-light centre: '+str(e))
""";assert needle in s;s=s.replace(needle,add+needle);p.write_text(s,encoding='utf8')
