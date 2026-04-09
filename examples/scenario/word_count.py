from collections import Counter
import pandas as pd


def word_stats(file_path, min_length):
    with open(file_path, 'r') as file:
        text = file.read()
        words = text.split()
        word_counts = Counter(words)
        frame = pd.DataFrame(word_counts.items(), columns=['Word', 'Count'])
        frame['Length'] = frame['Word'].apply(len)
        frame = frame[frame['Length'] >= min_length]
        return frame


if __name__ == "__main__":
    file_path = 'example.txt'  # Replace with your file path
    frame = word_stats(file_path, 3)
    print(frame.head())
    print(
        f"\nWord count: unique: {len(frame)}\t total {frame['Count'].sum()}, "
        f"average length: {frame['Length'].mean():.2f} characters"
    )
