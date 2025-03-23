from IPython.display import clear_output
import random
1  # -*- coding: utf-8 -*-
"""
Created on Mon Jul  8 10:11:34 2024

@author: gordo
"""


def display_board(board):

    print(f"    !     !   ")
    print(f" {board[7]}  !  {board[8]}  !  {board[9]}")
    print(f"- --!-----!---")
    print(f"    !     !   ")
    print(f" {board[4]}  !  {board[5]}  !  {board[6]}")
    print(f"- --!-----!---")
    print(f"    !     !   ")
    print(f" {board[1]}  !  {board[2]}  !  {board[3]}")
    print(f"    !     !   ")
    print(f" ")


test_board = ['#', 'X', 'X', 'X', ' ', 'X', 'O', 'X', 'O', 'X']
display_board(test_board)


def player_input():
    marker = ''

    while not (marker == 'X' or marker == 'O'):
        marker = input('Player 1: Do you want to be X or O? ').upper()

    if marker == 'X':
        return ('X', 'O')
    else:
        return ('O', 'X')


def place_marker(board, marker, position):
    board[position] = marker


def win_check(board, mark):
    win = False
    win = ((board[7] == mark and board[8] == mark and board[9] == mark) or
           # across the top
           # across the middle
           (board[4] == mark and board[5] == mark and board[6] == mark) or
           # across the bottom
           (board[1] == mark and board[2] == mark and board[3] == mark) or
           # down the middle
           (board[7] == mark and board[4] == mark and board[1] == mark) or
           # down the middle
           (board[8] == mark and board[5] == mark and board[2] == mark) or
           # down the right side
           (board[9] == mark and board[6] == mark and board[3] == mark) or
           # diagonal
           (board[7] == mark and board[5] == mark and board[3] == mark) or
           (board[9] == mark and board[5] == mark and board[1] == mark))
    return (win)


print(win_check(test_board, "X"))


def choose_first():
    player = random.randint(1, 2)
    player = "Player " + str(player)
    return player


def space_check(board, position):
    if board[position] == "X" or board[position] == "O":
        space = False
    else:
        space = True
    return (space)


def full_board_check(board):
    counter = 0

    for position in range(1, 10):
        if board[position] == "X" or board[position] == "O":
            counter += 1
    return (counter == 9)


def input_posn():
    while True:
        user_input = input("Please enter an integer between 0 and 9: ")
        try:
            value = int(user_input)
            if 0 <= value <= 9:
             #      print(f"Thank you! You entered {value}.")
                return value
            else:
                print("The number is not between 0 and 9. Please try again.")
        except ValueError:
            print("That's not an integer. Please try again.")

# Call the function to prompt the user


def player_choice(board):
    position = 0

    while position not in [1, 2, 3, 4, 5, 6, 7, 8, 9] or not space_check(board, position):
        position = int(input('Choose your next position: (1-9) '))

    return position


def replay():
    if input("do you want to play again (y/n): ") == "y":
        return True
    else:
        return False


print(replay())
