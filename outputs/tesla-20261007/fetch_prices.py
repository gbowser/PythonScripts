import urllib.request,urllib.parse,json,sys,datetime
region=sys.argv[1].upper()
start='2026-05-06T00:00:00Z';end='2026-10-08T00:00:00Z'
def fetch(product,kind):
    base=f'https://api.octopus.energy/v1/products/{product}/electricity-tariffs/E-1R-{product}-{region}/{kind}/'
    url=base+'?'+urllib.parse.urlencode({'period_from':start,'period_to':end,'page_size':1500})
    result=[]
    while url:
        data=json.load(urllib.request.urlopen(url));result+=data['results'];url=data['next']
    return {'source':base,'results':result}
p={'region':region,'import':fetch('AGILE-24-10-01','standard-unit-rates'),'export':fetch('AGILE-OUTGOING-19-05-13','standard-unit-rates'),'standing':fetch('AGILE-24-10-01','standing-charges')}
json.dump(p,open('outputs/tesla-20261007/prices.json','w'));print({k:len(v['results']) for k,v in p.items() if isinstance(v,dict)})
