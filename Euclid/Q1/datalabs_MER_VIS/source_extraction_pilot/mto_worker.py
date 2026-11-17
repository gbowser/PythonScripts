"""Subprocess worker isolates upstream MTObjects and avoids obsolete FITS writing APIs."""
import sys
from pathlib import Path
import numpy as np
from astropy.io import fits
source, infile, outfile, paramsfile = map(Path, sys.argv[1:5])
sys.path.insert(0, str(source))
import mtolib.main as mto
# Upstream FITS loader uses removed np.float on modern NumPy.
# Replace only this I/O function; detection/tree algorithms stay upstream.
mto.read_fits_file = lambda filename: np.array(fits.getdata(filename), dtype=np.float64, order='C')
from astropy.stats import sigma_clipped_stats
image = np.asarray(fits.getdata(infile), dtype=np.float64)
if not np.isfinite(image).all():
    raise ValueError('MTObjects pilot requires a fully finite crop')
mean, median, noise = sigma_clipped_stats(image, sigma=3.)
if not np.isfinite(noise) or noise <= 0:
    raise ValueError('Cannot estimate positive background noise')
# This diagnostic estimate is not an instrumental/calibrated gain.
gain = max(float((mean - image.min()) / noise**2), 1e-6)
sys.argv = ['mto', str(infile), '-bg_mean', str(float(mean)),
            '-bg_variance', str(float(noise**2)), '-gain', str(gain),
            '-alpha', '0.000001', '-move_factor', '0.3', '-verbosity', '1',
            '-par_out', str(paramsfile)]
print('Pilot noise model: clipped background/noise, estimated effective gain',
      float(mean), float(noise), gain, flush=True)
image, params = mto.setup()
processed = mto.preprocess_image(image, params, n=2)
tree = mto.build_max_tree(processed, params)
labels, ancestors = mto.filter_tree(tree, processed, params)
labels = mto.relabel_segments(labels, shuffle_labels=False)
fits.PrimaryHDU(np.asarray(labels).reshape(image.shape).astype(np.int32),
                fits.getheader(infile)).writeto(outfile, checksum=True)
mto.generate_parameters(image, labels, ancestors, params)
