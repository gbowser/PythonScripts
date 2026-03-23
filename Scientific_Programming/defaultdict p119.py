text = "Four score and seven years ago our fathers brought forth on this continent, a new nation, conceived in Liberty, and dedicated to the proposition that all men are created equal"

# remove punctuation
text = text.replace(',', '').lower()

word_lengths = {}

for word in text.split():
    try:
        word_lengths[len(word)] += 1
    except KeyError:
        word_lengths[len(word)] = 1

print(word_lengths)


###################Using defaultdict###################

from collections import defaultdict

word_lengths = defaultdict(int)

for word in text.split():
    word_lengths[len(word)] += 1

print(word_lengths)