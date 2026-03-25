# Section 6.2 page 228 Reading and Writing Files in numpy
import numpy as np

fname = 'eg6-a-student-data.txt'
dtype1 = np.dtype([('gender', '|S1'), ('height', 'f8')])
dtype2 = np.dtype([('gender', '|S1'), ('weight', 'f8')])
dtype3 = np.dtype([('gender', '|S1'), ('bps', 'f8'), ('bpd', 'f8')])


a = np.loadtxt(fname, dtype=dtype1, skiprows=9, usecols=(1,3))

print(f"{a}")

m = a['gender'] == b'M'

print(f"Gender = Male\n{m}\n)")

m_av = a['height'][m].mean()
f_av = a['height'][~m].mean()
print(f'Male average: {m_av:.2f} , Female average: {f_av:.2f} ')


def parse_weight(a):
    try:
        return float(a)
    except ValueError:
        return -99

def parse_bp(s):
    try:
        return float(s)
    except ValueError:
        return -99


b = np.loadtxt(fname, dtype=dtype2, skiprows=9, usecols=(1,4), converters={4: parse_weight})

m = b['gender'] == b'M'
mv = b['weight'] > 0
m_wav = b['weight'][mv & m].mean()
f_wav = b['weight'][mv & ~m].mean()
print(f"Male weight average: {m_wav:.2f} , Female weight average: {f_wav:.2f} ")


def reformat_lines(fi):
    for line in fi:
        line=line.replace('/', ' ')
        yield line

with open(fname) as fi:
    gender,bps, bpd=np.loadtxt(reformat_lines(fi), dtype3, skiprows=9, usecols=(1,7,8), converters={7:parse_bp,8:parse_bp}, unpack=True)

# Remove rows with invalid blood-pressure values.
valid_bp = (bps >= 0) & (bpd >= 0)
gender = gender[valid_bp]
bps = bps[valid_bp]
bpd = bpd[valid_bp]

#now do something with the data
print(f"Gender = {gender}\nBPS = {bps}\nBPD = {bpd}")
      
