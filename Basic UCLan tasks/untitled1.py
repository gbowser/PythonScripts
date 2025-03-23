


run2d=26
plate = 1324
mjd = 53088
fiberID = 456
baseURL = 'http://data.sdss3.org/sas/dr8/sdss/'
dirURL=f'spectro/redux/{run2d:d}/spectra/{plate:d}/'
fileURL="spec-{plate:d}-{mjd:d}-{fiberID:04d}"
url=baseURL+dirURL+fileURL+'.fits'

saveFilename='spectrum.fits'


import urllib.request
urllib.request.urlretrieve(url, saveFilename)
