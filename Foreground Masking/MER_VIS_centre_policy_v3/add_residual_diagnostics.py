from pathlib import Path
p=Path('MER_VIS_review_tool/fit_manual_centre_MER_VIS.py');s=p.read_text(encoding='utf8')
s=s.replace('best=[];best_good=[];chosen=', 'best=[];best_isos=[];best_good=[];chosen=',1)
s=s.replace('best=p;best_good=good;', 'best=p;best_isos=isos;best_good=good;',1)
s=s.replace("if sum(accepted(z) for z in extra)>=2:best=", "if sum(accepted(z) for z in extra)>=2:best_isos=[iso for iso in best_isos if iso.sma<outer]+[iso for iso in isos if iso.sma>=outer];best=",1)
s=s.replace('if len(g)>len(best_good):best=p;best_good=g', 'if len(g)>len(best_good):best=p;best_isos=isos;best_good=g',1)
needle="  if profile:write_csv(out/'profiles'/f'Euclid_{oid}_MER_VIS_ellipse_profile.csv',profile)"
addition='''  if profile and 'best_isos' in locals() and len(best_isos)>=3:
   try:
    from photutils.isophote import build_ellipse_model,IsophoteList
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from astropy.visualization import simple_norm
    radii={round(z['sma_fit_pix'],8) for z in profile if accepted(z,relaxed)}
    retained=[iso for iso in best_isos if round(float(iso.sma),8) in radii]
    if len(retained)>=3:
     model=build_ellipse_model(data.shape,IsophoteList(sorted(retained,key=lambda z:z.sma)),fill=np.nan)
     science=np.where(chosen_mask,np.nan,data);residual=np.where(chosen_mask,np.nan,data-model)
     finite_data=science[np.isfinite(science)];norm=simple_norm(finite_data,stretch='asinh',min_cut=float(np.percentile(finite_data,2)),max_cut=float(np.percentile(finite_data,99.7)))
     fig,axes=plt.subplots(1,3,figsize=(12,4),layout='constrained')
     for ax,array,title in zip(axes,[science,model,residual],['Background-subtracted science','Photutils elliptical model','Science − model (±5 sky noise)']):
      if ax is axes[2]:ax.imshow(array,origin='lower',cmap='coolwarm',vmin=-5*noise,vmax=5*noise)
      else:ax.imshow(array,origin='lower',cmap='gray',norm=norm)
      ax.plot((x0-xa+.5)/b-.5,(y0-ya+.5)/b-.5,'+',color='#ffd35c',markersize=8);ax.set_title(title,fontsize=10);ax.set_axis_off()
     fig.suptitle(f'{oid} · fixed reference; residual structure can include real bars/arms',fontsize=11)
     dest=out/'diagnostics';dest.mkdir(exist_ok=True);fig.savefig(dest/f'Euclid_{oid}_MER_VIS_model_residual.png',dpi=125);plt.close(fig)
     r['centre_diagnostic_png']=str(dest/f'Euclid_{oid}_MER_VIS_model_residual.png');r['centre_model_isophotes']=len(retained)
   except Exception as diagnostic_error:log.append('Model diagnostic: '+str(diagnostic_error));r['centre_diagnostic_error']=str(diagnostic_error)
'''
assert needle in s;s=s.replace(needle,needle+'\n'+addition,1);p.write_text(s,encoding='utf8')
