"""
This is test code from my Python Book
More waffle here
"""

nostarch_url = "https://nostarch.com"
shorter = nostarch_url.removeprefix("https://")
print(shorter)

my_name = "gordon bowser"
print(f"Hello {my_name} , would you like to learn Python")
print(f"Hello - Upper case {my_name.upper()}  !")
print(f"Hello - Title case {my_name.title()}  !")

author = "Albert Einstein"
quote = "time stands still"
print(f'{author} said "{quote}"')
ann_name = "   Ann Elizabeth Bowser  "
print(f"left strip {ann_name.lstrip()}")
print(f"right strip {ann_name.rstrip()}")
print(f"both strip {ann_name.strip()}")

filename1 = "python_notes.txt"
print(f" remove file extension {filename1.removesuffix(".txt")}")
