# normliasze a lit of numbers so that values lie between 0 and 1.

def normalize(nums):
    lo=min(nums)
    hi=max(nums)
    for i in range(len(nums)):
        nums[i]=(nums[i]-lo)/(hi-lo)
    return nums




my_list = list(map(int, input("Enter numbers separated by commas: ").split(",")))
print(f"Normalized values: {normalize(my_list)}")