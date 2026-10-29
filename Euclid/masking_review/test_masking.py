"""Scientific mask invariants and persistence tests; no browser/native MTO needed."""
import argparse
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS

import masking_core as core
from reviewer import Application


class MaskingTests(unittest.TestCase):
    def test_residual_pass_adds_selectable_labels_inside_the_galaxy(self):
        data=np.zeros((120,120));bad=np.zeros_like(data,bool)
        g=dict(x=60.,y=60.,a=10.,q=.7,theta=0.,scale=.1)
        base=np.zeros((100,100),np.int32);base[40:61,40:61]=1;base[10:14,10:14]=2
        residual=np.zeros_like(base);residual[45:47,45:47]=1;residual[55:57,55:57]=2;residual[50,50]=3
        products=[(base,dict(mean=7.,variance=2.,sigma=np.sqrt(2))),
                  (residual,dict(mean=0.,variance=1.,sigma=1.))]
        with patch.object(core,'run_mto',side_effect=products) as detector:
            labels,bg,bounds=core.detect_fit_galaxy(data,bad,g,core.parameters(dict(detect_on='original+residual',minarea=1)),Path('.'))
        self.assertEqual(detector.call_count,2)
        self.assertNotEqual(labels[55,55],labels[60,60])
        self.assertNotEqual(labels[65,65],labels[60,60])
        self.assertEqual(bg['mean'],7.)  # Raw science background retained for geometry.
        self.assertEqual(bg['residual_background']['mean'],0.)
        foreground=[int(labels[55,55]),int(labels[65,65])]
        mask=core.build_mask(labels,bad,foreground,int(labels[60,60]),0)
        self.assertTrue(mask[55,55]);self.assertTrue(mask[65,65]);self.assertFalse(mask[60,60])

    def test_mto_receives_only_fit_galaxy_crop_and_maps_labels_to_native_grid(self):
        data = np.zeros((300,300));bad=np.zeros_like(data,bool)
        g=dict(x=150.,y=150.,a=10.,q=.7,theta=0.,scale=.1)
        data[0,0]=1e9  # A distant source must never reach MTO.
        def detector(crop,mask,local,params,root):
            self.assertEqual(crop.shape,(100,100))
            self.assertEqual((local['x'],local['y']),(50.,50.))
            self.assertEqual(crop.max(),0)
            labels=np.zeros(crop.shape,np.int32);labels[50,50]=7
            return labels,dict(mean=0,variance=1,sigma=1)
        with patch.object(core,'run_mto',side_effect=detector):
            labels,background,bounds=core.detect_fit_galaxy(data,bad,g,core.parameters({}),Path('.'))
        self.assertEqual(bounds,dict(x0=100,x1=200,y0=100,y1=200))
        self.assertEqual(labels[150,150],7)
        self.assertEqual(np.count_nonzero(labels),1)
        self.assertEqual(labels.shape,data.shape)

    def test_autostretch_gamma_matches_median_target_without_modifying_pixels(self):
        data = np.array([[0., .1, 1.], [np.nan, .1, .1]])
        original = data.copy()
        stats = dict(minimum=0, maximum=1, median=.1, robust_sigma=.01)
        ordinary = core.preview(data, stats=stats)
        brighter = core.preview(data, gamma=2, stats=stats)
        self.assertEqual(ordinary[0, 1], 64)  # .25 target with gamma=1
        self.assertEqual(brighter[0, 1], 128)
        self.assertEqual(ordinary[1, 0], 0)
        np.testing.assert_equal(data, original)
        self.assertFalse(core.preview(np.ones((2, 2))).any())

    def test_display_preview_excludes_bad_pixels_and_preserves_native_data(self):
        data = np.arange(64, dtype=float).reshape(8, 8)
        original = data.copy()
        bad = np.zeros_like(data, bool)
        bad[0, 0] = True
        pixels, meta = core.display_pixels(data, bad, max_side=4)
        self.assertEqual(pixels.shape, (4, 4))
        self.assertEqual(meta['factor'], 2)
        self.assertTrue(np.isnan(pixels[0, 0]))
        self.assertEqual(meta['stats']['minimum'], 2)
        np.testing.assert_equal(data, original)

    def test_refit_recovers_known_ellipse_with_masked_contaminant(self):
        yy, xx = np.indices((160, 160))
        x, y, theta, q = 79.5, 79.5, .35, .65
        u = (xx-x)*np.cos(theta)+(yy-y)*np.sin(theta)
        v = -(xx-x)*np.sin(theta)+(yy-y)*np.cos(theta)
        radius = np.sqrt(u*u+(v/q)**2)
        data = 50*np.exp(-radius/15)+np.random.default_rng(42).normal(0,.002,xx.shape)
        bad = (xx-99)**2+(yy-91)**2 < 3**2
        data[bad] += 500  # Only a correctly applied mask excludes this source.
        w = WCS(naxis=2)
        w.wcs.crpix = [80.5, 80.5]
        w.wcs.crval = [60,-49]
        w.wcs.cdelt = [-1/3600,1/3600]
        w.wcs.ctype = ['RA---TAN','DEC--TAN']
        g = dict(x=x,y=y,a=35,q=q,theta=theta,scale=1.)
        bounds = dict(bar_min=3,bar_max=9,disc_min=15,disc_max=32)
        with tempfile.TemporaryDirectory() as tmp:
            result = core.fit_geometry(data,bad,w.to_header(),g,bounds,tmp,background_mean=0)
            self.assertGreaterEqual(result['n_disc'],6)
            self.assertAlmostEqual(result['disc_ellipticity'],1-q,delta=.015)
            self.assertAlmostEqual(result['inclination_deg'],np.degrees(np.arccos(q)),delta=1)
            start=w.pixel_to_world(x,y);end=w.pixel_to_world(x+np.cos(theta),y+np.sin(theta))
            east,north=start.spherical_offsets_to(end)
            expected=np.degrees(np.arctan2(east.arcsec,north.arcsec))%180
            difference=(result['disc_pa_deg']-expected+90)%180-90
            self.assertLess(abs(difference),1)
            self.assertTrue((Path(tmp)/'geometry.png').is_file())

    def test_parameters_reject_nonfinite_out_of_range_and_fractional_pixels(self):
        for value in [float('nan'), -0.1, 1.1, True]:
            with self.assertRaises(ValueError):
                core.parameters({'move_factor': value})
        with self.assertRaises(ValueError):
            core.parameters({'dilation': 1.5})
        with self.assertRaises(ValueError):
            core.parameters({'bg_variance': 0})
        self.assertIsNone(core.parameters({})['bg_variance'])

    def test_every_label_including_centre_can_be_masked(self):
        seg = np.zeros((100, 100), np.int32)
        seg[48:53, 48:53] = 1
        seg[5:40, 5:95] = 2  # Much larger than target: must not be filtered out.
        g = dict(x=50, y=50, a=15, q=.7, theta=0, scale=.1)
        g['outer_disc'] = dict(x=50, y=50, a=15, q=.7, theta=0)
        p = core.parameters({})
        rows, target = core.object_summary(seg, g, p)
        self.assertEqual(target, 1)
        self.assertTrue(next(r for r in rows if r['label'] == 2)['mask'])
        centre_mask=core.build_mask(seg,np.zeros_like(seg,bool),[1],target,0)
        self.assertTrue(centre_mask[50,50])
        mask = core.build_mask(seg, np.zeros_like(seg, bool), [2], target, 0)
        self.assertEqual(int(mask.sum()), 35 * 90)
        self.assertFalse(mask[50, 50])

    def test_foreground_detection_does_not_require_a_label_at_the_centre(self):
        seg = np.zeros((20, 20), np.int32)
        seg[2:4, 2:4] = 1
        rows,centre=core.object_summary(seg, dict(x=10, y=10, a=5, q=1, theta=0), core.parameters({}))
        self.assertEqual(centre,0)
        self.assertEqual(len(rows),1)

    def test_dilation_is_circular_and_always_keeps_bad_pixels(self):
        seg = np.zeros((9, 9), np.int32)
        seg[4, 4] = 2
        bad = np.zeros_like(seg, bool)
        bad[0, 0] = True
        mask = core.build_mask(seg, bad, [2], 1, 1)
        self.assertEqual(int(mask.sum()), 6)  # five-pixel cross plus invalid pixel
        self.assertFalse(mask[3, 3])

    def test_fit_galaxy_rectangle_is_clipped_to_native_image(self):
        g = dict(x=10, y=10, a=6, q=.5, theta=np.pi/2, scale=.1)
        region = core.ellipse_region((21, 21), g)
        self.assertTrue(region[15, 10])
        self.assertFalse(region[10, 15])
        g['outer_disc'] = dict(x=11, y=12, a=12, q=.8, theta=.4)
        bounds = core.fit_galaxy_bounds((21,21),g)
        self.assertEqual(bounds,dict(x0=0,x1=21,y0=0,y1=21))
        self.assertEqual(g['a'], 6)
        with self.assertRaises(ValueError):
            core.parameters({'aoi_radius_arcsec': 1.2})
        with self.assertRaises(ValueError):
            core.parameters({'margin': 1.5})

    def test_outer_disc_selection_does_not_use_inner_pa_interval_or_unclassified_outskirts(self):
        g = dict(scale=.1, disc_min=.4, disc_max=.95, bar_max=3.2)
        def point(radius, selected, accepted=True):
            return dict(sma_arcsec=str(radius), ellipticity='.45', pa_pixel_deg='37',
                        x_original_pix='10.3', y_original_pix='12.4',
                        used_for_geometry=str(accepted), selected_disc=str(selected))
        profile = [point(.9,False),point(5.9,True),point(7.4,False),point(9.,True,False)]
        e = core.outer_disc_ellipse(profile,g)
        self.assertAlmostEqual(e['sma_arcsec'],5.9)
        self.assertAlmostEqual(e['a']*1.3,76.7)
        self.assertAlmostEqual(e['q'],.55)
        self.assertAlmostEqual(e['theta'],np.radians(37))
        with self.assertRaisesRegex(ValueError,'No accepted outer disc'):
            core.outer_disc_ellipse([point(.9,False)],g)

    def test_save_native_mask_roundtrip_and_source_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'science.fits'
            w = WCS(naxis=2)
            w.wcs.crpix = [11, 11]
            w.wcs.crval = [60, -49]
            w.wcs.cdelt = [-.1/3600, .1/3600]
            w.wcs.ctype = ['RA---TAN', 'DEC--TAN']
            header = w.to_header()
            header.update(CENX=11, CENY=11, GALID='test')
            fits.PrimaryHDU(np.ones((21, 21)), header).writeto(source)
            digest = core.digest(source)
            run_id = 'a' * 32
            output = root / 'output'
            folder = output / 'runs' / run_id
            folder.mkdir(parents=True)
            seg = np.zeros((21, 21), np.int32)
            seg[9:12, 9:12] = 1
            seg[3:6, 3:6] = 2
            bad = np.zeros_like(seg, bool)
            bad[0, 0] = True
            np.savez_compressed(folder / 'detection.npz', segmentation=seg, bad=bad)
            g = dict(x=10, y=10, a=6, q=.8, theta=0, scale=.1)
            result = dict(object_id='test', run_id=run_id, target=1, processing_policy=core.PROCESSING_POLICY, processing_bounds=dict(x0=2,x1=19,y0=2,y1=19), params=core.parameters({'dilation': 0}),
                          geometry=g, background=dict(mean=0, sigma=1, variance=1), source_sha256=digest)
            core.json_write(folder / 'result.json', result)
            app = Application.__new__(Application)
            app.args = argparse.Namespace(fits_dir=None)
            app.output = output
            app.byid = {'test': dict(fits_path=str(source))}
            app.catalogue_hash = 'catalogue'
            payload = dict(run_id=run_id, selected=[2], confirm=True, notes='companion masked')
            review = app.save(payload)
            saved = output / 'reviews' / review['review_id']
            mask = fits.getdata(saved / 'mask.fits', memmap=False)
            self.assertEqual(mask.shape, (21, 21))
            self.assertEqual(mask.sum(), 161)  # 152 unprocessed pixels plus 9 contaminant pixels.
            self.assertEqual(mask[0,0],1)
            self.assertEqual(mask[10, 10], 0)
            self.assertEqual(core.digest(source), digest)
            self.assertEqual(json.loads((output / 'latest_test.json').read_text())['selected'], [2])
            self.assertTrue((saved / 'mask_review.png').is_file())
            np.testing.assert_allclose(WCS(fits.getheader(saved / 'mask.fits')).pixel_scale_matrix, w.pixel_scale_matrix)
            payload['selected'] = [1]
            centre_review=app.save(payload)
            self.assertEqual(centre_review['selected'],[1])
            with self.assertRaises(ValueError):
                app.folder('reviews', '../escape')


if __name__ == '__main__':
    unittest.main()
