# play fizz buzz
# 3 = fizz, 5 = buzz, 15 = fizz buzz
#count up to 100

counter = 1
while counter <= 100:
    if counter % 15 == 0:
        print("fizz buzz")
    elif counter % 3 == 0:
        print("fizz")
    elif counter % 5 == 0:
        print("buzz")
    else:
        print(counter)
    counter += 1