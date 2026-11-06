"""Geometric and mask-propagation invariants for bar deprojection."""
import tempfile
import argparse
import threading
import unittest
from unittest.mock import patch
from pathlib import Path
import numpy as np
from astropy.io import fits
from astropy.wcs import WCS
import deprojection as dp
import masking_core as core
from reviewer import Application


def header(scale=1., mirrored=True):
    w=WCS(naxis=2)
    w.wcs.crpix=[51,51];w.wcs.crval=[60,-49]
    w.wcs.cdelt=[(-1 if mirrored else 1)*scale/3600,scale/3600]
    w.wcs.ctype=['RA---TAN','DEC--TAN']
    return w.to_header()


def options(**overrides):
    result=dict(disc_pa_deg=0.,inclination_deg=0.,bar_pa_deg=0.,
                radius_arcsec=20.,bar_radius_arcsec=10.,slit_width=3,
                min_valid_fraction=1.,profile_scale='log')
    result.update(overrides)
    return result


class DeprojectionTests(unittest.TestCase):
    def test_profiles_keep_both_signed_sides_without_folding_or_mirroring(self):
        yy,xx=np.indices((9,9));science=100.+2*xx+3*yy
        p=dict(science=science,foreground=np.zeros((9,9),bool),coverage=np.ones((9,9)),
               offsets=np.arange(-4,5,dtype=float),scale=1.,bar_radius_deprojected_arcsec=3.,
               options=dict(slit_width=1,min_valid_fraction=1.,profile_scale='log'))
        rows=dp.profile_samples(p)
        for axis in ('major','minor'):
            points=[r for r in rows if r['axis']==axis]
            self.assertEqual([r['radius_arcsec'] for r in points],list(range(-4,5)))
            self.assertEqual(sum(r['radius_arcsec']==0 for r in points),1)
            self.assertNotEqual(points[0]['intensity'],points[-1]['intensity'])
        major=[r for r in rows if r['axis']=='major']
        self.assertEqual((major[0]['intensity'],major[4]['intensity'],major[-1]['intensity']),(112,120,128))
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        fig,ax=plt.subplots()
        dp.plot_axis_profiles(ax,p,rows,{})
        self.assertEqual(ax.get_xlim(),(-4,4))
        curves={line.get_label():line for line in ax.lines if line.get_label() in ('bar major','bar minor')}
        for line in curves.values():
            self.assertEqual(min(line.get_xdata()),-4)
            self.assertEqual(max(line.get_xdata()),4)
        self.assertTrue(any(np.array_equal(line.get_xdata(),[0,0]) for line in ax.lines))
        plt.close(fig)

    def test_api_rejects_a_refit_from_another_mask_and_uses_exact_matching_geometry(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'source.fits'
            fits.PrimaryHDU(np.ones((101,101)),header()).writeto(source)
            review_id='a'*32;refit_id='b'*32
            review_folder=root/'reviews'/review_id;review_folder.mkdir(parents=True)
            fits.PrimaryHDU(np.zeros((101,101),np.uint8)).writeto(review_folder/'mask.fits')
            sha=core.digest(review_folder/'mask.fits')
            review=dict(review_id=review_id,object_id='test',source_sha256=core.digest(source),
                        mask_sha256=sha,processing_policy=core.PROCESSING_POLICY,geometry=dict(x=50,y=50))
            core.json_write(review_folder/'review.json',review)
            refit_folder=root/'refits'/refit_id;refit_folder.mkdir(parents=True)
            fit=dict(object_id='test',mask_review_id='wrong',mask_sha256=sha,disc_pa_deg=0.,inclination_deg=0.,bar_pa_deg=0.,
                     centre_x=50.,centre_y=50.,bounds=dict(bar_max=7.5))
            core.json_write(refit_folder/'result.json',fit)
            app=Application.__new__(Application)
            app.output=root;app.args=argparse.Namespace(fits_dir=None,mtobjects_root=root)
            app.byid={'test':dict(object_id='test',fits_path=str(source))}
            app.catalogue_hash='catalogue';app.lock=threading.Lock();app.job=None
            payload=dict(action='deproject',object_id='test',review_id=review_id,refit_id=refit_id,
                         geometry_source='masked_refit',options=options(disc_pa_deg=47))
            with self.assertRaisesRegex(ValueError,'exact accepted mask'):
                app.start_job(payload)
            fit['mask_review_id']=review_id;core.json_write(refit_folder/'result.json',fit)
            with patch('reviewer.threading.Thread') as thread:
                app.start_job(payload)
                request=thread.call_args.kwargs['args'][1]
            self.assertEqual(request['options']['disc_pa_deg'],0.)
            self.assertEqual(request['options']['bar_radius_arcsec'],7.5)
            self.assertEqual(request['deprojection_centre'],[50.,50.])
            self.assertEqual(request['geometry_refit_sha256'],core.digest(refit_folder/'result.json'))

    def test_bar_vector_maps_to_positive_horizontal_axis_for_mirrored_wcs(self):
        for mirrored in (True,False):
            w=WCS(header(mirrored=mirrored)).celestial
            for d,i,b in [(0,0,0),(25,60,80),(130,45,10)]:
                transform,scale,angle,factor=dp.transform_matrix(w,50,50,d,i,b)
                sky=w.pixel_to_world(50,50)
                from astropy import units as u
                end=sky.directional_offset_by(b*u.deg,1*u.arcsec)
                x,y=w.world_to_pixel(end)
                bar=transform@np.array([x-50,y-50])
                self.assertGreater(bar[0],0)
                self.assertAlmostEqual(bar[1],0,delta=2e-5)
                self.assertAlmostEqual(bar[0],factor,delta=2e-5)

    def test_inclined_disc_maps_to_a_circle_and_bar_minor_expands(self):
        w=WCS(header()).celestial
        transform,scale,angle,factor=dp.transform_matrix(w,50,50,0,60,90)
        angles=np.linspace(0,2*np.pi,101)
        # North is the disc major direction; native X is foreshortened by cos(i).
        native=np.vstack((5*np.cos(angles),10*np.sin(angles)))
        radii=np.hypot(*(transform@native))
        np.testing.assert_allclose(radii,10,atol=1e-4)
        self.assertAlmostEqual(factor,2,places=6)

    def test_masked_bilinear_contributors_are_excluded_and_distinguished_from_crop_edge(self):
        data=np.ones((101,101))*10
        bad=np.zeros(data.shape,bool);mask=bad.copy();mask[60,50]=True
        bounds=dict(x0=30,x1=71,y0=30,y1=71)
        p=dp.resample(data,mask,bad,header(),(50,50),bounds,options())
        index=np.argmin(abs(p['offsets']-10));mid=len(p['offsets'])//2
        self.assertTrue(p['foreground'][mid,index])
        self.assertTrue(np.isnan(p['science'][mid,index]))
        self.assertFalse(p['foreground'][mid,mid])
        self.assertAlmostEqual(p['science'][mid,mid],10)
        # Deliberately limit processing coverage while the source image remains large.
        narrower=dict(x0=45,x1=56,y0=45,y1=56)
        p2=dp.resample(data,mask,bad,header(),(50,50),narrower,options())
        self.assertTrue(np.isnan(p2['science'][mid,0]))
        self.assertFalse(p2['foreground'][mid,0])

    def test_profile_records_partial_slit_coverage_and_leaves_strict_gaps(self):
        science=np.ones((9,9))*10
        fg=np.zeros((9,9),bool);fg[4,6]=True;science[4,6]=np.nan
        p=dict(science=science,foreground=fg,coverage=np.ones((9,9)),offsets=np.arange(-4,5,dtype=float),
               scale=1.,bar_radius_deprojected_arcsec=3.,options=dict(slit_width=3,min_valid_fraction=1.))
        rows=dp.profile_samples(p,background_mean=1.)
        point=next(r for r in rows if r['axis']=='major' and r['radius_arcsec']==2)
        self.assertTrue(np.isnan(point['intensity']))
        self.assertEqual(point['mean_available_intensity'],9)
        self.assertEqual(point['valid_samples'],2)
        self.assertAlmostEqual(point['foreground_mask_fraction'],1/3)
        self.assertEqual(dp.masked_intervals(rows,'major',1,True),[[1.5,2.5]])
        p['options']['min_valid_fraction']=.5
        relaxed=next(r for r in dp.profile_samples(p,1.) if r['axis']=='major' and r['radius_arcsec']==2)
        self.assertEqual(relaxed['intensity'],9)

    def test_files_preserve_nan_mask_and_profile_provenance(self):
        data=np.ones((101,101))*10
        bad=np.zeros_like(data,bool);mask=bad.copy();mask[60,50]=True
        review=dict(review_id='review',object_id='synthetic',processing_bounds=dict(x0=0,x1=101,y0=0,y1=101),background=dict(mean=1))
        with tempfile.TemporaryDirectory() as tmp:
            r=dp.write_products(data,mask,bad,header(),dict(x=50,y=50),review,options(),tmp,dict(mask_sha256='abc'))
            path=Path(tmp)/'deprojected_bar_aligned.fits'
            with fits.open(path,memmap=False) as hd:
                self.assertEqual(hd[0].header['REVIEWID'],'review')
                self.assertEqual(hd['FOREGROUND'].data.max(),1)
                self.assertTrue(np.isnan(hd[0].data[hd['MASK'].data.astype(bool)]).all())
                self.assertEqual(hd[0].header['CUNIT1'],'arcsec')
            self.assertTrue((Path(tmp)/'bar_profiles.csv').is_file())
            self.assertTrue((Path(tmp)/'bar_profile.png').is_file())
            self.assertTrue((Path(tmp)/'bar_axis_profiles.png').is_file())
            self.assertEqual(r['provenance']['mask_sha256'],'abc')
            self.assertTrue(r['major_bar_mask_intervals_arcsec'])

    def test_reject_incomplete_edge_on_and_even_width_geometry(self):
        for overrides in [dict(inclination_deg=85),dict(slit_width=2),dict(disc_pa_deg=None),dict(min_valid_fraction=0)]:
            values=options();values.update(overrides)
            with self.assertRaises(ValueError):dp.checked_options(values)


if __name__=='__main__':
    unittest.main()
