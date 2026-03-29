# notes.py

# Frequencies of musical notes in 4th octave tuned so that A4 = 440 Hz
notes = {4: {'A': 440, 'B': 493.88, 'C': 261.63, 'D': 293.66, 'E': 329.63,
             'F': 349.23, 'G': 392, 'C#': 277.18, 'D♭': 277.18, 'D#': 311.13,
             'E♭': 311.13, 'F#': 369.99, 'G♭': 369.99, 'G#': 415.30,
             'A♭': 415.30, 'A#': 466.16, 'B♭': 466.16}
        }
# Generate frequences of notes in the other octaves
for octave in (0,1,2,3,5,6,7,8):
    notes[octave] = {}
    for note, ref_freq in notes[4].items():
        notes[octave][note] = ref_freq * 2**(octave - 4)

# First a dictionary of major chord name (keys) and their major thirds and
# perfect fifths (list values)
major_chords = {
    'C': ['E', 'G'],
    'C#': ['F', 'G#'],
    'D♭': ['F', 'A♭'],
    'D': ['F#', 'A'],
    'D#': ['G', 'A#'],
    'E♭': ['G', 'B♭'],
    'E': ['G#', 'B'],
    'F': ['A', 'C'],
    'F#': ['A#', 'C#'],
    'G♭': ['B♭', 'D♭'],
    'G': ['B', 'D'],
    'G#': ['C', 'D#'],
    'A♭': ['C', 'E♭'],
    'A': ['C#', 'E'],
    'A#': ['D', 'F'],
    'B♭': ['D', 'F'],
    'B': ['D#', 'F#']
}

major_chord_notes = {}
for octave in range(9):
    major_chord_notes[octave] = {}
    for root, v in major_chords.items():
        major_third, perfect_fifth = v
        major_chord_notes[octave][root] = (notes[octave][root],
                                           notes[octave][major_third],
                                           notes[octave][perfect_fifth])
