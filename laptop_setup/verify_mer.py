from pathlib import Path
import sys,os,json,threading,urllib.request,time,unittest,tempfile
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'laptop_setup/verification';os.environ['FOREGROUND_MASKING_PC']='Laptop'
sys.path.insert(0,str(ROOT/'Euclid/review_MER_VIS'))
import review_MER_VIS as review
research=Path(r'C:\Users\gordo\Dropbox\Public Documents\UCLAN\MSc Research')
review.DEFAULT_DATA=research/'Euclid'
# Run the existing integration suite with an explicit laptop data root.
suite=unittest.defaultTestLoader.discover(str(ROOT/'Euclid/review_MER_VIS'),pattern='test_review_MER_VIS.py')
test=unittest.TextTestRunner(verbosity=2).run(suite)
result={'integration_tests':{'run':test.testsRun,'failures':len(test.failures),'errors':len(test.errors)}}
campaign=json.loads((ROOT/'Euclid/review_MER_VIS/centre_policy_MER_VIS_campaign.json').read_text())
store=review.Store(research/'Euclid',OUT/'mer',campaign)
server=review.LocalReviewServer(('127.0.0.1',0),review.Handler);server.store=store;server.token='laptop-verification'
thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();url=f'http://127.0.0.1:{server.server_port}'
def get(path):return urllib.request.urlopen(url+path).read()
result['health']=json.loads(get('/api/health'))
# Choose a campaign member with its original profile available.
for item in store.sample:
    oid=item['object_id'];galaxy=store.galaxy(oid)
    if galaxy.get('profile'):
        break
else:
    oid=store.sample[0]['object_id'];galaxy=store.galaxy(oid)
result['galaxy_id']=oid;result['galaxy_keys']=list(galaxy)
result['galaxy_response_bytes']=len(get('/api/galaxy?id='+oid)); result['image_response_bytes']=len(get('/api/image?id='+oid))
print('MER image/profile HTTP verified',oid,flush=True)
centre=galaxy['centre']
job=store.start_refit({'object_id':oid,'x':float(centre[0]),'y':float(centre[1]),'lock_centre':True})
print('Refit started',job,flush=True)
jobid=job['job_id'] if isinstance(job,dict) else job
for _ in range(300):
    status=store.refit_status(jobid)
    if status['status'] not in ('running','queued'):break
    time.sleep(1)
result['refit']={k:v for k,v in status.items() if k!='galaxy'}
server.shutdown();server.server_close();thread.join()
(OUT/'mer_results.json').write_text(json.dumps(result,indent=2,default=str));print(json.dumps(result,indent=2,default=str),flush=True)
