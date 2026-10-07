from pathlib import Path
from pypdf import PdfReader
folder=Path(r'd:\Dropbox\My Documents\Home Finances\Energy Bills\House Octopus July 2021')
parts=[]
for p in sorted(folder.glob('octopus-energy-statement-2026-*.pdf')):
    text='\n'.join(page.extract_text() or '' for page in PdfReader(p).pages)
    parts.append(p.name+'\n'+text)
    lines=text.splitlines()
    print('\n'+p.name)
    for i,l in enumerate(lines):
        if any(k in l.lower() for k in ['agile','standing charge','tariff name','tariff code','vat','unit rate','electricity charges']):
            print(' | '.join(lines[max(0,i-1):i+3]))
Path('outputs/tesla-20261007/bills.txt').write_text('\n\n'.join(parts),encoding='utf8')
