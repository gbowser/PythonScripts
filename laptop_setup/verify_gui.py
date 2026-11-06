from pathlib import Path
import os,sys,json,argparse
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'laptop_setup/verification';os.environ['FOREGROUND_MASKING_PC']='Laptop'
sys.path.insert(0,str(ROOT/'Foreground Masking/Interactive tools'))
import interactive_toy_objects_SEP_MTObjects as gui
import numpy as np
from astropy.io import fits
config=ROOT/'laptop_setup/config';research=gui.research_output_root('Laptop')
args=argparse.Namespace(pc='Laptop',manifest=gui.display.DEFAULT_MANIFEST,mtobjects_root=ROOT.parent/'mtobjects',sep_best=config/'sep-diagnostic-rejected-fold20.json',mto_best=research/gui.CURRENT_OPTIMISATION_DIR/gui.MTO_WINNER_RELATIVE,injection_manifest=config/'paired-injections-laptop.json',output=OUT/'comparison')
def fail(title,message):raise RuntimeError(f'{title}: {message}')
gui.messagebox.showerror=fail;gui.messagebox.showwarning=fail
app=gui.CombinedToyTester(args)
try:
    app.update();assert app.data is not None
    # Exercise one exact saved injection set on a current clean-22 galaxy.
    label=next(label for label,name in app.label_to_name.items() if name=='NGC4765')
    app.galaxy_var.set(label);app.load_galaxy()
    app.batch_set_var.set(app.batch_set_labels['training_seed_1'])
    app.load_batch_toy_set();assert app.batch_delta is not None
    # Use one actual galaxy; native GUI, no broad batch processing.
    name=app.label_to_name[app.galaxy_var.get()];print('GUI opened',name,app.data.shape,flush=True)
    app.calculate();app.update();assert set(app.last_results)=={'SEP','MTObjects'}
    app.save_png();stats={}
    for method,p in app.last_results.items():
        mask=p['mask'];cleaned=p['cleaned'];assert mask.shape==app.data.shape and mask.dtype==bool
        assert np.isfinite(cleaned[np.isfinite(app.data)]).all()
        for key in ['mask','cleaned']:
            fits.writeto(OUT/'comparison'/f'{name}_{method}_{key}.fits',p[key].astype('uint8' if key=='mask' else 'float32'),overwrite=True)
        stats[method]={'masked_pixels':int(mask.sum()),'shape':list(mask.shape),'finite_recovered':True,'objects':len(p['objects'])}
    # Also load one immutable batch injection, checking the laptop path copy.
    values=app.batch_set_combo['values'] if hasattr(app,'batch_set_combo') else []
    result={'galaxy':name,'parameters':{'SEP':str(args.sep_best),'MTObjects':str(args.mto_best)},'methods':stats,'status':app.status.get(),'output':str(args.output)}
    (OUT/'gui_results.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2),flush=True)
finally:app.destroy()
