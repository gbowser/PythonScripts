"""Isolated trials for source separation in the close-pair example; no adopted masks."""
import json
from pathlib import Path
import subprocess
import sys
import numpy as np
from scipy.ndimage import gaussian_filter
import masking_core as core


def trial(config):
    row=core.catalogue(core.DEFAULT_CATALOGUE)[0]
    data,bad,header,g,path=core.load_image(row)
    if config['residual_sigma']:
        finite=~bad
        sigma=config['residual_sigma']
        model=gaussian_filter(np.where(finite,data,0),sigma)/np.maximum(gaussian_filter(finite.astype(float),sigma),1e-10)
        data=data-model
    params=core.parameters(dict(gaussian_fwhm=config['fwhm'],move_factor=.9,minarea=1,dilation=1))
    labels,bg,bounds=core.detect_fit_galaxy(data,bad,g,params,core.ROOT/'mtobjects')
    centre=int(labels[round(g['y']),round(g['x'])])
    points={}
    for name,x,y in [('left',531,558),('right',562,547)]:
        label=int(labels[y,x]);points[name]=dict(label=label,centre_label=centre,
            same_as_centre=label==centre,area=int(np.sum(labels==label)) if label else 0,
            nearby_labels=[int(v) for v in np.unique(labels[y-3:y+4,x-3:x+4])])
    result=dict(config=config,points=points,background=bg)
    destination=core.HERE/'validation_output/knots'/f'trial_{config["residual_sigma"]}_{config["fwhm"]}.npz'
    np.savez_compressed(destination,segmentation=labels)
    return result


if __name__=='__main__':
    if len(sys.argv)>1:
        print(json.dumps(trial(json.loads(sys.argv[1]))))
    else:
        destination=core.HERE/'validation_output/knots'
        destination.mkdir(parents=True,exist_ok=True)
        reports=[]
        for residual in [0,3,5,8]:
            for fwhm in [0.,.5,1.]:
                config=dict(residual_sigma=residual,fwhm=fwhm)
                proc=subprocess.run([sys.executable,str(Path(__file__).resolve()),json.dumps(config)],capture_output=True,text=True,timeout=120)
                if proc.returncode:
                    print(proc.stderr[-1000:],flush=True);continue
                report=json.loads(proc.stdout.strip().splitlines()[-1]);reports.append(report)
                print(report,flush=True)
        core.json_write(destination/'separation_trials.json',reports)
