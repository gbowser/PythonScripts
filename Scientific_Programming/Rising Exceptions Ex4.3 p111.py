n = int(input("Enter an even number: "))
if n%2:
    raise ValueError("n must be even!   " )
#statement continues here without interruption
print("This will not be printed if n is odd.")

def str_vector(v):
    assert type(v) is list or type(v) is tuple, \
        'argument to str_vector must be a list or tuple'

    assert len(v) in (2, 3), \
        'vector must be 2D or 3D in str_vector'

    unit_vectors = ['i', 'j', 'k']

    s = []
    for i, component in enumerate(v):
        s.append('{}{}'.format(component, unit_vectors[i]))

    return '+'.join(s).replace('+-', '-')

print(f"Vector: {str_vector([1, 2])}")
