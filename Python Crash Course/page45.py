
places=["Paris","London", "Oxshott","Claygate","Cobham"]
print(sorted(places,reverse=False))
print(f"\n {places}")

reversed_list = sorted(places,reverse=True)
print(reversed_list)

reversed_list.reverse()
print(reversed_list)
print(reversed_list[1])
print(reversed_list[4])
