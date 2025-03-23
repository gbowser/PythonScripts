import numpy as np

def query(starfilename,planetfilename) :
  star_data = np.loadtxt(starfilename, delimiter=',', usecols=(0, 2))
  planet_data = np.loadtxt(planetfilename, delimiter=',', usecols=(0, 5))
  
  results_array = np.zeros(0)
  for star in star_data:
    for planet in planet_data:
      if star[0]==planet[0]:
        radius = planet[1]/star[1]
        results_array=np.append(results_array,radius)
  results_array=results_array[np.argsort(results_array)]

  return results_array

# You can use this to test your code
# Everything inside this if-statement will be ignored by the automarker
if __name__ == '__main__':
  # Compare your function output to the SQL query
  result = query('stars.csv', 'planets.csv')
  print(result)