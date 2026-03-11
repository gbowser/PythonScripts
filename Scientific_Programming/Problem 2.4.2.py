#The Hamming distance between two strings of equal length is the number of positions
#at which the corresponding symbols are different.

#Given two DNA strings s1 and s2 of equal length, compute the Hamming distance.   


def hamming_distance(s1, s2):
    counter = 0
    for i in range(len(s1)):
        if s1[i] != s2[i]:
            counter += 1
    return counter
        

s1 = input("Enter the first DNA string: ")
s2 = input("Enter the second DNA string: ")
if len(s1) != len(s2):
    print("Error: The two DNA strings must be of equal length.")
else:    
    print(f"The Hamming distance between the two DNA strings is: {hamming_distance(s1, s2)}")

