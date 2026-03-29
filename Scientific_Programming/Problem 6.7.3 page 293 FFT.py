from pathlib import Path

import numpy as np
from scipy.io import wavfile
from scipy.signal import find_peaks
from notes import notes as octave_notes


def build_note_frequency_map(octave_dict):
    """Flatten {octave: {note: freq}} into {'C4': freq, ...}."""
    flat_notes = {}
    for octave, note_map in octave_dict.items():
        for note_name, frequency in note_map.items():
            ascii_name = note_name.replace("♭", "b")
            flat_notes[f"{ascii_name}{octave}"] = frequency
    return flat_notes


notes = build_note_frequency_map(octave_notes)


def to_mono(wav):
    """Convert stereo audio to mono by averaging channels."""
    if wav.ndim == 2:
        return wav.mean(axis=1)
    return wav.astype(float)


def positive_fft(signal, sample_rate):
    """Return positive frequencies and amplitudes from the FFT."""
    n = len(signal)
    fft_vals = np.fft.fft(signal)
    freqs = np.fft.fftfreq(n, d=1 / sample_rate)

    mask = freqs > 0
    return freqs[mask], np.abs(fft_vals[mask])


def strongest_frequencies(freqs, amps, n_peaks=20):
    """Find the strongest spectral peaks."""
    peaks, _ = find_peaks(amps, height=np.max(amps) * 0.1)
    peak_freqs = freqs[peaks]
    peak_amps = amps[peaks]

    order = np.argsort(peak_amps)[::-1]
    return peak_freqs[order][:n_peaks]


def nearest_note(freq, note_dict):
    """Return the nearest note name to a given frequency."""
    names = list(note_dict.keys())
    values = np.array(list(note_dict.values()))
    idx = np.argmin(np.abs(values - freq))
    return names[idx], values[idx]


def pitch_class(note_name):
    """
    Reduce note names like C4, F#5, Bb3 to pitch classes C, F#, Bb.
    Assumes octave number is at the end.
    """
    if note_name[-1].isdigit():
        return note_name[:-1]
    return note_name


def major_chord_name(note_classes):
    """
    Identify a major chord from pitch classes.
    A major chord consists of root, major third, perfect fifth.
    """
    chromatic = ['C', 'C#', 'D', 'D#', 'E', 'F',
                 'F#', 'G', 'G#', 'A', 'A#', 'B']

    enharmonic = {
        'Db': 'C#', 'D♭': 'C#',
        'Eb': 'D#', 'E♭': 'D#',
        'Gb': 'F#', 'G♭': 'F#',
        'Ab': 'G#', 'A♭': 'G#',
        'Bb': 'A#', 'B♭': 'A#',
    }

    cleaned = []
    for n in note_classes:
        cleaned.append(enharmonic.get(n, n))

    unique_notes = sorted(set(cleaned), key=lambda x: chromatic.index(x))

    for root in unique_notes:
        i = chromatic.index(root)
        third = chromatic[(i + 4) % 12]
        fifth = chromatic[(i + 7) % 12]

        if {root, third, fifth}.issubset(set(unique_notes)):
            return f"{root} major"

    return "No major chord identified"


def find_audio_file(script_dir):
    """Find the chord audio file in the same directory as the script."""
    candidate_names = ["chords.wav", "chord.wav"]
    for name in candidate_names:
        candidate = script_dir / name
        if candidate.exists():
            return candidate

    wav_files = sorted(script_dir.glob("*.wav"))
    if wav_files:
        return wav_files[0]

    raise FileNotFoundError(f"No WAV file found in {script_dir}")


# ---------- main program ----------
script_dir = Path(__file__).resolve().parent
audio_path = find_audio_file(script_dir)
sample_rate, wav = wavfile.read(audio_path)

wav = to_mono(wav)
freqs, amps = positive_fft(wav, sample_rate)

peak_freqs = strongest_frequencies(freqs, amps, n_peaks=20)

print(f"Using audio file: {audio_path.name}")
print("Strongest frequencies and nearest notes:")
found_notes = []

for f in peak_freqs:
    name, ref_freq = nearest_note(f, notes)
    pc = pitch_class(name)
    found_notes.append(pc)
    print(f"{f:8.2f} Hz  ->  {name:4s} ({ref_freq:8.2f} Hz)")

chord = major_chord_name(found_notes)

print("\nDetected pitch classes:", sorted(set(found_notes)))
print("Detected chord:", chord)
