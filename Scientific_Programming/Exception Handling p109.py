import math

def func(x):

    def trig(x):
        for f in (math.sin, math.cos, math.tan):
            print(f"{f.__name__}({x}) = {f(x)}")

    def invtrig(x):
        for f in (math.asin, math.acos, math.atan):
            print(f"{f.__name__}({x}) = {f(x)}")

    trig(x)
    invtrig(x)


func(1.2)
