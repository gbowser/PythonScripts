import json, tempfile, threading, unittest
from pathlib import Path
from review_MER_VIS import Store
class StatusTests(unittest.TestCase):
 def test_status_preserves_assessment_and_exports(self):
  with tempfile.TemporaryDirectory() as tmp:
   s=Store.__new__(Store);s.byid={'123':{}};s.sample=[];s.digest='test';s.lock=threading.RLock();s.output=Path(tmp);s.review_path=s.output/'reviews.json';s.reviews={'123':dict(object_id='123',notes='Keep this note',settings={'disc':[1,2]},calculation={'disc_pa':45},reviewed_utc='old')}
   for state in [False,True,False]:
    r=s.set_reviewed({'object_id':'123','reviewed':state})['review'];self.assertEqual(r['reviewed'],state);self.assertEqual(r['notes'],'Keep this note');self.assertEqual(r['settings'],{'disc':[1,2]});self.assertEqual(r['calculation'],{'disc_pa':45});self.assertEqual(json.loads(s.review_path.read_text())['123']['reviewed'],state)
   self.assertIn('False',s.export_csv().decode('utf-8-sig'))
   for bad in [{'object_id':'123','reviewed':1},{'object_id':'unknown','reviewed':False}]:
    with self.assertRaises(ValueError):s.set_reviewed(bad)
   s.reviews={};r=s.set_reviewed({'object_id':'123','reviewed':True})['review'];self.assertTrue(r['reviewed']);self.assertEqual(r['disc_decision'],'not_assessed')
if __name__=='__main__':unittest.main()
