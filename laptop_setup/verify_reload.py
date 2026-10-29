import os,sys,argparse
from pathlib import Path
root=Path.cwd();os.environ['FOREGROUND_MASKING_PC']='Laptop';sys.path.insert(0,str(root/'Foreground Masking/Interactive tools'))
import interactive_toy_objects_SEP_MTObjects as gui
config=root/'laptop_setup/config';research=gui.research_output_root('Laptop')
args=argparse.Namespace(pc='Laptop',manifest=gui.display.DEFAULT_MANIFEST,mtobjects_root=root.parent/'mtobjects',sep_best=config/'sep-diagnostic-rejected-fold20.json',mto_best=research/gui.CURRENT_OPTIMISATION_DIR/gui.MTO_WINNER_RELATIVE,injection_manifest=config/'paired-injections-laptop.json',output=root/'laptop_setup/verification/comparison')
app=gui.CombinedToyTester(args)
try:
    app.reload_optimised_parameters()
    assert app.sep_best==args.sep_best and app.mto_best==args.mto_best
    print('PASS: GUI reload preserves both explicit parameter sources')
finally:app.destroy()
