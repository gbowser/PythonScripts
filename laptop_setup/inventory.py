from pathlib import Path
import os,sys,json,csv,hashlib,importlib,importlib.metadata as md,ctypes,struct
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT)); os.environ['FOREGROUND_MASKING_PC']='Laptop'
OUT=ROOT/'laptop_setup'/'verification'; OUT.mkdir(exist_ok=True)
from machine_paths import detect_pc,research_folder
research=research_folder('Laptop')
result={'machine':detect_pc(),'research':str(research),'packages':{}}
for package,module in [('numpy','numpy'),('scipy','scipy'),('astropy','astropy'),('photutils','photutils'),('matplotlib','matplotlib'),('pandas','pandas'),('sep','sep'),('optuna','optuna'),('Pillow','PIL'),('reportlab','reportlab'),('pypdf','pypdf'),('python-docx','docx')]:
    importlib.import_module(module);result['packages'][package]=md.version(package)
import tkinter as tk
import matplotlib;matplotlib.use('TkAgg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
window=tk.Tk();canvas=FigureCanvasTkAgg(Figure(),window);canvas.draw();window.update();window.destroy();result['tk']='TkAgg canvas rendered'
import numpy as np
from astropy.io import fits
sys.path.insert(0,str(ROOT/'Euclid/review_MER_VIS'))
import review_MER_VIS as review
campaign=json.loads((ROOT/'Euclid/review_MER_VIS/centre_policy_MER_VIS_campaign.json').read_text())
store=review.Store(research/'Euclid',OUT/'mer',campaign)
missing=[]
for row in store.rows:
    if not Path(row['fits_path']).is_file():missing.append(row['fits_path'])
profiles=research/'Euclid/Euclid_MER_VIS_geometry/profiles'
result['MER']={'rows':len(store.rows),'missing_fits':missing,'missing_campaign_profiles':[str(profiles/f"Euclid_{s['object_id']}_MER_VIS_ellipse_profile.csv") for s in store.sample if not (profiles/f"Euclid_{s['object_id']}_MER_VIS_ellipse_profile.csv").is_file()]}
originals=[store.manifest,*list((ROOT/'Euclid/review_MER_VIS/saved_reviews_centre_v3').glob('*.json'))]
result['preserved_hashes']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in originals}
# Record every embedded absolute path without altering source products.
audit=[]
for folder in [ROOT/'Euclid/review_MER_VIS',ROOT/'Euclid/reports/MER_VIS_current',research/'Remove foreground objects/clean22_haigh_aligned_bright150_galaxy150_sep_sensitivity']:
    for p in folder.rglob('*'):
        try:
            if p.suffix.lower() not in ('.json','.csv') or p.stat().st_size>20_000_000:continue
            text=p.read_text(encoding='utf-8-sig')
            if 'D:\\' in text or '/mnt/d/' in text:audit.append(str(p))
        except (OSError,UnicodeError):pass
result['files_with_desktop_paths']=audit
sys.path.insert(0,str(ROOT/'Foreground Masking/Interactive tools'))
import interactive_toy_objects_SEP_MTObjects as gui
mroot=research/'Remove foreground objects'
sep=gui.current_optimisation_winner(mroot,gui.SEP_WINNER_RELATIVE,'sep_toy_cross_validation_best.json')
mto=gui.current_optimisation_winner(mroot,gui.MTO_WINNER_RELATIVE,'mtobjects_toy_cross_validation_best.json')
assert sep and mto,'Missing selected parameter JSON'
result['parameters']={key:{'path':str(p),'label':gui.parameter_source_label(mroot,p,key),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for key,p in [('SEP',sep),('MTObjects',mto)]}
manifest=gui.display.DEFAULT_MANIFEST
rows=gui.display.read_manifest(manifest)
result['S4G']={'manifest':str(manifest),'rows':len(rows),'missing_images':[str(gui.display.image_path_for_pc(r,'Laptop')) for r in rows if not gui.display.image_path_for_pc(r,'Laptop').is_file()]}
engine=ROOT.parent/'mtobjects'
handle=os.add_dll_directory('C:/msys64/ucrt64/bin');result['native_libraries']={}
for name in gui.mto_processing.MTOBJECTS_REQUIRED_LIBS:
    p=engine/'mtolib/lib'/name; binary=p.read_bytes();offset=struct.unpack_from('<I',binary,0x3c)[0];machine=struct.unpack_from('<H',binary,offset+4)[0];ctypes.CDLL(str(p));result['native_libraries'][name]={'machine':hex(machine),'sha256':hashlib.sha256(binary).hexdigest(),'loaded':True}
(OUT/'inventory.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2),flush=True)
