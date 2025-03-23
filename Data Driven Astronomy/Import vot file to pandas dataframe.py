# https://gist.github.com/icshih/52ca49eb218a2d5b660ee4a653301b2b

from astropy.io.votable import parse
from astropy import units as u
from astropy.coordinates import SkyCoord
import pandas as pd


dir_import = "D://Dropbox/Public Documents/UCLAN/AA3050 Dissertation/Pleaides Membership/"
file_import = "Brandner 2023.vot"

def votable_to_pandas(votable_file):
    votable = parse(votable_file)
    table = votable.get_first_table().to_table(use_names_over_ids=True)
    return table.to_pandas()

mydf = votable_to_pandas(dir_import+file_import)

#basic single call
example=SkyCoord(ra=10.9*u.degree, dec=15*u.degree, distance = 12*u.pc, frame='icrs').cartesian.x
print(example)

angle=30.0
angle=angle*u.deg
print(angle)


df = pd.DataFrame({'angles': [0, 30, 45, 60, 90]})  # Angles in degrees
print(df)
# Convert the 'angles' column to Astropy degrees
df['angles'] = df['angles'] * u.deg
print(df)



# convert to astropy units
mydf[["x","y","z"]]=0*u.pc
mydf["RA_ICRS"]=mydf["RA_ICRS"]*u.deg
mydf["DE_ICRS"]=mydf["DE_ICRS"]*u.deg
mydf["dpgeo"]=mydf["dpgeo"]*u.pc
print(mydf)


df_test=pd.DataFrame({'RA': [10*u.deg,20*u.deg],'DEC':[14*u.deg,15*u.deg],'DIST':[8*u.pc,10*u.pc],'x':[0*u.pc,0*u.pc]})
print(df_test)

df_test["x"]=SkyCoord(ra=(df_test["RA"]), dec=(df_test["DEC"]), distance=(df_test["DIST"]), frame='icrs').cartesian.x




print(mydf)


mydf["x"]=SkyCoord(ra=(mydf["RA_ICRS"]), dec=(mydf["DE_ICRS"]), distance=(mydf["dpgeo"]), frame='icrs').cartesian.x

pass


