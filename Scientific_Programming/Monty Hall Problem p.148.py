#    Run a single trial of the Monty Hall problem, with or without switching
#    after the game show host reveals a goat behind one of the unchosen doors
#    (switch_doors is True or False). The car is behind door number 1 and the
#    game show host knows that. Returns True for a win, otherwise returns False.
#
import random


def run_trial(switch_doors, ndoors=3):
    chosen_door = random.randint(1, ndoors)

    if switch_doors:
        revealed_door = 3 if chosen_door == 2 else 2
        available_doors = [
            dnum
            for dnum in range(1, ndoors + 1)
            if dnum not in (chosen_door, revealed_door)
        ]
        chosen_door = random.choice(available_doors)

    return chosen_door == 1        #so True if the player wins the CAR, else False


def run_trials(ntrials, switch_doors, ndoors=3):
    nwins = 0
    for _ in range(ntrials):
        if run_trial(switch_doors, ndoors):
            nwins += 1
    return nwins


ndoors = 3
ntrials = 10000

nwins_without_switch = run_trials(ntrials, False, ndoors)
nwins_with_switch = run_trials(ntrials, True, ndoors)

print(f"Monty Hall Problem with {ndoors} doors")
print(f"Proportion of wins without switching: {nwins_without_switch / ntrials:.4f}")
print(f"Proportion of wins with switching: {nwins_with_switch / ntrials:.4f}")
