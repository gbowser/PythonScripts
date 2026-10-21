from pathlib import Path
import ast,json,math,sys
import numpy as np
sys.path.insert(0,str(Path(__file__).parent))
from review_MER_VIS import Store,DEFAULT_DATA
# Execute only the two existing numerical methods, without importing the GUI/application.
original=Path('Interactive tools/interactive_toy_objects_SEP_MTObjects.py')
tree=ast.parse(original.read_text(encoding='utf-8-sig'))
methods={n.name:n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name in ['_midtones_transfer','_autostretched_view']}
for n in methods.values():n.decorator_list=[]
namespace={'np':np,'math':math};exec(compile(ast.fix_missing_locations(ast.Module(body=list(methods.values()),type_ignores=[])),str(original),'exec'),namespace)
class Param:
 def __init__(self,value):self.value=value
 def get(self):return self.value
class Reference:
 _midtones_transfer=staticmethod(namespace['_midtones_transfer'])
 _autostretched_view=namespace['_autostretched_view']
 def __init__(self,shadows,target):self.autostretch_shadows=Param(shadows);self.autostretch_background=Param(target);self.stretch_mode=Param('AutoStretch')
store=Store(DEFAULT_DATA,Path('MER_VIS_review_tool/test_state'))
Path('MER_VIS_review_tool/test_galaxies.json').write_text(json.dumps([store.galaxy(x['object_id']) for x in store.sample]),encoding='utf8')
arrays=[np.random.default_rng(12).normal(.003,.001,10003),np.array([-.2,0,.1,.2,.3,.5,3]),np.full(20,.1)]
for oid in [store.sample[0]['object_id'],next(s['object_id'] for s in store.sample if s['category']=='control')]:
 g=store.galaxy(oid);params={k:[v] for k,v in zip(['x0','x1','y0','y1'],g['default_window'])};meta,body=store.image(oid,params);a=np.frombuffer(body,dtype='<f4');arrays.append(a[np.isfinite(a)].astype(float))
cases=[]
for a in arrays:
 med=float(np.median(a));stats=dict(minimum=float(a.min()),maximum=float(a.max()),median=med,robust_sigma=1.4826*float(np.median(abs(a-med))))
 probes=np.unique(np.r_[np.percentile(a,[0,1,5,25,50,75,95,99,100]),med])
 for shadows,target in [(-2.8,.25),(-1.5,.35)]:
  expected=Reference(shadows,target)._autostretched_view(probes,a)
  cases.append(dict(stats=stats,shadows=shadows,target=target,probes=probes.tolist(),expected=expected.tolist()))
Path('MER_VIS_review_tool/test_stf_vectors.json').write_text(json.dumps(cases),encoding='utf8');print('Built',len(cases),'AutoSTF reference cases from the earlier numerical methods')
