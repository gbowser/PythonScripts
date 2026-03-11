#Beford's law states that the 1st digit of many data sets is more likely to be 1 than 2, 2 than 3, and so on. The
#probability of the 1st digit being d is given by P(d) = log10(d+1) - log10(d) = log10(1 + 1/d). Write a program that
#calculates the probability of the 1st digit being 1, 2, ..., 9 and prints the results in a table. Use the math module to calculate the logarithms.


def first_digit(n):
    n = abs(n)
    while n >= 10:
        n //= 10
    return n


#create a list of 500 Fibonacci numbers
fib = [0, 1]
for i in range(2, 500):
    fib.append(fib[i-1] + fib[i-2])     
#count the number of times each digit appears as the first digit

frequency = [0] * 10

for i in fib:
    j = first_digit(i)
    frequency[j] += 1   
#calculate the probability of each digit being the first digit
total = sum(frequency)  
probability = [0] * 10
for i in range(1, 10):
    probability[i] = frequency[i] / total   
#print the results in a table


print("Digit\tFrequency\tProbability")      
for i in range(1, 10):
    print(f"{i}\t{frequency[i]}\t\t{probability[i]:.4f}")







