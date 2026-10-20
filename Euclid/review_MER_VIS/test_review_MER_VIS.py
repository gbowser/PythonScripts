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
        self.assertEqual(len({r['object_id'] for r in sample}),48)
        self.assertEqual(Counter(r['category'] for r in sample),dict(sparse=12,bar=12,ellipticity=12,variation=6,control=6))
        self.assertIn('-518633776290631360',[r['object_id'] for r in sample if r['category']=='sparse'])
        self.assertIn('-601121275504424227',[r['object_id'] for r in sample if r['category']=='variation'])
        bootstrap=self.get('/api/bootstrap');self.assertEqual(bootstrap['app'],APP_ID)

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
