"""Three-image segmentation feasibility pilot; never changes source FITS files."""
from pathlib import Path
import argparse, csv, hashlib, importlib.metadata as md, json, subprocess, sys
from datetime import datetime, timezone
import numpy as np
from astropy.io import fits
from astropy.nddata import Cutout2D
from astropy.wcs import WCS
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from astropy.visualization import simple_norm
from skimage.segmentation import find_boundaries
import sep

def dump_csv(path, rows, fields=None):
    fields = fields or list(dict.fromkeys(k for row in rows for k in row))
    with Path(path).open('w', newline='') as f:
        writer=csv.DictWriter(f, fieldnames=fields); writer.writeheader(); writer.writerows(rows)

def prepare_sep(data):
    """Retain spatial noise when valid; explicitly record a global fallback otherwise."""
    background = sep.Background(data)
    residual = np.ascontiguousarray(data - background.back())
    original_rms = background.rms()
    bad = ~np.isfinite(original_rms) | (original_rms <= 0)
    record = dict(model='spatial', invalid_rms_pixels=int(bad.sum()),
                  global_rms=float(background.globalrms), threshold_sigma=1.5)
    if bad.any():
        global_rms = float(background.globalrms)
        if not np.isfinite(global_rms) or global_rms <= 0:
            raise ValueError('Both spatial and global SEP noise estimates are invalid')
        noise = np.full(data.shape, global_rms, dtype=np.float64)
        record['model'] = 'global_fallback_invalid_spatial_rms'
    else:
        noise = original_rms
    return background, residual, noise, original_rms, record

def select(work, count, max_side):
    with (work/'MER_VIS_datalabs_manifest.csv').open(encoding='utf-8-sig',newline='') as f:
        targets=list(csv.DictReader(f))
    chosen=[]
    for target in targets:
        path=work/'cutouts'/f"Euclid_{target['object_id']}_MER_VIS_cutout.fits"
        if not path.is_file(): continue
        h=fits.getheader(path)
        if str(h.get('GALID')) != target['object_id'] or h.get('PARTIAL',True): continue
        cx,cy=float(h['CENX'])-1,float(h['CENY'])-1
        width=min(int(h['NAXIS1']),max_side);height=min(int(h['NAXIS2']),max_side)
        # Full native sampling, bounded galaxy-centred window; no binning.
        with fits.open(path,memmap=True) as hdul:
            cut=Cutout2D(hdul[0].data,(cx,cy),(height,width),wcs=WCS(h).celestial,
                         mode='trim',copy=True)
        if min(cut.data.shape)<64 or not np.isfinite(cut.data).all(): continue
        chosen.append((path,h,cut,target))
        if len(chosen)==count: break
    if not chosen: raise RuntimeError('No suitable finite complete cutouts found')
    return chosen

def run(work, root, count=3, max_side=1024, methods=('sep','mto')):
    if not 1<=count<=5 or not 64<=max_side<=1536:
        raise ValueError('Pilot limited to 1–5 images and 64–1536 pixels per axis')
    work=Path(work).resolve();root=Path(root).resolve()
    out=root/('results_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ'))
    out.mkdir(parents=True,exist_ok=False)
    config=dict(work=str(work),max_images=count,max_side=max_side,methods=list(methods),
                sep=dict(thresh_sigma=1.5,minarea=5,deblend_nthresh=32,deblend_cont=.005),
                mto=dict(alpha=1e-6,move_factor=.3,noise_model='sigma clipped global; estimated effective gain'),
                packages={name:md.version(name) for name in ('numpy','astropy','sep','scipy','scikit-image','matplotlib')},
                note='Feasibility pilot. No masks adopted and no calibrated noise model.')
    (out/'configuration.json').write_text(json.dumps(config,indent=2))
    if (root/'installation.json').exists():
        (out/'installation.json').write_bytes((root/'installation.json').read_bytes())
    rows=[]
    for path,header,cut,target in select(work,count,max_side):
        folder=out/target['object_id'];folder.mkdir()
        h=header.copy();h.update(cut.wcs.to_header(relax=True))
        cx,cy=cut.to_cutout_position((float(header['CENX'])-1,float(header['CENY'])-1))
        h['CENX']=float(cx)+1;h['CENY']=float(cy)+1
        h.add_history('Source extraction pilot native sampling crop; original unchanged.')
        # Float64 input avoids obsolete upstream np.float cast and preserves native bytes.
        data=np.array(cut.data,dtype=np.float64,order='C')
        infile=folder/'pilot_input.fits'
        fits.PrimaryHDU(data,h).writeto(infile,checksum=True)
        (folder/'input_provenance.json').write_text(json.dumps(dict(
            object_id=target['object_id'],source_path=str(path),source_size=path.stat().st_size,
            crop_shape=list(data.shape),original_shape=[header['NAXIS2'],header['NAXIS1']],
            crop_origin=list(map(int,cut.origin_original)),centre_xy_zero_based=[float(cx),float(cy)],
            pilot_input_sha256=hashlib.sha256(infile.read_bytes()).hexdigest()),indent=2))
        maps={}
        for method in methods:
            row=dict(object_id=target['object_id'],method=method,status='error',objects='',target_label='',error='')
            try:
                dest=folder/f'{method}_segmentation.fits'
                if method=='sep':
                    background,residual,noise,original_rms,noise_record=prepare_sep(data)
                    (folder/'sep_noise_model.json').write_text(json.dumps(noise_record,indent=2))
                    fits.PrimaryHDU(original_rms,h).writeto(folder/'sep_rms_original.fits',checksum=True)
                    if noise_record['model'] != 'spatial':
                        print(target['object_id'], 'SEP noise fallback:', noise_record, flush=True)
                    objects,labels=sep.extract(residual,1.5,err=noise,minarea=5,
                                              deblend_nthresh=32,deblend_cont=.005,
                                              segmentation_map=True)
                    fits.PrimaryHDU(labels.astype(np.int32),h).writeto(dest,checksum=True)
                    dump_csv(folder/'sep_catalogue.csv',
                             [dict(zip(objects.dtype.names,map(lambda x:x.item(),obj))) for obj in objects],
                             list(objects.dtype.names))
                    fits.PrimaryHDU(background.back(),h).writeto(folder/'sep_background.fits',checksum=True)
                    fits.PrimaryHDU(noise,h).writeto(folder/'sep_rms.fits',checksum=True)
                elif method=='mto':
                    source=root/'mtobjects'
                    worker=Path(__file__).resolve().with_name('mto_worker.py')
                    if not (source/'mtolib/lib/mt_objects.so').exists():
                        raise RuntimeError('MTObjects is not built; inspect installation.json/setup output')
                    with (folder/'mto.log').open('w') as log:
                        result=subprocess.run([sys.executable,str(worker),str(source),str(infile),
                                               str(dest),str(folder/'mto_catalogue.csv')],cwd=source,
                                              stdout=log,stderr=subprocess.STDOUT,timeout=300)
                    if result.returncode:
                        raise RuntimeError(f'MTObjects exited {result.returncode}; see mto.log')
                    labels=fits.getdata(dest)
                else: raise ValueError('Unknown method')
                if labels.shape!=data.shape:raise ValueError('Segmentation dimensions differ')
                maps[method]=labels
                if method == 'sep': row['noise_model'] = noise_record['model']
                # Upstream MTObjects may use nonpositive background IDs.
                ids=np.unique(labels);n=int(np.count_nonzero(ids>0))
                row.update(status='ok',objects=n,target_label=int(labels[int(round(cy)),int(round(cx))]))
            except Exception as error:
                row['error']=str(error)
                print(target['object_id'],method,'ERROR:',error,flush=True)
            rows.append(row);dump_csv(out/'summary.csv',rows)
        fig,axes=plt.subplots(1,1+len(methods),figsize=(6*(1+len(methods)),6),squeeze=False)
        for ax in axes[0]:
            ax.imshow(data,origin='lower',cmap='gray',norm=simple_norm(data,'asinh',percent=99.5))
            ax.plot(cx,cy,'r+',ms=8);ax.set_axis_off()
        axes[0,0].set_title('Native sampling pilot crop')
        for ax,method in zip(axes[0,1:],methods):
            if method in maps:
                boundary=find_boundaries(maps[method],mode='outer')
                overlay=np.zeros((*data.shape,4));overlay[boundary]=[0,1,0,.85]
                ax.imshow(overlay,origin='lower');ax.set_title(method.upper()+' boundaries')
            else:ax.set_title(method.upper()+' failed — see summary and log')
        fig.suptitle(target['object_id']+' — diagnostic segmentation only')
        fig.tight_layout();fig.savefig(folder/'comparison.png',dpi=130);plt.close(fig)
        print('Saved',folder/'comparison.png',flush=True)
    print('RESULTS:',out,flush=True)
    return out

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--work',type=Path,required=True);p.add_argument('--root',type=Path,required=True)
    p.add_argument('--methods',nargs='+',choices=['sep','mto'],default=['sep','mto'])
    p.add_argument('--count',type=int,default=3);p.add_argument('--max-side',type=int,default=1024)
    a=p.parse_args();run(a.work,a.root,a.count,a.max_side,a.methods)
