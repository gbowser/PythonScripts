"""Persist the latest edited account split separately from simulation snapshots."""
import json
import math
from pathlib import Path
ALLOCATION=Path(__file__).resolve().parent/'data'/'account_allocation.json'

def saved_allocation(names,fallback):
    if not ALLOCATION.exists(): return list(fallback)
    balances=json.loads(ALLOCATION.read_text(encoding='utf-8'))['balances']
    values=[float(balances[n]) for n in names]
    if any(not math.isfinite(v) or v<0 for v in values) or sum(values)<=0:
        raise ValueError('Saved account allocation must have a positive total and non-negative balances.')
    return values

def save_allocation(names,values):
    values=[float(v) for v in values]
    if any(not math.isfinite(v) or v<0 for v in values) or sum(values)<=0:
        raise ValueError('Reference allocation requires a positive total.')
    ALLOCATION.parent.mkdir(parents=True,exist_ok=True)
    temporary=ALLOCATION.with_suffix('.tmp')
    temporary.write_text(json.dumps({'balances':dict(zip(names,values))},indent=2),encoding='utf-8')
    temporary.replace(ALLOCATION)
