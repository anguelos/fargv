import fargv
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
    args, _ = fargv.parse({"file_path": "example.txt", "min_length": 3})
    frame = word_stats(args.file_path, args.min_length)
    if args.verbosity > 0:
        print(frame)
    print(
        f"\nWord count: unique: {len(frame)}\t total {frame['Count'].sum()}, "
        f"average length: {frame['Length'].mean():.2f} characters"
    )
