"""Integration checks use isolated review output; source FITS/geometry stay read-only."""
import hashlib
import json
import tempfile
import threading
import unittest
import urllib.request
import urllib.error
from pathlib import Path
from collections import Counter
import numpy as np
from astropy.io import fits
from review_MER_VIS import Store, Handler, ThreadingHTTPServer, DEFAULT_DATA, APP_ID


class ReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="MER_VIS_review_test_")
        cls.store = Store(DEFAULT_DATA, Path(cls.temp.name))
        cls.hash_before = hashlib.sha256(cls.store.manifest.read_bytes()).hexdigest()
        cls.server = ThreadingHTTPServer(("127.0.0.1",0),Handler)
        cls.server.store,cls.server.token = cls.store,"test-token"
        cls.url=f"http://127.0.0.1:{cls.server.server_port}"
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join()
        assert hashlib.sha256(cls.store.manifest.read_bytes()).hexdigest()==cls.hash_before
        cls.temp.cleanup()

    def get(self,path):
        return json.loads(urllib.request.urlopen(self.url+path).read())

    def test_sample_and_documented_examples(self):
        sample=self.store.sample
        self.assertEqual(len({r['object_id'] for r in sample}),58)
        self.assertEqual(Counter(r['category'] for r in sample),dict(sparse=12,bar=12,ellipticity=12,variation=6,control=12,failed=4))
        reference=[self.store.byid[s['object_id']] for s in sample if s['category']=='control']
        self.assertTrue(all(not r['codex_quality_flags'] for r in reference))
        self.assertEqual(sum('nearly_face_on' in r['codex_information'] for r in reference),6)
        self.assertIn('-518633776290631360',[r['object_id'] for r in sample if r['category']=='sparse'])
        self.assertIn('-601121275504424227',[r['object_id'] for r in sample if r['category']=='variation'])
        bootstrap=self.get('/api/bootstrap');self.assertEqual(bootstrap['app'],APP_ID)

    def test_existing_sample_and_reviews_survive_expansion(self):
        folder=Path(self.temp.name)/'migration';folder.mkdir()
        old=[r for r in self.store.sample if r['category']!='failed' and not (r['category']=='control' and 'nearly_face_on' in self.store.byid[r['object_id']]['codex_information'])]
        self.assertEqual(len(old),48)
        document=dict(app=APP_ID,source_sha256=self.hash_before,sample=old)
        (folder/'MER_VIS_review_sample.json').write_text(json.dumps(document))
        review_file=folder/'MER_VIS_saved_reviews.json'
        review_file.write_text(json.dumps({old[0]['object_id']:{'notes':'Preserve my existing review'}}))
        before=review_file.read_bytes();updated=Store(DEFAULT_DATA,folder)
        self.assertEqual(len(updated.sample),58)
        self.assertTrue({r['object_id'] for r in old}.issubset({r['object_id'] for r in updated.sample}))
        self.assertEqual(review_file.read_bytes(),before)
        self.assertEqual(len(Store(DEFAULT_DATA,folder).sample),58)

    def test_all_failed_galaxies_are_reviewable(self):
        failed=[r for r in self.store.rows if r['codex_fit_status']=='fit_failed']
        group={s['object_id'] for s in self.store.sample if s['category']=='failed'}
        self.assertEqual(group,{r['object_id'] for r in failed})
        for row in failed:
            galaxy=self.get('/api/galaxy?id='+row['object_id'])
            self.assertEqual(galaxy['original']['status'],'fit_failed')
            self.assertTrue(galaxy['fit_error'])
            self.assertEqual(galaxy['centre'],[None,None])
            self.assertIsNone(galaxy['original']['disc_pa'])
            meta,body=self.store.image(row['object_id'],dict(x0=['0'],x1=['30'],y0=['0'],y1=['30']))
            self.assertGreater(len(body),0)
            self.assertGreater(meta['width'],0)

    def test_refit_validation_and_origin(self):
        oid='-586374330510251740'
        for payload in [dict(object_id=oid,x=-1,y=2),dict(object_id=oid,x=float('nan'),y=2),dict(object_id=oid,x=True,y=2),dict(object_id='unknown',x=2,y=2)]:
            with self.assertRaises((ValueError,KeyError)):self.store.start_refit(payload)
        for job in ['../outside','g'*32]:
            with self.assertRaises(ValueError):self.store.refit_status(job)
        req=urllib.request.Request(self.url+'/api/refit',data=b'{}',headers={'Content-Type':'application/json','Origin':'https://not-local.example','X-Review-Token':'test-token'})
        with self.assertRaises(urllib.error.HTTPError) as error:urllib.request.urlopen(req)
        self.assertEqual(error.exception.code,403)

    def test_native_pixels_and_byte_orientation(self):
        oid='-518633776290631360'
        galaxy=self.get('/api/galaxy?id='+oid)
        self.assertEqual(galaxy['original']['n_disc'],3)
        params=dict(x0=['700'],x1=['732'],y0=['700'],y1=['732'])
        meta,body=self.store.image(oid,params)
        self.assertEqual(meta['factor'],1)
        array=np.frombuffer(body,dtype='<f4').reshape(meta['height'],meta['width'])
        with fits.open(self.store.byid[oid]['fits_path'],memmap=True) as hd:
            np.testing.assert_equal(array,np.asarray(hd[0].section[700:732,700:732],dtype=np.float32))

    def test_unknown_objects_and_invalid_origin_do_not_write(self):
        with self.assertRaises(urllib.error.HTTPError) as error:self.get('/api/galaxy?id=../../unknown')
        self.assertEqual(error.exception.code,400)
        body=json.dumps(dict(object_id='-518633776290631360')).encode()
        req=urllib.request.Request(self.url+'/api/review',data=body,headers={'Content-Type':'application/json','Origin':'https://not-local.example','X-Review-Token':'test-token'})
        with self.assertRaises(urllib.error.HTTPError) as error:urllib.request.urlopen(req)
        self.assertEqual(error.exception.code,403)

    def test_review_round_trip_and_resume(self):
        payload=dict(object_id='-518633776290631360',disc_decision='uncertain',bar_decision='not_assessed',centre_decision='looks_correct',rule_action='improve',notes='TEST ONLY: isolated output folder',settings={'disc':[2.2,4.5]},calculation={'n_disc':3})
        req=urllib.request.Request(self.url+'/api/review',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json','Origin':self.url,'X-Review-Token':'test-token'})
        response=json.loads(urllib.request.urlopen(req).read());self.assertTrue(response['saved'])
        resumed=Store(DEFAULT_DATA,Path(self.temp.name));self.assertEqual(resumed.reviews[payload['object_id']]['notes'],payload['notes'])
        self.assertIn(b'TEST ONLY',resumed.export_csv())


if __name__=='__main__':unittest.main(verbosity=2)
