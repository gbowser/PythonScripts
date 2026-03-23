#Q.4.3.2
#what does the code do and how does it work?
nmax=5
x=[1]
for n in range(1,nmax+2):
    print(x)
#    x=[([0]+x)[i]+(x+[0])[i] for i in range(n+1)]
            
# Beginner-friendly version of the line above:
    left = [0] + x
    right = x + [0]
    new_x = []
    for i in range(n + 1):
        new_x.append(left[i] + right[i])
        x = new_x

print(f"Pascal's triangle up to row {nmax}:")
#
#Question 4.3.3
#   0   1   2   3   4   5   6   7   8   9 
a=['A','B','C','D','E','F','G','H','I','J']    #this is a LIST of letters, not a string
b=[ 4,  2,  6,  1,  5,  0,  4,  8,  1,  9]     #this is a LIST of indices, note missing 3 or 7, and 2 x 4's.
#
#sorted b looks like [0, 1, 1, 2, 4, 4, 5, 6, 8, 9]

l = [a[x] for x in b]           # E, C, G, B, F, A, E, I, B, J   (a[4], a[2], a[6], a[1], a[5], a[0], a[4], a[8], a[1], a[9])
m=  [a[x] for x in sorted (b)]  # A, B, B, C, E, F, G, I     (a[0], a[1], a[1], a[2], a[4], a[4], a[5], a[6], a[8], a[9])
n = [a[b[x]] for x in b]        # 1st x is 4, b[4] is 5, a[5] is F, so first element is F, then 2nd x is 2, b[2] is 6, a[6] is G, so second element is G, etc.
o = [x for (y,x) in sorted (zip(b,a))]  #Sorted tuples are (0, 'F'), (1, 'D'), (1, 'I'), (2, 'B'), (4, 'A'), (4, 'G'), etc.
                                        #so first element is F, then D, then I, etc. Note that the 2 x 1's in b are sorted in the
                                        # order they appear in a, so D comes before I, 
                                        # and the 2 x 4's in b are sorted in the order they appear in a, so E comes before F.

print("\n")

print(f"zip(b,a)=list{list(zip(b,a))}") # this is a list of tuples, where each tuple is (b[i], a[i])
print(f"sorted(zip(b,a))={sorted(zip(b,a))}") # this is a list of tuples, where each tuple is (b[i], a[i])

print("\n")

print(f"l={l}")
print(f"m={m}")
print(f"n={n}")
print(f"o={o}")

#Question 4.3.5
#Phone Number substitution cipher from The Wire
#all numbers are switched with the number the opposite side of 5 (in the centre)
# and 5 & 0 are switched with each other

phone_number = "07123456789"
encrypted = "".join(str(10 - int(d)) if d not in "05" else ("0" if d == "5" else "5") for d in phone_number)
print(encrypted)
