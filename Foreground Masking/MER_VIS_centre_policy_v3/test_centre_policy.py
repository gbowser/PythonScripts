import json,math,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path('MER_VIS_review_tool').resolve()))
from centre_policy_MER_VIS import centre_measurement,checked_policy,numerical_acceptance,DEFAULT_POLICY
class CentreTests(unittest.TestCase):
 def test_limits_and_reference(self):
  for scale in [.1,.2]:
   # Native cap independent of any fitting binning; floor protects small ellipses.
   a=centre_measurement(dict(x_original_pix=13,y_original_pix=20,sma_arcsec=20),[10,20],scale)
   self.assertTrue(a['centre_accepted']);self.assertEqual(a['centre_limit_native_pix'],3)
   b=centre_measurement(dict(x_original_pix=13.01,y_original_pix=20,sma_arcsec=20),[10,20],scale)
   self.assertFalse(b['centre_accepted']);self.assertIn('exceeds',b['centre_rejection_reason'])
  small=centre_measurement(dict(x_original_pix=11,y_original_pix=20,sma_arcsec=.1),[10,20],.1);self.assertEqual(small['centre_limit_native_pix'],1)
 def test_no_relaxed_centre_bypass(self):
  p=dict(valid=True,stop_code=2,sampled_fraction=.6,ellipticity_error=.15,pa_error_deg=15,intensity=1)
  self.assertFalse(numerical_acceptance(p));self.assertTrue(numerical_acceptance(p,True))
  centre=centre_measurement(dict(x_original_pix=15,y_original_pix=20,sma_arcsec=10),[10,20],.1)
  self.assertFalse(centre['centre_accepted'])
 def test_invalid_policy(self):
  for p in [dict(cap_native_pixels=0),dict(fraction_radius=float('nan')),dict(floor_native_pixels=4)]:
   with self.assertRaises(ValueError):checked_policy(p)
 def test_bad_coordinates(self):
  self.assertFalse(centre_measurement({},[0,0],.1)['centre_accepted'])
if __name__=='__main__':
 result=unittest.main(exit=False)
 if not result.result.wasSuccessful():raise SystemExit(1)
 vectors=[]
 for radius in [.2,1,3,6,12]:
  for offset in [0,.5,1,1.5,2.5,3,3.1]:
   p=dict(x_original_pix=100+offset,y_original_pix=200,sma_arcsec=radius);expected=centre_measurement(p,[100,200],.1);vectors.append(dict(point=p,reference=dict(x=100,y=200),scale=.1,expected=expected))
 Path('MER_VIS_centre_policy_v3/centre_policy_vectors.json').write_text(json.dumps(vectors,indent=2))
