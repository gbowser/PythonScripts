#  https://github.com/ska-sa/ARIWS-Cookbook/blob/main/0-Introduction/

import numpy as np
import matplotlib.pylab as plt

def ft2(y):
    """Returns the fourier transform of y"""
    return np.fft.fftshift(np.fft.fft2(np.fft.fftshift(y)))

def ftfreqs(N,dt):
    """Returns the Fourier frequencies"""
    return np.fft.fftshift(np.fft.fftfreq(N,dt))   

N1 = 100
g1 = np.zeros([N1,N1])


g1[N1//2,N1//2] = 1.0
G1 = ft2(g1)

# plot g1 and G1
f, ax = plt.subplots(1,2,figsize=[13,8])  

ax[0].imshow(g1,cmap=plt.get_cmap('Greys'),origin='lower')
ax[0].set_xlim(N1/2-20,N1/2+20)
ax[0].set_ylim(N1/2-20,N1/2+20)
ax[0].set_title('g1')

ax[1].imshow(abs(G1),cmap=plt.get_cmap('Greys'),origin='lower')
ax[1].set_title('G1')
plt.show()

print('Fourier transform G1: ')
print(G1)     

g2 = np.zeros([N1,N1])
g2[N1//2-10,N1//2-10] = 1.0
g2[N1//2+10,N1//2+10] = 1.0
g2[N1//3+10,N1//3+10] = 1.0


G2 = ft2(g2)


# plot g2 and G2
f, ax = plt.subplots(1,2,figsize=[13,5])  

ax[0].imshow(g2,cmap=plt.get_cmap('Greys'),origin='lower')
ax[0].set_xlim(N1/2-30,N1/2+30)
ax[0].set_ylim(N1/2-30,N1/2+30)
ax[0].set_title('g2')

ax[1].imshow(G2.real,cmap=plt.get_cmap('Greys'),origin='lower')
ax[1].set_title('G2')
plt.show()


g3 = np.zeros([N1,N1])
g3[N1//2-10,N1//2+10] = 1.0
g3[N1//2+10,N1//2-10] = 1.0

G3 = ft2(g3)


f, ax = plt.subplots(1,2,figsize=[13,5])  

ax[0].imshow(g3,cmap=plt.get_cmap('Greys'),origin='lower')
ax[0].set_xlim(N1/2-30,N1/2+30)
ax[0].set_ylim(N1/2-30,N1/2+30)
ax[0].set_title('g3')

ax[1].imshow(G3.real,cmap=plt.get_cmap('Greys'),origin='lower')
ax[1].set_title('G3')
plt.show()

g4 = np.zeros([N1,N1],dtype=complex)
g4[N1//2-10,N1//2+10] = 1.0j
g4[N1//2+10,N1//2-10] = -1.0j

G4 = ft2(g4)


f, ax = plt.subplots(1,2,figsize=[13,5])  

ax[0].imshow(g4.imag,cmap=plt.get_cmap('Greys'),origin='lower')
ax[0].set_xlim(N1/2-30,N1/2+30)
ax[0].set_ylim(N1/2-30,N1/2+30)
ax[0].set_title('g4')

ax[1].imshow(G4.real,cmap=plt.get_cmap('Greys'),origin='lower')
ax[1].set_title('G4')
plt.show()

f, ax = plt.subplots(2,2,figsize=[13,8])  

ax[0,0].imshow(g3.real,cmap=plt.get_cmap('Greys'),origin='lower')
ax[0,0].set_xlim(N1/2-30,N1/2+30)
ax[0,0].set_ylim(N1/2-30,N1/2+30)
ax[0,0].set_title('g3')

ax[0,1].imshow(G3.real,cmap=plt.get_cmap('Greys'),origin='lower')
ax[0,1].set_xlim(N1/2-10,N1/2+10)
ax[0,1].set_ylim(N1/2-10,N1/2+10)
ax[0,1].set_title('G3')
ax[0,1].axhline(y=N1/2,color='g')
ax[0,1].axvline(x=N1/2,color='g')

ax[1,0].imshow(g4.imag,cmap=plt.get_cmap('Greys'),origin='lower')
ax[1,0].set_xlim(N1/2-30,N1/2+30)
ax[1,0].set_ylim(N1/2-30,N1/2+30)
ax[1,0].set_title('g4')

ax[1,1].imshow(G4.real,cmap=plt.get_cmap('Greys'),origin='lower')
ax[1,1].set_xlim(N1/2-10,N1/2+10)
ax[1,1].set_ylim(N1/2-10,N1/2+10)
ax[1,1].set_title('G4')
ax[1,1].axhline(y=N1/2,color='g')
ax[1,1].axvline(x=N1/2,color='g')
plt.show()



N2 = 1200
g5 = np.zeros([N2,N2])

# this just sets g5 to 1.0 within a radius if N2/2 from the centre:
xvals = np.tile(np.arange(0,N2,1),(N2,1))
yvals = np.transpose(np.tile(np.arange(N2,0,-1),(N2,1)))
g5[((xvals-N2//2)**2.0+(yvals-N2//2)**2.0)<500] = 1.0

G5 = ft2(g5)


# crease plot to change along the way
f, ax = plt.subplots(1,2,figsize=[13,8])  

ax[0].imshow(g5,cmap=plt.get_cmap('jet'),origin='lower')
ax[0].set_xlim(N2/2-300,N2/2+300)
ax[0].set_ylim(N2/2-300,N2/2+300)
ax[0].set_title('g5')

ax[1].imshow(G5.real,cmap=plt.get_cmap('jet'),origin='lower')
ax[1].set_title('G5')
plt.show()     


g6 = np.zeros([N2,N2])
g6[N2//2-10,N2//2+10] = 40.0
g6[N2//2+10,N2//2-10] = 40.0

G6 = ft2(g6)
 
# crease plot to change along the way
f, ax = plt.subplots(1,2,figsize=[13,8])  

ax[0].imshow(g6,cmap=plt.get_cmap('jet'),origin='lower')
ax[0].set_xlim(N2/2-30,N2/2+30)
ax[0].set_ylim(N2/2-30,N2/2+30)
ax[0].set_title('g6')

ax[1].imshow(G6.real,cmap=plt.get_cmap('jet'),origin='lower')
ax[1].set_title('G6')
plt.show()    


g7 = g5 + g6
G7 = ft2(g7)

f, ax = plt.subplots(1,2,figsize=[13,8])  

ax[0].imshow(g7,cmap=plt.get_cmap('jet'),origin='lower')
ax[0].set_xlim(N2/2-40,N2/2+40)
ax[0].set_ylim(N2/2-40,N2/2+40)
ax[0].set_title('g7')

ax[1].imshow(G7.real,cmap=plt.get_cmap('jet'),origin='lower')
ax[1].set_title('G7')
plt.show()