"""Read the newest Evelyn positions export without changing source files."""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import math
from zipfile import BadZipFile
from openpyxl import load_workbook

POSITIONS_FOLDER=Path(r'D:\Dropbox\My Documents\Home Finances\Pension')
ACCOUNTS=['Gordon GIA','Gordon ISA','Gordon SIPP','Ann GIA','Ann ISA','Ann SIPP']
EQUITY_TYPES={'Japan Collectives','UK Collectives','Europe Collectives','North America Collectives',
    'Emerging Markets Collectives','Asia Pacific Collectives','Direct Equity','Sector Equity Energy',
    'Global Equity Income','Global Small/Mid-Cap Equity','Global Large-Cap Blend Equity','US Large-Cap Blend Equity'}


def newest_positions(folder=POSITIONS_FOLDER):
    files=[p for p in Path(folder).iterdir() if p.is_file() and p.name.lower().startswith('positions') and p.suffix.lower()=='.xlsx' and not p.name.startswith('~$')]
    if not files: raise ValueError('No positions*.xlsx file found in '+str(folder))
    return max(files,key=lambda p:(p.stat().st_mtime_ns,p.name.lower()))


def number(value,label):
    try: result=float(value)
    except (ValueError,TypeError): raise ValueError('Missing or invalid '+label)
    if not math.isfinite(result): raise ValueError('Invalid '+label)
    return result


def account_name(value):
    text=str(value).upper()
    owner='Gordon' if text.startswith('GORDON BOWSER ') else 'Ann' if text.startswith('ANN BOWSER ') else None
    if owner is None: raise ValueError('Unrecognised account owner: '+str(value))
    wrapper='SIPP' if '.SIPP.' in text else 'ISA' if '.ISA.' in text else 'GIA' if '.DIM.' in text else None
    if wrapper is None: raise ValueError('Unrecognised account wrapper: '+str(value))
    return owner+' '+wrapper


def read_positions(folder=POSITIONS_FOLDER):
    path=newest_positions(folder)
    try: wb=load_workbook(path,read_only=True,data_only=True)
    except BadZipFile as error: raise ValueError('Newest positions file is not a readable XLSX: '+path.name) from error
    accounts={n:dict(value=0.0,gain=0.0,income=0.0,dividends=0.0,interest=0.0,gilt_gain=0.0,positions=0) for n in ACCOUNTS}
    audit=[]
    required={'Instrument Name','Valuation','Valuation Currency','Unrealized PL','Unrealized PL Currency','annualIncome','annualIncomeCurrency','accountName','securityType'}
    found=False
    try:
        for sheet in wb:
            rows=sheet.iter_rows(values_only=True)
            headers=next(rows,())
            if not required<=set(headers): continue
            if found: raise ValueError('Multiple position tables found; refusing to double count.')
            found=True
            for row_num,row in enumerate(rows,2):
                if not any(v is not None for v in row): continue
                r=dict(zip(headers,row));name=account_name(r['accountName'])
                for column in ['Valuation Currency','Unrealized PL Currency','annualIncomeCurrency']:
                    if str(r[column]).strip().upper()!='GBP': raise ValueError(f'{sheet.title} row {row_num}: {column} is not GBP; currency conversion is unavailable.')
                value=number(r['Valuation'],'valuation');gain=number(r['Unrealized PL'],'unrealised gain');income=number(r['annualIncome'],'annual income')
                if value<0 or income<0: raise ValueError('Negative valuation/income requires manual review.')
                item=accounts[name];item['value']+=value;item['gain']+=gain;item['income']+=income;item['positions']+=1
                kind=None
                gilt=str(r['Instrument Name']).upper().startswith('UK (GOVT OF)')
                if name.endswith('GIA'):
                    if gilt or r['securityType']=='Cash': kind='interest'
                    elif r['securityType'] in EQUITY_TYPES: kind='dividends'
                    elif income==0: kind='unclassified zero estimate'
                    else: raise ValueError(f"Cannot classify GIA income for {r['Instrument Name']} ({r['securityType']}); no fields were imported.")
                    if kind in ['interest','dividends']: item[kind]+=income
                    if gilt: item['gilt_gain']+=gain
                    audit.append(dict(account=name,instrument=r['Instrument Name'],classification=kind,estimated_annual_income=income,unrealised_gain=gain,gilt=gilt,source_row=row_num))
        if not found: raise ValueError('Required Evelyn positions headers not found.')
        if any(not v['positions'] for v in accounts.values()): raise ValueError('The export must contain all six accounts; no fields were imported.')
        for name,item in accounts.items():
            if item['value']<=0: raise ValueError('Account has no positive value: '+name)
            item['income_yield']=item['income']/item['value']
            if name.endswith('GIA'):
                if item['income']<=0: raise ValueError('Cannot calculate dividend share with zero GIA income: '+name)
                item['dividend_share']=item['dividends']/item['income']
    finally: wb.close()
    return dict(file=str(path.resolve()),file_saved=datetime.fromtimestamp(path.stat().st_mtime,ZoneInfo('Europe/London')).isoformat(),
        accounts=accounts,total=sum(v['value'] for v in accounts.values()),audit=audit,
        notes=['Annual income is the provider estimate, not a tax voucher. Equity-fund income is classified as dividends; cash and direct UK gilt income as interest.',
               'Unrealised gain is the export total, including CGT-exempt gilt gains. It is not a verified taxable gain or adjusted tax cost.',
               'A zero annualIncome estimate can omit accumulation-fund income or excess reportable income. Confirm against tax statements.'])
