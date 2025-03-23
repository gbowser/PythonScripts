# -*- coding: utf-8 -*-
"""
Created on Mon Jul 15 14:15:25 2024

@author: gordo
"""


class Account:
    def __init__(self, owner, balance):
        self.owner = owner
        self.balance = balance

    def __str__(self):
        return f"Account owner:   {self.owner}\nAccount balance: ${self.balance}"

    def deposit(self, amount):
        self.balance = self.balance+amount

    def withdraw(self, amount):
        if amount > self.balance:
            print("Funds Unavailable")
        else:
            self.balance = self.balance-amount
            print("Withdrawal accepted")


acct1 = Account('Jose', 100)
print(acct1)

print(acct1.owner)
print(acct1.balance)
acct1.deposit(50)
print(acct1.balance)

acct1.withdraw(500)
print(acct1.balance)
acct1.withdraw(75)
print(acct1.balance)
