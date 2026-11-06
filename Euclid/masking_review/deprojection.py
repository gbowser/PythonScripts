"""Masked, WCS-aware face-on/bar-aligned resampling and aperture profiles.

Positions are zero-based native pixels. Input PAs are observed sky angles east
of north modulo 180; output distances are arcsec in the disc plane. Resampling
is geometric, preserving intensity values without an inclination flux correction.
"""
from __future__ import annotations

import csv
import math
from pathlib import Path
import numpy as np
from astropy.io import fits
from astropy.wcs import WCS
import masking_core as core


def checked_options(values):
    fields = dict(disc_pa_deg=None, inclination_deg=None, bar_pa_deg=None,
                  radius_arcsec=None, bar_radius_arcsec=None, slit_width=3,
                  min_valid_fraction=1., profile_scale='log')
    if set(values)-set(fields):
        raise ValueError('Unknown deprojection options')
    fields.update(values)
    for key in fields:
        if key=='profile_scale':
            if fields[key] not in ('log','linear'):
                raise ValueError('Choose log or linear profile scale')
            continue
        value=fields[key]
        if isinstance(value,bool):
            raise ValueError(f'{key} must be numeric')
        try:
            value=float(value)
        except (TypeError,ValueError):
            raise ValueError(f'Enter a finite {key}') from None
        if not math.isfinite(value):
            raise ValueError(f'Enter a finite {key}')
        fields[key]=value
    if not 0<=fields['inclination_deg']<85:
        raise ValueError('Inclination must be between 0 and 85 degrees (upper bound excluded)')
    for key in ('radius_arcsec','bar_radius_arcsec'):
        if not 0<fields[key]<=600:
            raise ValueError(f'{key} must be greater than zero and at most 600 arcsec')
    width=fields['slit_width']
    if not width.is_integer() or not 1<=width<=31 or int(width)%2!=1:
        raise ValueError('Slit width must be an odd integer from 1 to 31 output pixels')
    fields['slit_width']=int(width)
    if not .1<=fields['min_valid_fraction']<=1:
        raise ValueError('Minimum valid aperture fraction must be between 0.1 and 1')
    for key in ('disc_pa_deg','bar_pa_deg'):
        fields[key]%=180
    return fields


def transform_matrix(wcs, x, y, disc_pa, inclination, bar_pa):
    """Return native-pixel offsets -> face-on bar-frame arcsec."""
    sky=wcs.pixel_to_world(x,y)
    columns=[]
    for dx,dy in ((1.,0.),(0.,1.)):
        east,north=sky.spherical_offsets_to(wcs.pixel_to_world(x+dx,y+dy))
        columns.append([east.arcsec,north.arcsec])
    jacobian=np.asarray(columns,dtype=float).T
    scale=float(np.sqrt(abs(np.linalg.det(jacobian))))
    if not np.isfinite(jacobian).all() or not math.isfinite(scale) or scale<=0:
        raise ValueError('A valid celestial WCS is required for deprojection')
    d,i,b=np.radians([disc_pa,inclination,bar_pa])
    cosine=math.cos(i)
    disc_basis=np.array([[math.sin(d),math.cos(d)], [math.cos(d),-math.sin(d)]])
    stretch=np.diag([1.,1./cosine])
    delta=b-d
    angle=math.atan2(math.sin(delta)/cosine,math.cos(delta))
    rotation=np.array([[math.cos(angle),math.sin(angle)],[-math.sin(angle),math.cos(angle)]])
    transform=rotation@stretch@disc_basis@jacobian
    bar_factor=math.hypot(math.cos(delta),math.sin(delta)/cosine)
    return transform,scale,math.degrees(angle)%180,bar_factor


def resample(data, mask, bad, header, centre, bounds, options):
    options=checked_options(options)
    data=np.asarray(data,dtype=float)
    mask=np.asarray(mask,dtype=bool)
    bad=np.asarray(bad,dtype=bool)|~np.isfinite(data)
    if mask.shape!=data.shape or bad.shape!=data.shape or data.ndim!=2:
        raise ValueError('Science, mask and bad-pixel arrays must share a two-dimensional grid')
    x,y=map(float,centre)
    if not all(math.isfinite(v) for v in (x,y)) or not (0<=x<data.shape[1] and 0<=y<data.shape[0]):
        raise ValueError('Deprojection centre must lie inside the native science image')
    wcs=WCS(header).celestial
    transform,scale,angle,bar_factor=transform_matrix(wcs,x,y,options['disc_pa_deg'],options['inclination_deg'],options['bar_pa_deg'])
    if options['radius_arcsec']<options['bar_radius_arcsec']*bar_factor:
        raise ValueError('Profile half-length must include the full deprojected bar extent')
    half=math.ceil(options['radius_arcsec']/scale)
    if half*2+1>4097:
        raise ValueError('Requested image exceeds 4097 pixels per side; reduce profile half-length')
    if options['slit_width']>half*2+1:
        raise ValueError('Profile aperture is wider than the requested output image')
    offsets=np.arange(-half,half+1,dtype=float)*scale
    shape=(len(offsets),len(offsets))
    science=np.full(shape,np.nan,np.float32)
    foreground_out=np.zeros(shape,bool)
    coverage=np.zeros(shape,np.float32)
    valid_weight=np.zeros(shape,np.float32)
    region=core.processing_region(data.shape,bounds)
    foreground=mask&region&~bad
    available=region&~bad
    clean=available&~mask
    inverse=np.linalg.inv(transform)
    for start in range(0,len(offsets),128):
        xx,yy=np.meshgrid(offsets,offsets[start:start+128])
        mapped=inverse@np.vstack((xx.ravel(),yy.ravel()))
        sx=mapped[0].reshape(xx.shape)+x;sy=mapped[1].reshape(xx.shape)+y
        x0=np.floor(sx).astype(int);y0=np.floor(sy).astype(int)
        dx=sx-x0;dy=sy-y0
        total=np.zeros(xx.shape);support=np.zeros(xx.shape);usable=np.zeros(xx.shape)
        hits=np.zeros(xx.shape,bool)
        for ox,oy,weight in ((0,0,(1-dx)*(1-dy)),(1,0,dx*(1-dy)),(0,1,(1-dx)*dy),(1,1,dx*dy)):
            ix=x0+ox;iy=y0+oy
            inside=(ix>=0)&(iy>=0)&(ix<data.shape[1])&(iy<data.shape[0])
            ix=np.clip(ix,0,data.shape[1]-1);iy=np.clip(iy,0,data.shape[0]-1)
            has_weight=weight>1e-10
            supported=inside&available[iy,ix]
            valid=inside&clean[iy,ix]
            support+=np.where(supported,weight,0)
            usable+=np.where(valid,weight,0)
            total+=np.where(valid,weight*np.where(np.isfinite(data[iy,ix]),data[iy,ix],0),0)
            hits|=inside&has_weight&foreground[iy,ix]
        sl=slice(start,start+xx.shape[0])
        accepted=(support>=1-1e-7)&(usable>=1-1e-7)&~hits
        science[sl]=np.divide(total,usable,out=np.full(xx.shape,np.nan),where=accepted)
        foreground_out[sl]=hits
        coverage[sl]=support;valid_weight[sl]=usable
    return dict(science=science,foreground=foreground_out,coverage=coverage,valid_weight=valid_weight,
                offsets=offsets,scale=scale,transform=transform,bar_angle_disc_deg=angle,
                bar_radius_deprojected_arcsec=options['bar_radius_arcsec']*bar_factor,
                bar_length_factor=bar_factor,options=options)


def profile_samples(products, background_mean=0.):
    science=products['science'].astype(float)-float(background_mean)
    centre=science.shape[0]//2
    width=products['options']['slit_width'];half=width//2
    threshold=products['options']['min_valid_fraction']
    rows=[]
    for axis in ('major','minor'):
        if axis=='major':
            values=science[centre-half:centre+half+1,:]
            fg=products['foreground'][centre-half:centre+half+1,:]
            geometric=products['coverage'][centre-half:centre+half+1,:]
        else:
            values=science[:,centre-half:centre+half+1].T
            fg=products['foreground'][:,centre-half:centre+half+1].T
            geometric=products['coverage'][:,centre-half:centre+half+1].T
        valid=np.isfinite(values);count=valid.sum(axis=0)
        means=np.divide(np.where(valid,values,0).sum(axis=0),count,
                        out=np.full(values.shape[1],np.nan),where=count>0)
        displayed=np.where((count/width)>=threshold-1e-10,means,np.nan)
        for k,radius in enumerate(products['offsets']):
            rows.append(dict(axis=axis,radius_arcsec=float(radius),intensity=float(displayed[k]),
                mean_available_intensity=float(means[k]),valid_samples=int(count[k]),requested_samples=width,
                valid_fraction=float(count[k]/width),foreground_mask_fraction=float(fg[:,k].mean()),
                unsupported_fraction=float((geometric[:,k]<1-1e-7).mean()),
                mask_intersects_aperture=bool(fg[:,k].any()),
                within_bar_extent=bool(abs(radius)<=products['bar_radius_deprojected_arcsec'])))
    return rows


def masked_intervals(rows, axis, scale, within_bar_only=False):
    points=[r for r in rows if r['axis']==axis]
    intervals=[];start=None;previous=None
    for row in points:
        cut=row['mask_intersects_aperture'] and (not within_bar_only or row['within_bar_extent'])
        if cut and start is None:
            start=row['radius_arcsec']-scale/2
        if start is not None and not cut:
            intervals.append([start,previous+scale/2]);start=None
        previous=row['radius_arcsec']
    if start is not None:
        intervals.append([start,previous+scale/2])
    return intervals


def write_products(data, mask, bad, header, geometry, review, options, output, provenance):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    products=resample(data,mask,bad,header,(geometry['x'],geometry['y']),review['processing_bounds'],options)
    background=float(review['background']['mean'])
    rows=profile_samples(products,background)
    h=fits.Header()
    half=len(products['offsets'])//2
    for axis in (1,2):
        h[f'CTYPE{axis}']='LINEAR';h[f'CUNIT{axis}']='arcsec'
        h[f'CRPIX{axis}']=half+1;h[f'CRVAL{axis}']=0.;h[f'CDELT{axis}']=products['scale']
    for key in ('OBJECT','GALID','BUNIT'):
        if key in header:h[key]=header[key]
    o=products['options']
    h['DISCPA']=o['disc_pa_deg'];h['INCL']=o['inclination_deg'];h['BARPA']=o['bar_pa_deg']
    h['BARDISC']=products['bar_angle_disc_deg'];h['BARRAD']=products['bar_radius_deprojected_arcsec']
    h['CENXIN']=geometry['x'];h['CENYIN']=geometry['y'];h['BGMEAN']=background
    h['REVIEWID']=review['review_id'];h['SLITW']=o['slit_width'];h['MINFRAC']=o['min_valid_fraction']
    h.add_history('Geometric deprojection; no inclination photometric correction.')
    h.add_history('Bar lies along +X; Y is perpendicular in the disc plane.')
    h.add_history('Bilinear interpolation requires every contributing science pixel to be unmasked.')
    h.add_history('Masked/unsupported output science is NaN; no gap filling.')
    unitless=h.copy()
    if 'BUNIT' in unitless:del unitless['BUNIT']
    hdus=[fits.PrimaryHDU(products['science'],h),
          fits.ImageHDU((~np.isfinite(products['science'])).astype(np.uint8),unitless,name='MASK'),
          fits.ImageHDU(products['foreground'].astype(np.uint8),unitless,name='FOREGROUND'),
          fits.ImageHDU(products['coverage'],unitless,name='COVERAGE'),
          fits.ImageHDU(products['valid_weight'],unitless,name='VALID_WEIGHT')]
    fits.HDUList(hdus).writeto(output/'deprojected_bar_aligned.fits',checksum=True)
    with (output/'bar_profiles.csv').open('w',newline='',encoding='utf8') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    result=dict(status='provisional_deprojection',object_id=review['object_id'],mask_review_id=review['review_id'],
        options=o,centre_x=geometry['x'],centre_y=geometry['y'],pixel_scale_arcsec=products['scale'],
        bar_angle_in_disc_deg=products['bar_angle_disc_deg'],bar_radius_deprojected_arcsec=products['bar_radius_deprojected_arcsec'],
        background_mean=background,background_sigma=float(review['background'].get('sigma',0.)),
        slit_width_arcsec=o['slit_width']*products['scale'],native_to_bar_arcsec=products['transform'].tolist(),
        major_mask_intervals_arcsec=masked_intervals(rows,'major',products['scale']),
        minor_mask_intervals_arcsec=masked_intervals(rows,'minor',products['scale']),
        major_bar_mask_intervals_arcsec=masked_intervals(rows,'major',products['scale'],True),
        valid_output_fraction=float(np.isfinite(products['science']).mean()),provenance=provenance,
        axis_profile_file='bar_axis_profiles.png',coordinate_convention='signed_distance_zero_at_reviewed_centre',
        profile_radius_range_arcsec=[float(products['offsets'][0]),float(products['offsets'][-1])],
        notes=['Science values are geometrically resampled without an inclination brightness correction.',
               'Profiles use background-subtracted input intensity units.',
               'Shading marks any foreground-mask overlap with the finite-width aperture.',
               'No interpolation bridges mask gaps. Aperture coverage is recorded for every sample.',
               'Deprojection assumes a flat disc; geometry remains subject to review.'])
    draw_diagnostic(products,rows,header,result,output/'bar_profile.png')
    draw_axis_profile(products,rows,header,result,output/'bar_axis_profiles.png')
    core.json_write(output/'result.json',result)
    return result


def plot_axis_profiles(ax, products, rows, header):
    """Both physical sides on a common signed axis; never fold or mirror data."""
    from matplotlib.patches import Patch
    from matplotlib.ticker import MaxNLocator
    for axis,color,style in [('major','#1f77b4','-'),('minor','#d62728','--')]:
        points=[r for r in rows if r['axis']==axis]
        radius=np.array([r['radius_arcsec'] for r in points]);intensity=np.array([r['intensity'] for r in points])
        if products['options']['profile_scale']=='log':
            intensity=np.where(intensity>0,intensity,np.nan)
        ax.plot(radius,intensity,color=color,linestyle=style,linewidth=1.6,label=f'bar {axis}')
    mask_handles=[]
    for axis,color,hatch in [('major','#ffb64b',None),('minor','#c9b4ee','///')]:
        intervals=masked_intervals(rows,axis,products['scale'])
        for lo,hi in intervals:
            ax.axvspan(lo,hi,color=color,alpha=.28,hatch=hatch,linewidth=0)
        if intervals:
            mask_handles.append(Patch(facecolor=color,alpha=.4,hatch=hatch,label=f'{axis} aperture mask cut'))
    if products['options']['profile_scale']=='log':ax.set_yscale('log')
    extent=products['bar_radius_deprojected_arcsec']
    for edge in (-extent,extent):ax.axvline(edge,color='#1f77b4',linewidth=1.15)
    ax.axvline(0,color='#333333',linestyle=':',linewidth=1)
    radius=max(abs(float(products['offsets'][0])),abs(float(products['offsets'][-1])))
    ax.set_xlim(-radius,radius)
    ax.xaxis.set_major_locator(MaxNLocator(nbins=9,symmetric=True))
    ax.set(title='major/minor-axis cuts',xlabel='deprojected radius [arcsec]',
           ylabel=f'intensity ({header.get("BUNIT","input units")}; background subtracted)')
    handles,_=ax.get_legend_handles_labels()
    ax.legend(handles=handles+mask_handles,fontsize=9,loc='best')


def draw_axis_profile(products,rows,header,result,path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,ax=plt.subplots(figsize=(9,6.6))
    plot_axis_profiles(ax,products,rows,header)
    fig.suptitle(str(result['object_id'])+' | provisional',fontsize=11)
    fig.text(.5,.025,'Zero = reviewed galaxy centre. Both sides are measured independently. Shading marks mask cuts; gaps are not filled.',
             ha='center',fontsize=8)
    fig.subplots_adjust(left=.12,right=.98,bottom=.13,top=.86)
    fig.savefig(path,dpi=150)
    plt.close(fig)


def draw_diagnostic(products, rows, header, result, path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch
    fig=plt.figure(figsize=(13,6.8))
    grid=fig.add_gridspec(2,2,width_ratios=[1,1.45],height_ratios=[3,1],hspace=.12,wspace=.28)
    image_ax=fig.add_subplot(grid[:,0]);profile_ax=fig.add_subplot(grid[0,1]);coverage_ax=fig.add_subplot(grid[1,1],sharex=profile_ax)
    offsets=products['offsets'];scale=products['scale'];edge=[offsets[0]-scale/2,offsets[-1]+scale/2]*2
    science=products['science'];finite=np.isfinite(science)
    if finite.any():
        image_ax.imshow(core.preview(science),origin='lower',extent=edge,cmap='gray',interpolation='nearest')
        # Contours are measured intensity contours on the already deprojected masked image.
        positive=science[finite]
        background=result['background_mean']
        peak=float(np.max(positive)-background)
        low=max(3*result['background_sigma'],peak*.005)
        levels=background+np.geomspace(low,peak*.8,7) if peak*.8>low>0 else []
        if len(levels)>1:
            image_ax.contour(offsets,offsets,np.ma.masked_invalid(science),levels=levels,colors='cyan',linewidths=.45,alpha=.7)
    tint=np.zeros((*science.shape,4));tint[products['foreground']]=[1,.3,.1,.7]
    tint[(~finite)&~products['foreground']]=[.4,.4,.4,.5]
    image_ax.imshow(tint,origin='lower',extent=edge,interpolation='nearest')
    slit=result['slit_width_arcsec']
    image_ax.axhspan(-slit/2,slit/2,color='#2a77b7',alpha=.2)
    image_ax.axvspan(-slit/2,slit/2,color='#c3426d',alpha=.15)
    bar_radius=products['bar_radius_deprojected_arcsec']
    image_ax.plot([-bar_radius,bar_radius],[0,0],color='#2a77b7',linewidth=1.2)
    image_ax.set(title='Face-on, bar horizontal\nOrange: foreground mask; gray: unsupported',xlabel='Along bar (arcsec)',ylabel='Across bar (arcsec)')
    plot_axis_profiles(profile_ax,products,rows,header)
    for axis,color,style in [('major','#1f77b4','-'),('minor','#d62728','--')]:
        points=[r for r in rows if r['axis']==axis]
        radius=np.array([r['radius_arcsec'] for r in points])
        coverage_ax.plot(radius,[r['valid_fraction'] for r in points],color=color,linestyle=style,linewidth=1)
    for axis,color,hatch in [('major','#ffb64b',None),('minor','#c9b4ee','///')]:
        for lo,hi in masked_intervals(rows,axis,scale):
            coverage_ax.axvspan(lo,hi,color=color,alpha=.2,linewidth=0)
    profile_ax.set_xlabel('')
    profile_ax.tick_params(labelbottom=False)
    coverage_ax.set(xlabel='Signed deprojected distance (arcsec)',ylabel='Valid fraction',ylim=(-.03,1.05),yticks=[0,.5,1])
    coverage_ax.axhline(products['options']['min_valid_fraction'],color='#777777',linestyle=':',linewidth=.8)
    profile_ax.set_xlim(offsets[0],offsets[-1])
    fig.suptitle(f'{result["object_id"]} | masked deprojection and bar profiles | provisional',fontsize=12)
    footer=f'Slit width {slit:.3g} arcsec; required valid fraction {products["options"]["min_valid_fraction"]:.0%}. Blue verticals: adopted bar extent; dotted: centre. Gaps are not filled.'
    if products['options']['profile_scale']=='log':footer+=' Non-positive values are omitted on log display (retained in CSV).'
    fig.text(.5,.025,footer,ha='center',fontsize=8,wrap=True)
    fig.subplots_adjust(left=.06,right=.98,bottom=.12,top=.88)
    fig.savefig(path,dpi=140)
    plt.close(fig)
