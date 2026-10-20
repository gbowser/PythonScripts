from pathlib import Path
p=Path('MER_VIS_pipeline_v2/recover_failed_MER_VIS_geometry.py');s=p.read_text(encoding='utf-8-sig');needle="method='standard';relaxed=False";replacement="""method='standard';relaxed=False
   if len(best_good)<3:
    # The peak may be a knot. Independently retry catalogue and local flux centroid.
    local=(np.hypot(xx-x,yy-y)<max(8,rrseg))&~mask
    wt=np.where(local,np.maximum(smooth,0),0);total=wt.sum()
    cx0=float((wt*xx).sum()/total) if total else x;cy0=float((wt*yy).sum()/total) if total else y
    for altx,alty in [(x,y),(cx0,cy0)]:
     for frac,angle in [(.25,pa),(.5,pa),(.35,(pa+np.pi/2)%np.pi),(.5,(pa+np.pi/4)%np.pi)]:
      try:
       isos=run_ellipse(data,mask_neighbours,altx,alty,max(2,min(frac*rrseg,maxsma*.6)),.2,angle,maxsma)
       trial=profile_rows(isos,wcs,altx,alty,xa,ya,b);strict=[z for z in trial if accepted(z)];loose=[z for z in trial if accepted(z,True)]
       if (len(strict),len(loose))>(len(best_good),sum(accepted(z,True) for z in best)):
        best=trial;best_good=strict;xc=altx;yc=alty;chosen='alternate_centre_neighbour_mask';chosen_mask=mask_neighbours;method='alternate_centre'
       if len(best_good)>=8:break
      except Exception as e:log.append('Alternate centre: '+str(e))
     if len(best_good)>=8:break
"""
s=s.replace(needle,replacement);p.write_text(s,encoding='utf8')
