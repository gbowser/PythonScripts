import json,statistics,collections
from pathlib import Path
p=Path('MER_VIS_review_analysis_20261028/review_audit.json');doc=json.loads(p.read_text());rows=doc['galaxies'];usable=[r for r in rows if r['decisions']['disc']=='usable'];convincing=[r for r in rows if r['decisions']['bar']=='convincing']
counts={'usable_disc_with_PA':sum(r['final']['disc_pa'] is not None for r in usable),'usable_disc_with_inclination':sum(r['final']['inclination'] is not None for r in usable),'convincing_bar_with_PA':sum(r['final']['bar_pa'] is not None for r in convincing),'convincing_bar_without_PA':[r['id'] for r in convincing if r['final']['bar_pa'] is None],'marginal_pool':[r['id'] for r in rows if r['pool']=='marginal'],'final_issues':dict(collections.Counter(issue for r in rows for issue in r['final']['issues']))}
changes={}
for key in ['disc_pa','inclination','bar_pa']:
 values=[abs(r['deltas'][key]) for r in rows if key in r['deltas']];changes[key]={'n':len(values),'median_abs':statistics.median(values) if values else None,'max_abs':max(values) if values else None,'above5':sum(v>5 for v in values),'above10':sum(v>10 for v in values)}
print(json.dumps({'counts':counts,'changes':changes},indent=2))
print('LARGEST CHANGES')
for r in sorted((r for r in rows if 'disc_pa' in r['deltas']),key=lambda r:abs(r['deltas']['disc_pa']),reverse=True)[:9]:print(json.dumps({k:r[k] for k in ['id','category','decisions','notes','deltas','pool']}|{'n_disc':r['final']['n_disc'],'PA_RMS':r['final']['pa_scatter'],'original':r['baseline']['disc_pa'],'reviewed':r['final']['disc_pa']},ensure_ascii=False))
print('ORIGINAL ELLIPTICITY MEMBERS')
for r in rows:
 if r['category']=='ellipticity':print(json.dumps({'id':r['id'],'initial_eps_range':r['baseline']['eps_span'],'final_eps_range':r['final']['eps_span'],'initial_n':r['baseline']['n_disc'],'final_n':r['final']['n_disc'],'disc_edited':r['disc_bounds_changed'],'rule':r['decisions']['rule']}))
doc['summary']['availability']=counts;doc['summary']['angle_changes']=changes;p.write_text(json.dumps(doc,indent=2),encoding='utf8')
