import csv,zipfile,json,datetime,collections
z=zipfile.ZipFile('HomeEnergy/tesla-energy-2026.zip')
raw=[]; daily=[]; seen=set(); gaps=[]
for name in sorted(z.namelist()):
    rows=list(csv.DictReader(z.read(name).decode('utf-8-sig').splitlines()))
    vals=[0.0]*20; hours=[0.0]*48; count=0
    for r in rows:
        t=datetime.datetime.fromisoformat(r['Timestamp']); key=t.isoformat()
        if key in seen: raise ValueError('Duplicate '+key)
        seen.add(key); nums=[float(r[k]) for k in list(r)[2:]]
        raw.append([key,r['Display time']]+nums)
        vals=[a+b/12000 for a,b in zip(vals,nums)]
        hours[t.hour*2+t.minute//30]+=nums[14]/12000
        count+=1
    daily.append([name[13:23],count,count/12]+vals+hours)
ts=[datetime.datetime.fromisoformat(r[0]) for r in raw]
for a,b in zip(ts,ts[1:]):
    if (b-a).total_seconds()!=300:gaps.append([a.isoformat(),b.isoformat(),(b-a).total_seconds()/60])
headers=list(rows[0])[2:22]
out={'raw':raw,'daily':daily,'headers':headers,'gaps':gaps,'start':raw[0][0],'end':raw[-1][0],'files':len(daily)}
json.dump(out,open('outputs/tesla-20261007/data.json','w'))
print(json.dumps({k:out[k] for k in ['start','end','files','gaps']}))
print(dict(zip(headers,[sum(r[3+i] for r in daily) for i in range(20)])))
print('Incomplete days',[(r[0],r[1]) for r in daily if r[1]!=288])
