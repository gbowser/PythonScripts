from pathlib import Path
root=Path('../Euclid').resolve()
helper='''def fit_image_compatible(ellipse, **kwargs):
    """Photutils 2 uses nclip; Photutils 3 uses n_clip."""
    import inspect
    parameters = inspect.signature(ellipse.fit_image).parameters
    clip_name = 'n_clip' if 'n_clip' in parameters else 'nclip'
    return ellipse.fit_image(**kwargs, **{clip_name: 3})


def sample_fraction(iso):
    """Accept both Photutils 2 and 3 isophote attribute names."""
    ndata = iso.n_data if hasattr(iso, 'n_data') else iso.ndata
    nflag = iso.n_flag if hasattr(iso, 'n_flag') else iso.nflag
    return ndata / max(1, ndata + nflag)


'''
for path in (root/'fit_euclid_VIS_geometry.py',root/'datalabs_MER_VIS/fit_MER_VIS_geometry_portable.py'):
 text=path.read_text(encoding='utf-8')
 if 'def fit_image_compatible' not in text:
  text=text.replace('def fit_one(',helper+'def fit_one(')
 text=text.replace('trial=ellipse.fit_image(', 'trial=fit_image_compatible(ellipse, ')
 text=text.replace('fix_center=True,n_clip=3,sclip=3','fix_center=True,sclip=3')
 text=text.replace('sampled_fraction=iso.n_data/max(1,iso.n_data+iso.n_flag)', 'sampled_fraction=sample_fraction(iso)')
 path.write_text(text,encoding='utf-8')
 print('Updated',path)
