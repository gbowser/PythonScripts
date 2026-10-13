"""Photutils ellipse profiles and provisional disc/bar geometry for native cutouts.

Automatic radial selections are hypotheses, not catalogue measurements. Review
the PNG and set bar/disc radial ranges in --ranges-csv before scientific use.
"""
import argparse
import csv
from pathlib import Path
import numpy as np
from astropy.io import fits
from astropy.stats import sigma_clipped_stats
from astropy.wcs import WCS
from photutils.isophote import Ellipse, EllipseGeometry
from scipy.ndimage import binary_dilation, gaussian_filter, label
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse as PlotEllipse
from extract_calibrated_galaxies import DEFAULT_OUTPUT
from extract_euclid_bars import local_pixel_matrix
from deproject_calibrated_galaxies import transform_cutout


def axial_mean(angles):
    return np.angle(np.mean(np.exp(2j * np.asarray(angles)))) / 2 % np.pi


def axial_scatter(angles):
    mean = axial_mean(angles)
    return np.degrees(np.sqrt(np.mean(((np.asarray(angles)-mean+np.pi/2) % np.pi-np.pi/2)**2)))


def sky_pa(angle, matrix):
    west, north = matrix @ np.array([np.cos(angle), np.sin(angle)])
    return float(np.degrees(np.arctan2(-west, north)) % 180)


def write_csv(path, rows):
    if not rows:
        return
    with path.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def fit_one(path, out, q0=0., ranges=None, previews=False):
    ranges = ranges or {}
    with fits.open(path) as hdul:
        raw = hdul[0].data.astype(float)
        header = hdul[0].header.copy()
        bad = ~np.isfinite(raw)
        if 'FLG' in hdul:
            # OBJECTS and STITCHBLOCK are informational, not rejected pixels.
            reject_bits = sum(1 << b for b in list(range(20)) + [21,22])
            bad |= (hdul['FLG'].data & reject_bits) != 0
    x0, y0 = header['CENX']-1, header['CENY']-1
    # Reduce fitting cost without changing the saved native science pixels.
    binning = 2
    ny, nx = np.array(raw.shape)//binning
    blocks = np.where(bad, np.nan, raw)[:ny*2, :nx*2].reshape(ny,2,nx,2)
    count = np.sum(np.isfinite(blocks), axis=(1,3))
    data = np.nansum(blocks, axis=(1,3))/np.maximum(count,1)
    mask = count < 3
    x, y = (x0-.5)/2, (y0-.5)/2
    yy, xx = np.indices(data.shape)
    rr = np.hypot(xx-x, yy-y)
    margin = min(x,y,nx-1-x,ny-1-y)
    background_pixels = (~mask) & (rr > .75*margin)
    background, _, noise = sigma_clipped_stats(data[background_pixels], sigma=3)
    data -= background
    smooth = gaussian_filter(np.where(mask,0,data), 1.5)
    print(f'  Background {background:.4g}, noise {noise:.4g}, extent limit {margin:.1f} fit pixels; peak {np.nanmax(smooth):.4g}', flush=True)
    segments, nsegments = label((smooth > 3*noise) & ~mask)
    if nsegments:
        target = segments[int(round(y)), int(round(x))]
        if target == 0:
            raise ValueError('Catalogue centre is not on a detected galaxy')
        neighbours = (segments != 0) & (segments != target)
        mask |= binary_dilation(neighbours, iterations=3)
        galaxy = segments == target
        extent = float(np.percentile(rr[galaxy], 95))
    else:
        raise ValueError('No galaxy detected')
    maxsma = min(.9*margin, max(20,extent*1.7))
    sma0 = max(5,min(extent*.3,maxsma*.4))
    weights = np.where((rr < sma0*2) & ~mask, np.maximum(smooth,0),0)
    dx,dy=xx-x,yy-y
    cov=np.array([[np.sum(weights*dx*dx),np.sum(weights*dx*dy)],
                  [np.sum(weights*dx*dy),np.sum(weights*dy*dy)]])
    values,vectors=np.linalg.eigh(cov)
    pa=np.arctan2(vectors[1,-1],vectors[0,-1]) % np.pi
    eps=float(np.clip(1-np.sqrt(max(values[0],1e-9)/max(values[1],1e-9)),.1,.7))
    isophotes=[]
    seeds=[(sma0,eps,pa),(max(4,sma0*.5),eps,pa),(max(4,sma0*1.5),eps,pa),
           (4,.3,pa),(6,.3,(pa+np.pi/4)%np.pi),(6,.3,(pa+np.pi/2)%np.pi)]
    for start,seed_eps,seed_pa in seeds:
        ellipse=Ellipse(np.ma.array(data,mask=mask), geometry=EllipseGeometry(x,y,start,seed_eps,seed_pa))
        trial=ellipse.fit_image(minsma=3,maxsma=maxsma,step=.08,
                               fix_center=True,n_clip=3,sclip=3,maxit=80,maxgerr=1.)
        if len(trial)>len(isophotes): isophotes=trial
        if len(trial)>20: break
    wcs=WCS(header).celestial
    matrix=local_pixel_matrix(wcs,wcs.pixel_to_world(x0,y0),x0,y0)
    scale=float(np.sqrt(abs(np.linalg.det(matrix))))
    profile=[]
    for iso in isophotes:
        profile.append(dict(sma_arcsec=iso.sma*2*scale, ellipticity=iso.eps,
                            pa_pixel_deg=np.degrees(iso.pa), pa_sky_deg=sky_pa(iso.pa,matrix),
                            ellipticity_error=iso.ellip_err,pa_error_deg=np.degrees(iso.pa_err),
                            intensity=iso.intens,intensity_error=iso.int_err,
                            stop_code=iso.stop_code,valid=iso.valid,
                            sampled_fraction=iso.n_data/max(1,iso.n_data+iso.n_flag)))
    stem=path.stem.removesuffix('_cutout')
    write_csv(out/(stem+'_ellipse_profile.csv'),profile)
    # Always save a diagnostic, including failed/short profiles.
    fig,ax=plt.subplots(figsize=(7,7))
    ax.imshow(np.arcsinh(data/max(noise,1e-9)),origin='lower',cmap='gray',vmin=0,vmax=np.arcsinh(np.percentile(data[~mask],99.9)/noise))
    for iso in isophotes[::3]:
        ax.add_patch(PlotEllipse((x,y),2*iso.sma,2*iso.sma*(1-iso.eps),angle=np.degrees(iso.pa),fill=False,color='cyan',lw=.7))
    ax.plot(x,y,'r+'); lim=min(maxsma*1.3,margin)
    ax.set(xlim=(x-lim,x+lim),ylim=(y-lim,y+lim),title=f"{header['GALID']}: fitted ellipses; fixed catalogue centre")
    fig.savefig(out/(stem+'_ellipse_overlay.png'),dpi=120);plt.close(fig)
    good=[p for p in profile if p['valid'] and p['stop_code']==0 and p['sampled_fraction']>=.7
          and p['intensity']>0 and p['intensity']>5*max(p['intensity_error'],1e-12)]
    if len(good)<10:
        raise ValueError(f'Only {len(good)} reliable isophotes; inspect profile')
    a=np.array([p['sma_arcsec'] for p in good])
    e=np.array([p['ellipticity'] for p in good])
    angles=np.deg2rad([p['pa_sky_deg'] for p in good])
    manual=all(ranges.get(k,'').strip() for k in ('bar_min_arcsec','bar_max_arcsec','disc_min_arcsec','disc_max_arcsec'))
    if manual:
        bmin,bmax,dmin,dmax=[float(ranges[k]) for k in ('bar_min_arcsec','bar_max_arcsec','disc_min_arcsec','disc_max_arcsec')]
        if not 0<bmin<bmax<dmin<dmax:
            raise ValueError('Require 0 < bar_min < bar_max < disc_min < disc_max')
    else:
        inner=np.where((a>.12*a.max()) & (a<.55*a.max()))[0]
        peak=inner[np.argmax(e[inner])]
        bmin,bmax=.75*a[peak],1.15*a[peak]
        dmin,dmax=max(1.25*bmax,.65*a.max()),a.max()*1.001
    bar=(a>=bmin)&(a<=bmax)
    disc=(a>=dmin)&(a<=dmax)
    if bar.sum()<3 or disc.sum()<3:
        raise ValueError('Insufficient bar/disc isophotes in selected radial ranges')
    diskpa,barpa=np.degrees(axial_mean(angles[disc])),np.degrees(axial_mean(angles[bar]))
    q=1-float(np.median(e[disc]))
    inc=float(np.degrees(np.arccos(np.sqrt(np.clip((q*q-q0*q0)/(1-q0*q0),0,1)))))
    reasons=[]
    if axial_scatter(angles[disc])>10: reasons.append('disc_PA_unstable')
    if axial_scatter(angles[bar])>10: reasons.append('bar_PA_unstable')
    if np.ptp(e[disc])>.15: reasons.append('disc_axis_ratio_unstable')
    if q>.9: reasons.append('nearly_face_on_PA_uncertain')
    if inc>=80: reasons.append('high_inclination')
    if np.median(e[bar])<.25: reasons.append('weak_ellipse_bar_signature')
    if q<=q0: reasons.append('axis_ratio_below_thickness')
    if bmax<1.5: reasons.append('small_bar_sensitive_to_resolution')
    radius=max(3*bmax,45.)
    row=dict(object_id=str(header['GALID']), input_file=str(path), disk_pa_deg=diskpa,
             inclination_deg=inc,bar_pa_deg=barpa,radius_arcsec=radius,
             geometry_source='Photutils isophotes; provisional image estimate',
             status='needs_review' if not manual or reasons else 'reviewed_ranges',
             quality_flags=';'.join(reasons),q0=q0,disc_axis_ratio=q,
             disc_pa_scatter_deg=axial_scatter(angles[disc]),bar_pa_scatter_deg=axial_scatter(angles[bar]),
             bar_min_arcsec=bmin,bar_max_arcsec=bmax,disc_min_arcsec=dmin,disc_max_arcsec=dmax,
             centre_x_pix=x0+1,centre_y_pix=y0+1,centre_source='Q1 catalogue; fixed during fit',
             masked_fraction=float(mask.mean()),output_file='')
    fig,axes=plt.subplots(1,3,figsize=(15,5))
    vmin,vmax=np.percentile(data[~mask],[10,99.8])
    axes[0].imshow(np.arcsinh(data/max(noise,1e-9)),origin='lower',cmap='gray',
                   vmin=np.arcsinh(vmin/max(noise,1e-9)),vmax=np.arcsinh(vmax/max(noise,1e-9)))
    axes[0].contour(mask,levels=[.5],colors=['red'],linewidths=.2)
    for iso in isophotes[::4]:
        axes[0].add_patch(PlotEllipse((x,y),2*iso.sma,2*iso.sma*(1-iso.eps),
                           angle=np.degrees(iso.pa),fill=False,color='cyan',lw=.6))
    lim=min(maxsma*1.2,margin)
    axes[0].set(xlim=(x-lim,x+lim),ylim=(y-lim,y+lim),title='Masked pixels red; fitted ellipses cyan')
    axes[1].plot(a,e,'.-'); axes[1].set(ylabel='Ellipticity',xlabel='Semi-major axis (arcsec)')
    axes[2].plot(a,np.degrees(angles),'.-'); axes[2].set(ylabel='Sky PA east of north (deg)',xlabel='Semi-major axis (arcsec)',ylim=(0,180))
    for ax in axes[1:]:
        ax.axvspan(bmin,bmax,color='orange',alpha=.25,label='Bar');ax.axvspan(dmin,dmax,color='green',alpha=.2,label='Disc');ax.legend()
    fig.suptitle(f"{header['GALID']} — {row['status']} {row['quality_flags']}")
    fig.tight_layout();fig.savefig(out/(stem+'_geometry_review.png'),dpi=140);plt.close(fig)
    candidate=path.with_name(stem+'_provisional_bar_aligned.fits')
    if reasons and candidate.exists():
        # A rerun can invalidate an earlier preview; keep it visibly rejected.
        rejected=candidate.with_name(stem+'_rejected_bar_aligned.fits')
        candidate.replace(rejected)
        with fits.open(rejected,mode='update') as hdul:
            hdul[0].header['GEOMSTAT']='REJECTED'
            hdul[0].add_checksum()
    if previews and not reasons:
        # Preserve a distinct provisional name; never silently promote a fit.
        temporary=path.with_name(stem+'_bar_aligned.fits')
        if temporary.exists():
            raise FileExistsError(f'Protecting existing aligned output: {temporary}')
        generated=transform_cutout(path,row,overwrite=False)
        generated.replace(candidate)
        with fits.open(candidate,mode='update') as hdul:
            hdul[0].header['GEOMSTAT']='PROVISIONAL'
            hdul[0].header['Q0']=q0
            hdul[0].add_checksum()
        row['output_file']=str(candidate)
    return row


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-dir',type=Path,default=DEFAULT_OUTPUT)
    parser.add_argument('--ranges-csv',type=Path)
    parser.add_argument('--q0',type=float,default=0.,help='Intrinsic disc thickness; default thin disc')
    parser.add_argument('--previews',action='store_true',help='Save explicitly provisional aligned FITS for stable fits')
    args=parser.parse_args()
    if not 0<=args.q0<1: parser.error('q0 must be in [0,1)')
    ranges={}
    if args.ranges_csv:
        with args.ranges_csv.open(newline='',encoding='utf-8-sig') as handle:
            ranges={r['object_id']:r for r in csv.DictReader(handle)}
    rows=[];errors=[]
    for path in sorted(args.input_dir.glob('*_cutout.fits')):
        print(f'Fitting {path.name}',flush=True)
        try:
            row=fit_one(path,args.input_dir,args.q0,ranges.get(str(fits.getheader(path)['GALID'])),args.previews)
            rows.append(row); print(f"  {row['status']}: disc PA {row['disk_pa_deg']:.1f}, i {row['inclination_deg']:.1f}, bar PA {row['bar_pa_deg']:.1f}; {row['quality_flags']}",flush=True)
        except Exception as error:
            errors.append(dict(input_file=str(path),error=str(error)))
            print(f'  Fit failed: {error}',flush=True)
    write_csv(args.input_dir/'photutils_geometry_manifest.csv',rows)
    error_path=args.input_dir/'photutils_fit_errors.csv'
    if errors: write_csv(error_path,errors)
    else: error_path.write_text('input_file,error\n',encoding='utf-8')
    print(f'{len(rows)} geometry candidates; {len(errors)} failed fits',flush=True)


if __name__=='__main__': main()
