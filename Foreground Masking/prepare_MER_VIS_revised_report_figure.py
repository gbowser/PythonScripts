from pathlib import Path
import numpy as np,csv
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
rows=list(csv.DictReader(open('MER_VIS_report_work/PA_convention_audit.csv')))
fig,axes=plt.subplots(1,2,figsize=(10.5,3))
for ax,subset,title in [(axes[0],rows,'All 2207 provisional fits'),(axes[1],[r for r in rows if r['unflagged']=='True'],'546 fits without quality flags')]:
 z=np.array([float(r['converted_plus90_hypothesis_difference_deg']) for r in subset]);ax.hist(z,bins=np.arange(-90,96,6),color='#36728c',edgecolor='white',linewidth=.4);ax.axvline(0,color='black',ls='--',lw=.8);ax.set(title=title,xlabel='Photutils disc PA minus adjusted Euclid PA (degrees)',ylabel='Galaxies',xlim=(-90,90));ax.tick_params(labelsize=8)
fig.tight_layout();fig.savefig('MER_VIS_report_work/pa_adopted_90.png',dpi=180);plt.close(fig)
