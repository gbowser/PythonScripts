import csv, json, math
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
RESEARCH = Path(r'D:\Dropbox\Public Documents\UCLAN\MSc Research\Remove foreground objects')
MANIFEST = ROOT / 'Erwin_s4g_image_downloader/geometry_output/s4g_image_geometry_manifest.csv'
def read_csv(p):
    with p.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))
def header(p):
    result = {}
    with p.open('rb') as f:
        while True:
            block = f.read(2880)
            if len(block) != 2880: raise ValueError('Invalid FITS header')
            for i in range(0,2880,80):
                card = block[i:i+80].decode('ascii')
                key = card[:8].strip()
                if key == 'END': return result
                if card[8:10] != '= ': continue
                value = card[10:].split('/')[0].strip()
                if value.startswith("'"): value = value.strip("' ")
                else:
                    try: value = float(value.replace('D','E'))
                    except ValueError: pass
                result[key] = value
def centre(h, x, y):
    assert h['CTYPE1'] == 'RA---TAN' and h['CTYPE2'] == 'DEC--TAN', h
    dx,dy = x-h['CRPIX1'],y-h['CRPIX2']
    def sip(prefix):
        total=0.0
        for key,value in h.items():
            parts=key.split('_')
            if len(parts)==3 and parts[0]==prefix and parts[1].isdigit() and parts[2].isdigit():
                total+=value*dx**int(parts[1])*dy**int(parts[2])
        return total
    dx,dy=dx+sip('A'),dy+sip('B')
    xi = math.radians(h['CD1_1']*dx+h['CD1_2']*dy)
    eta = math.radians(h['CD2_1']*dx+h['CD2_2']*dy)
    a,d = math.radians(h['CRVAL1']), math.radians(h['CRVAL2'])
    denom = math.cos(d)-eta*math.sin(d)
    ra = (math.degrees(a+math.atan2(xi,denom)))%360
    dec = math.degrees(math.atan2(math.sin(d)+eta*math.cos(d),math.hypot(denom,xi)))
    return ra,dec
def sex(value, ra=False):
    sign = '' if ra else ('+' if value>=0 else '-')
    value=abs(value)/(15 if ra else 1)
    seconds=round(value*3600,2)
    hours=int(seconds//3600); minutes=int(seconds%3600//60); s=seconds%60
    return f'{sign}{hours:02d}:{minutes:02d}:{s:05.2f}'
decisions={}
for p in RESEARCH.rglob('*decisions.csv'):
    for row in read_csv(p):
        status=row.get('classification') or row.get('blind_decision')
        if status not in ('Clean','Ambiguous','Polluted'): continue
        name=row['name'].strip()
        if name not in decisions or row.get('reviewed_at','')>decisions[name]['reviewed_at']:
            decisions[name]={'status':status,'reviewed_at':row.get('reviewed_at',''),'notes':row.get('notes',''),'source':p.name}
gui={r['name']:r['classification'] for r in read_csv(RESEARCH/'clean_candidate_union_rereview/candidate_union_rereview_decisions.csv')}
fornax_ra=(3+38/60+29.083/3600)*15
fornax_dec=-(35+27/60+2.67/3600)
rows=[]
for r in sorted(read_csv(MANIFEST),key=lambda r:r['name']):
    p=Path(r['image_path']); h=header(p)
    ra,dec=centre(h,float(r['center_x_pix']),float(r['center_y_pix']))
    assert 0<=ra<360 and -90<=dec<=90
    # Independent stable haversine calculation for checking Excel's cosine formula.
    a,d,ac,dc=map(math.radians,(ra,dec,fornax_ra,fornax_dec))
    hav=math.sin((d-dc)/2)**2+math.cos(d)*math.cos(dc)*math.sin((a-ac)/2)**2
    separation=math.degrees(2*math.asin(math.sqrt(min(1,max(0,hav)))))
    review=decisions.get(r['name'],{})
    rows.append({'name':r['name'],'status':review.get('status','Unreviewed'),'ra':ra,'dec':dec,'ra_sex':sex(ra,True),'dec_sex':sex(dec),'hemisphere':'North' if dec>0 else 'South' if dec<0 else 'Equator','separation':separation,'reviewed_at':review.get('reviewed_at',''),'notes':review.get('notes',''),'status_source':review.get('source','No recorded categorical review'),'coordinate_source':p.name,'gui_status':gui.get(r['name'],'Unreviewed'),'frame':h.get('RADESYS',''),'equinox':h.get('EQUINOX','')})
assert len(rows)==182 and len({r['name'] for r in rows})==182
assert all(r['frame']=='ICRS' for r in rows)
payload={'rows':rows,'fornax_ra':fornax_ra,'fornax_dec':fornax_dec}
(OUT/'population.json').write_text(json.dumps(payload,indent=2),encoding='utf-8')
print(json.dumps({'galaxies':len(rows),'status_counts':dict(Counter(r['status'] for r in rows)),'hemisphere_counts':dict(Counter(r['hemisphere'] for r in rows)),'closest':sorted(rows,key=lambda r:r['separation'])[:3]},indent=2))
