"""Local, compressed JSON snapshots. No executable pickle data."""
from datetime import date, datetime
from zoneinfo import ZoneInfo
from pathlib import Path
import gzip
import json
import uuid
import pandas as pd

STORE = Path(__file__).resolve().parent / 'data' / 'saved_runs'


def encode(value):
    if isinstance(value, pd.DataFrame):
        return {'__table__': value.to_json(orient='table', index=False, double_precision=15)}
    if isinstance(value, (date, datetime)):
        return {'__date__': value.isoformat()}
    if isinstance(value, dict):
        return {k: encode(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [encode(v) for v in value]
    if hasattr(value, 'item'):
        return value.item()
    return value


def decode(value):
    if isinstance(value, dict):
        if '__table__' in value:
            from io import StringIO
            return pd.read_json(StringIO(value['__table__']), orient='table')
        if '__date__' in value:
            return date.fromisoformat(value['__date__'][:10])
        return {k: decode(v) for k, v in value.items()}
    if isinstance(value, list):
        return [decode(v) for v in value]
    return value


def proposed_name(result):
    now = datetime.now(ZoneInfo('Europe/London')).strftime('%y%m%d-%H%M-')
    s = result['settings']
    label = f"Evelyn S{s['evelyn_scenario']}" if s.get('evelyn_scenario') else 'Custom'
    return now + label + (' shock' if s['crash_enabled'] else '') + (' property sale' if s['property_sale_enabled'] else '')


def run_path(run_id, directory=STORE):
    # Only opaque IDs are used as filenames, never user-entered names.
    uuid.UUID(run_id)
    return Path(directory) / (run_id + '.json.gz')


def save_run(name, result, controls, directory=STORE):
    if not name.strip():
        raise ValueError('Enter a run name.')
    run_id = str(uuid.uuid4())
    target = run_path(run_id, directory)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(version=1, id=run_id, name=name.strip(),
                   saved_at=datetime.now(ZoneInfo('Europe/London')).isoformat(),
                   result=result, controls=controls)
    temp = target.with_suffix('.tmp')
    with gzip.open(temp, 'wt', encoding='utf-8', compresslevel=9) as stream:
        json.dump(encode(payload), stream, allow_nan=False)
    temp.replace(target)
    metadata = {k:payload[k] for k in ['version','id','name','saved_at']}
    metadata['settings'] = result['settings']
    meta = target.with_suffix('.meta.json')
    meta_temp = meta.with_suffix('.tmp')
    meta_temp.write_text(json.dumps(metadata),encoding='utf-8')
    meta_temp.replace(meta)
    return run_id


def load_run(run_id, directory=STORE):
    with gzip.open(run_path(run_id, directory), 'rt', encoding='utf-8') as stream:
        payload = decode(json.load(stream))
    if payload.get('version') != 1:
        raise ValueError('Unsupported saved-run version.')
    return payload


def list_runs(directory=STORE):
    runs, errors = [], []
    for path in Path(directory).glob('*.json.gz'):
        try:
            meta = path.with_suffix('.meta.json')
            payload = json.loads(meta.read_text(encoding='utf-8')) if meta.exists() else load_run(path.name[:-8], directory)
            s = payload.get('settings') or payload['result']['settings']
            runs.append(dict(id=payload['id'], Name=payload['name'], Saved=payload['saved_at'],
                             Gift=s.get('gift'), Gift_years=s.get('gift_years'),
                             Mean_y=s.get('initial_y'), Std_dev=s.get('std_y'),
                             Shock=s['crash_enabled'], Property_sale=s['property_sale_enabled'], Parameters=s, Size_KB=round(path.stat().st_size/1024,1)))
        except (OSError, ValueError, KeyError, TypeError) as error:
            errors.append(f'{path.name}: {error}')
    return sorted(runs, key=lambda r: r['Saved'], reverse=True), errors


def delete_runs(ids, directory=STORE):
    for run_id in ids:
        target=run_path(run_id,directory)
        target.unlink(missing_ok=True)
        target.with_suffix('.meta.json').unlink(missing_ok=True)


def compare_runs(baseline, alternative, value='portfolio_real', percentile='p50'):
    a, b = baseline['result'], alternative['result']
    if a['settings']['start_date'] != b['settings']['start_date']:
        raise ValueError('Compare runs with the same valuation date so real pounds and years are aligned.')
    def series(result):
        table=result['quantiles']
        return table.loc[table['value']==value].set_index('year')[percentile]
    x, y = series(a).align(series(b), join='inner')
    return pd.DataFrame({'year': x.index, 'Baseline': x.values, 'Comparison': y.values,
                         'Delta': (y-x).values})


def paired_deltas(baseline, alternative, value='portfolio_real'):
    """Common-random-number comparisons, not differences of marginal quantiles."""
    a,b=baseline['result'],alternative['result']
    fields=['start_date','seed','simulations','years','non_stochastic']
    labels={'start_date':'valuation date','seed':'random seed','simulations':'simulation count',
            'years':'projection years','non_stochastic':'non-stochastic mode'}
    mismatch=[f"{labels[key]} (baseline: {a['settings'].get(key)}, comparison: {b['settings'].get(key)})"
              for key in fields if a['settings'].get(key)!=b['settings'].get(key)]
    if mismatch:
        raise ValueError('Incompatible pairing parameters: '+ '; '.join(mismatch)+'.')
    # A revised engine can change RNG consumption or path numbering.
    if a['inputs'].get('model_revision') != b['inputs'].get('model_revision'):
        raise ValueError('Paired paths require the same model revision.')
    left=a['details'].set_index(['simulation','year'])[value]
    right=b['details'].set_index(['simulation','year'])[value]
    if not left.index.is_unique or not right.index.is_unique or set(left.index)!=set(right.index):
        raise ValueError('Saved path/year observations do not match.')
    difference=(right-left).rename('Delta').reset_index()
    q=difference.groupby('year').Delta.quantile([i/10 for i in range(1,10)]).unstack()
    q.columns=[f'p{round(c*100)}' for c in q.columns]
    return difference,q.reset_index()
