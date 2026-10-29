import unittest
from review_policy_MER_VIS import centre_confirmation,adoption_status

class PolicyTests(unittest.TestCase):
    def setUp(self):
        self.r=dict(reviewed=True,disc_decision='usable',bar_decision='convincing',centre_decision='looks_correct',
                    refit_id='a',centre_reference_x_pix=10.,centre_reference_y_pix=20.)
        self.c=dict(disc_pa=30.,inclination=40.,bar_pa=50.,issues=['Centre reference unverified: visual confirmation required'])
    def test_exact_confirmation(self):
        self.assertTrue(centre_confirmation(self.r,'a',dict(x=10.,y=20.)))
        self.assertFalse(centre_confirmation(self.r,'b',dict(x=10.,y=20.)))
        self.assertFalse(centre_confirmation(self.r,'a',dict(x=11.,y=20.)))
        self.r['reviewed']=False
        self.assertFalse(centre_confirmation(self.r,'a',dict(x=10.,y=20.)))
    def test_stale_warning_retained_as_provenance(self):
        got=adoption_status(self.r,self.c,True)
        self.assertEqual(got['adoption_status'],'reviewed_supported')
        self.assertEqual(got['effective_issues'],[])
        self.assertEqual(len(got['raw_issues']),1)
    def test_uncertain_withheld(self):
        self.r['disc_decision']='uncertain';got=adoption_status(self.r,self.c,True)
        self.assertFalse(got['automatic_deprojection_ready']);self.assertIsNone(got['adopted_inclination_deg'])
    def test_sparse_provisional_not_rejected(self):
        self.c['issues']=['Sparse disc sampling'];got=adoption_status(self.r,self.c,True)
        self.assertEqual(got['adoption_status'],'reviewed_provisional');self.assertEqual(got['adopted_inclination_deg'],40.)
        self.assertFalse(got['automatic_deprojection_ready'])
    def test_two_samples_no_inclination(self):
        self.c['inclination']=None;got=adoption_status(self.r,self.c,True)
        self.assertEqual(got['adoption_status'],'provisional_incomplete_disc');self.assertIsNone(got['adopted_disc_pa_deg'])
    def test_missing_bar_still_keeps_disc(self):
        self.c['bar_pa']=None;got=adoption_status(self.r,self.c,True)
        self.assertEqual(got['adopted_disc_pa_deg'],30.);self.assertFalse(got['automatic_deprojection_ready'])

if __name__=='__main__':unittest.main()
