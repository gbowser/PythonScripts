"""Synthetic check of ellipse recovery and WCS angle conversion."""
import numpy as np
from photutils.isophote import Ellipse, EllipseGeometry
from fit_euclid_geometry import sky_pa, axial_mean, axial_scatter

def main():
    yy,xx=np.indices((201,201))
    pa=np.deg2rad(32)
    major=(xx-100)*np.cos(pa)+(yy-100)*np.sin(pa)
    minor=-(xx-100)*np.sin(pa)+(yy-100)*np.cos(pa)
    data=100*np.exp(-.5*((major/30)**2+(minor/18)**2))
    data+=np.random.default_rng(17).normal(0,.05,data.shape)
    result=Ellipse(data,geometry=EllipseGeometry(100,100,20,.35,.5)).fit_image(
        minsma=10,maxsma=55,fix_center=True)
    use=[r for r in result if r.valid and r.stop_code==0 and 15<r.sma<45]
    assert len(use)>5
    assert abs(np.median([r.eps for r in use])-.4)<.01
    assert abs(np.degrees(axial_mean([r.pa for r in use]))-32)<.5
    # North-up image, x increasing west: major pixel angle 32 => sky PA 122.
    assert abs(sky_pa(pa,np.array([[.1,0],[0,.1]]))-122)<1e-8
    assert axial_scatter(np.deg2rad([179,0,1]))<1
    print('PASS: ellipse axis ratio/PA recovery and WCS/axial angle conventions')

if __name__=='__main__': main()
