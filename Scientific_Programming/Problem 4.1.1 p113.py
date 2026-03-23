# Write a program to read in the data from the file swallow-speeds.txt 
# and use it to calculate the average air-speed velocity of an (unladen) African swallow. 
# Use exceptions to handle the processing of lines which do not contain valid data points.

def average_speed(filename):
    try:
        with open(filename, 'r') as f:
            speeds = []
            for line in f:
                try:
                    speed = float(line.strip())
                    speeds.append(speed)
                except ValueError:
                    print(f"Skipping invalid data point: {line.strip()}")
    except IOError:
        print(f"Error opening file: {filename}")
        return None

    if not speeds:
        print("No valid data points found.")
        return None

    return sum(speeds) / len(speeds)


average = average_speed('swallow-speeds.txt')
if average is not None:
    print(f"Average air-speed velocity of an (unladen) African swallow: {average:.2f} m/s")
