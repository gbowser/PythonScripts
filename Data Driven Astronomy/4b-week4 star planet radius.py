import numpy as np

def query(fname_1, fname_2):
  stars = np.loadtxt(fname_1, delimiter=',', usecols=(0, 2))
  planets = np.loadtxt(fname_2, delimiter=',', usecols=(0, 5))

  f_stars = stars[stars[:,1]>1, :]                
  s_stars = f_stars[np.argsort(f_stars[:, 1]), :] 
 
  final = np.zeros((1, 1))
  for i in range(s_stars.shape[0]):
    kep_id = s_stars[i, 0]
    s_radius = s_stars[i, 1]

    matching_planets = planets[np.where(planets[:, 0] == kep_id), 1].T
    final = np.concatenate((final, matching_planets/s_radius))

  return np.sort(final[1:], axis = 0)
    
    

 
if __name__ == '__main__':
  print(query('stars.csv', 'planets.csv')) 
    

 