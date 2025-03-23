# -*- coding: utf-8 -*-
"""
Created on Tue Jul 16 17:03:36 2024

@author: gordo
"""
import random

# CARD CLASS
# SUIT, RANK, VALUE

# Lists are in [] and are Mutable , Tuples are () and Immutable


suits = ('Hearts', 'Diamonds', 'Spades', 'Clubs')

ranks = ('Two', 'Three', 'Four', 'Five', 'Six', 'Seven',
         'Eight', 'Nine', 'Ten', 'Jack', 'Queen', 'King', 'Ace')

values = {'Two': 2, 'Three': 3, 'Four': 4, 'Five': 5, 'Six': 6, 'Seven': 7, 'Eight': 8,
          'Nine': 9, 'Ten': 10, 'Jack': 10, 'Queen': 10, 'King': 10, 'Ace': 11}

playing = True
# CARD


class Card:
    def __init__(self, suit, rank):
        self.suit = suit
        self.rank = rank
        self.value = values[rank]

    def __str__(self):
        return self.rank + " of " + self.suit


# DECK
class Deck:
    def __init__(self):
        self.deck = []
        for suit in suits:
            for rank in ranks:
                # create the Card Object
                created_card = Card(suit, rank)
                self.deck.append(created_card)


def shuffle(self):
    random.shuffle(self.deck)


def deal(self):
    return self.deck.pop()


class Hand:
    def __init__(self):
        self.cards = []  # start with an empty list as we did in the Deck class
        self.value = 0   # start with zero value
        self.aces = 0    # add an attribute to keep track of aces


test_deck = Deck()
print(test_deck)
