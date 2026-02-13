def xor1(a, b):
    return not (a == b)


def xor2(a, b):
    return a == (not b)


print(xor1(0, 0))
print(xor1(0, 1))
print(xor1(1, 0))
print(xor1(1, 1))
print()

print(xor2(0, 0))
print(xor2(0, 1))
print(xor2(1, 0))
print(xor2(1, 1))
