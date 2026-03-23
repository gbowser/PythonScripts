
#create a list of resistor colours using 2 letter abbreviations
resistor_colours = ['bk','bn','rd','or','ye','gn','bu','vt','gy','wh']
resistor_dictionary = {}
for index, colour in enumerate(resistor_colours):
    resistor_dictionary[colour] = index
print(resistor_dictionary)


# or more compact version using dictionary comprehension
resistor_dictionary = {colour: index for index, colour in enumerate(resistor_colours)}
print(resistor_dictionary)

#now add the tolerance colours
tolerance_colours = ['gd','sl']
tolerance_dictionary = {colour: index for index, colour in enumerate(tolerance_colours)}
print(tolerance_dictionary) 
