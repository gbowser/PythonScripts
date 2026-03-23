# try-except-else-finally.py

def process_file(filename):
    try:
        f1 = open(filename, 'r')
    except IOError:
        print("Oops, couldn't open {} for reading".format(filename))
        return
    else:
        lines = f1.readlines()
        print("{} has {} lines.".format(filename, len(lines)))
        f1.close()
    finally:
        print("Done with file {}".format(filename))

    print("The first line of {} is:\n{}".format(filename, lines[0]))
    # further processing of the lines ...
    return


process_file('sonnet0.txt')
process_file('sonnet18.txt')

############ Version 2 ############
def process_file2(filename):
    try:
        with open(filename, 'r') as f:
            lines = f.readlines()
            print(f"{filename} has {len(lines)} lines.")
    except IOError:
        print(f"Oops, couldn't open {filename} for reading")
        return
    finally:
        print(f"Done with file {filename}")

    print(f"The first line of {filename} is:\n{lines[0]}")


process_file('sonnet0.txt')
process_file('sonnet18.txt')


process_file2('sonnet0.txt')
process_file2('sonnet18.txt')