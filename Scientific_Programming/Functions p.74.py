# functions
def report_length(value, units="m"):
    print(f"The length is {value:.2f} {units}")

report_length(1.23456789)
report_length(1.23456789, "cm")

def local_global(a,b,c):
    print(f"Local variables: a={a}, b={b}, c={c}")
    global d
    d = a + b + c
    print(f"Global variable d set to: {d}")

d=0 #global variable
local_global(1,2,3)
print(f"Accessing global variable d: {d}")  

def func1(a):
        print(f'func1: {a} , id={id(a)}')
        a = 7  #re-assigning local a to 7
        print(f'func1: {a} , id={id(a)}')

a=3
print("\n \n")
func1(a)
print(f'Outside func1: a={a} , id={id(a)}')