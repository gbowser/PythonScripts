def func(a,b,**kwargs):
    for k in kwargs:
        print(k,"=",kwargs[k])

func(1,2,x=3,y=4,z=5)


def func2(a,b,c,x,y,z):
    print(a,b,c)
    print(x,y,z)


args=[1,2,3]
kwargs={'x':4,'y':5,'z':"msg"}
func2(*args,**kwargs)
