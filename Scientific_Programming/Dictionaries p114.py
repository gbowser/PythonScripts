height={'Buffy': 1.6, 'Willow': 1.7, 'Xander': 1.8, 'Giles': 1.9, 'Angel': 1.85}

print(height)
print(f"Height of Buffy: {height['Buffy']} m")

height['Spike'] = 1.75
print(height)

boy="Xander" 
print(f"Height of {boy}: {height[boy]} m")

boy="Ralph" 
print(f"Height of {boy}: {height.get(boy, 'Not found')} m")


# keys, values and items
print(f"Keys: {list(height.keys())}\n")
print(f"Values: {list(height.values())}\n")
print(f"Items: {list(height.items())}\n")