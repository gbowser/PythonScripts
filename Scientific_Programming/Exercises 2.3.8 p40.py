# https://scipython.com/books/book2/chapter-2-the-core-python-language-i/

s="seehemewe"
print(s[:3])
print(s[3:5])
print(s[5:7])
print(s[-2:])
print(s[3:6])
print(s[-4:2:-1])
print(s[-4:-7:-1])
print(s[5:7]+s[6:7])
print(s[-2::-3])

mystring = "rotavator"
print(mystring[::-1])
print(mystring==mystring[::-1])

days='Sun Mon Tues Wed Thu Fri Sat'
print(days.index('M'))
print(days[days.index('M'):])
print(days[days.index('M'):days.index('Sa')].rstrip())
print(days[6:3:-1].lower()*3)

print(days.replace('rs','').replace('s ',' ')[::4])

print(' -*- '.join(days.split()))

suff='thstndrdthththththththth'
n=10

print('{:d}{:s}'.format(n, suff[n*2:n*2+2]))

s='eggs'
print(s==('eggs' or 'ham'))
print(s==('ham' or 'eggs'))
