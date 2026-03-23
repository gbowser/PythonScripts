# Get freqeuncy of each word in a text file and print the top 10 most common words

import string


def word_frequency(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        text = file.read().lower()  # Convert to lowercase for uniformity
        for mark in string.punctuation:
            text = text.replace(mark, "")
        words = text.split()  # Split the text into words

    frequency = {}
    for word in words:
        if word in frequency:
            frequency[word] += 1
        else:
            frequency[word] = 1

    # Sort the frequency dictionary by value (frequency) in descending order
    def frequency_count(item):
        return item[1]

    sorted_frequency = sorted(frequency.items(), key=frequency_count, reverse=True)

    # Print the top 10 most common words
    print("Top 10 most common words:")
    for word, count in sorted_frequency[:10]:
        print(f"{word}: {count}")


# Example usage
word_frequency("MobyDick.txt")  # Replace "example.txt" with your text file path
