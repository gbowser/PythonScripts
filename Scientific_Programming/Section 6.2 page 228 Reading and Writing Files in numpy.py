# Section 6.2 page 228 Reading and Writing Files in numpy
import numpy as np

fname = 'eg6-a-student-data.txt'
dtype1 = np.dtype([('gender', '|S1'), ('height', 'f8')])
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

dtype2 = np.dtype([('gender', '|S1'), ('weight', 'f8')])
b = np.loadtxt(fname, dtype=dtype2, skiprows=9, usecols=(1,4), converters={4: parse_weight})

mv=b['weight']>0
m_wav=b['weight'][mv & m].mean()
f_wav=b['weight'][mv & ~m].mean()
print(f"Male weight average: {m_wav:.2f} , Female weight average: {f_wav:.2f} ")
