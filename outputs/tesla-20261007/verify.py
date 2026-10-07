import json,datetime,re
d=json.load(open('outputs/tesla-20261007/data.json'));p=json.load(open('outputs/tesla-20261007/prices.json'))
rates={datetime.datetime.fromisoformat(x['valid_from'].replace('Z','+00:00')).timestamp():x['value_exc_vat']/100 for x in p['import']['results']}
periods=[('2026-05-23','2026-06-04',261.9,45.58,54.55),('2026-06-04','2026-07-04',686.7,64.99,84.98),('2026-07-04','2026-08-04',733.8,96.25,118.36),('2026-08-04','2026-09-04',784.6,144.59,169.11),('2026-09-04','2026-10-01',468.5,58.94,76.94),('2026-10-01','2026-10-04',79.6,21.19,22.79)]
result=[];total=homecost=baseline=0
for row in d['raw']:
    t=datetime.datetime.fromisoformat(row[0]);date=row[0][:10];bucket=t.replace(minute=30*(t.minute//30),second=0,microsecond=0).timestamp();rate=.2226 if date<'2026-05-23' else rates[bucket];vat=1.05 if date<'2026-10-01' else 1
    total+=row[16]/12000*rate*vat;homecost+=row[2]/12000*rate*vat;baseline+=row[2]/12000*.2226*vat
for lo,hi,kwh,energy,bill in periods:
    rr=[r for r in d['raw'] if lo<=r[0][:10]<hi]
    used=sum(r[16]/12000 for r in rr);cost=sum(r[16]/12000*rates[datetime.datetime.fromisoformat(r[0]).replace(minute=30*(int(r[0][14:16])//30),second=0,microsecond=0).timestamp()] for r in rr)
    result.append([lo,hi,kwh,used,energy,cost,bill]);print(result[-1])
json.dump(result,open('outputs/tesla-20261007/reconciliation.json','w'))
actualsc=sum((.4442 if r[0]<'2026-05-23' else .5313)*(1.05 if r[0]<'2026-10-01' else 1) for r in d['daily']);fixedsc=sum(.4442*(1.05 if r[0]<'2026-10-01' else 1) for r in d['daily'])
print('baseline',baseline+fixedsc,'actual',total+actualsc,'total saving',baseline+fixedsc-total-actualsc,'battery',homecost-total,'tariff',baseline+fixedsc-homecost-actualsc)
