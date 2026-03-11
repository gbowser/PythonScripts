# Luhn Algorithm

def digits_from_card_number(card_number):
    cleaned_number = card_number.replace(" ", "")
    return [int(digit) for digit in cleaned_number]


#card_number = "1234 5678 9012 3456"
card_number = "4799 2739 8713 6272"

digits = digits_from_card_number(card_number)
print(digits)

reversed_digits = digits[::-1]

for i in range(1, len(reversed_digits), 2):
    if reversed_digits[i] * 2 > 9:
        reversed_digits[i] = reversed_digits[i] * 2 - 9
    else:
        reversed_digits[i] = reversed_digits[i] * 2
total_sum = sum(reversed_digits)
if total_sum % 10 == 0:
    print("The card number is valid.")
else:    print("The card number is invalid.")   
